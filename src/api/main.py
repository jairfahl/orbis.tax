"""
api/main.py — FastAPI: 8 endpoints do motor cognitivo TaxMind Light.

POST /v1/analyze                          — análise tributária completa
GET  /v1/chunks                           — busca RAG direta
GET  /v1/health                           — status do sistema
POST /v1/ingest/upload                    — ingestão de PDF adicional
POST /v1/cases                            — criar caso protocolo
GET  /v1/cases/{case_id}                  — estado do caso
POST /v1/cases/{case_id}/steps/{passo}    — submeter passo
POST /v1/cases/{case_id}/carimbo/confirmar — confirmar alerta carimbo
"""

import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Optional

import psycopg2
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.cognitive.engine import MODEL_DEV, AnaliseResult, analisar
from src.ingest.chunker import chunkar_documento
from src.protocol.carimbo import CarimboConfirmacaoError, DetectorCarimbo
from src.protocol.engine import CaseEstado, ProtocolError, ProtocolStateEngine
from src.ingest.embedder import gerar_e_persistir_embeddings
from src.ingest.loader import DocumentoNorma, extrair_texto_pdf
from src.quality.engine import QualidadeStatus
from src.rag.retriever import ChunkResultado, retrieve

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="TaxMind Light API",
    description="Motor cognitivo para análise da Reforma Tributária brasileira",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Schemas de entrada ---

class AnalyzeRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Consulta tributária")
    norma_filter: Optional[list[str]] = Field(None, description="Filtrar por normas: EC132_2023, LC214_2025, LC227_2026")
    top_k: int = Field(3, ge=1, le=10)
    model: str = Field(MODEL_DEV)


# --- Serialização de AnaliseResult para dict ---

def _analise_to_dict(resultado: AnaliseResult) -> dict:
    return {
        "query": resultado.query,
        "qualidade": {
            "status": resultado.qualidade.status.value,
            "regras_ok": resultado.qualidade.regras_ok,
            "bloqueios": resultado.qualidade.bloqueios,
            "ressalvas": resultado.qualidade.ressalvas,
            "disclaimer": resultado.qualidade.disclaimer,
        },
        "fundamento_legal": resultado.fundamento_legal,
        "grau_consolidacao": resultado.grau_consolidacao,
        "contra_tese": resultado.contra_tese,
        "scoring_confianca": resultado.scoring_confianca,
        "resposta": resultado.resposta,
        "disclaimer": resultado.disclaimer,
        "anti_alucinacao": {
            "m1_existencia": resultado.anti_alucinacao.m1_existencia,
            "m2_validade": resultado.anti_alucinacao.m2_validade,
            "m3_pertinencia": resultado.anti_alucinacao.m3_pertinencia,
            "m4_consistencia": resultado.anti_alucinacao.m4_consistencia,
            "bloqueado": resultado.anti_alucinacao.bloqueado,
            "flags": resultado.anti_alucinacao.flags,
        },
        "chunks": [
            {
                "chunk_id": c.chunk_id,
                "norma_codigo": c.norma_codigo,
                "artigo": c.artigo,
                "texto": c.texto,
                "score_vetorial": c.score_vetorial,
                "score_bm25": c.score_bm25,
                "score_final": c.score_final,
            }
            for c in resultado.chunks
        ],
        "prompt_version": resultado.prompt_version,
        "model_id": resultado.model_id,
        "latencia_ms": resultado.latencia_ms,
    }


# --- Endpoints ---

@app.post("/v1/analyze")
async def analyze(req: AnalyzeRequest):
    """
    Análise tributária completa P1→P4.
    Retorna 400 se a qualidade for VERMELHO (bloqueado).
    """
    logger.info("POST /v1/analyze query=%s", req.query[:80])
    try:
        resultado = analisar(
            query=req.query,
            top_k=req.top_k,
            norma_filter=req.norma_filter,
            model=req.model,
        )
    except Exception as e:
        logger.error("Erro interno em /v1/analyze: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    if resultado.qualidade.status == QualidadeStatus.VERMELHO:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Consulta bloqueada pelo DataQualityEngine",
                "bloqueios": resultado.qualidade.bloqueios,
                "qualidade_status": "vermelho",
            },
        )

    return _analise_to_dict(resultado)


@app.get("/v1/chunks")
async def get_chunks(
    q: str = Query(..., description="Texto da busca"),
    top_k: int = Query(3, ge=1, le=10),
    norma: Optional[str] = Query(None, description="Código da norma para filtrar"),
):
    """Busca RAG direta sem análise cognitiva."""
    logger.info("GET /v1/chunks q=%s top_k=%d norma=%s", q[:60], top_k, norma)
    try:
        norma_filter = [norma] if norma else None
        chunks = retrieve(q, top_k=top_k, norma_filter=norma_filter)
    except Exception as e:
        logger.error("Erro em /v1/chunks: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

    return [
        {
            "chunk_id": c.chunk_id,
            "norma_codigo": c.norma_codigo,
            "artigo": c.artigo,
            "texto": c.texto,
            "score_vetorial": c.score_vetorial,
            "score_bm25": c.score_bm25,
            "score_final": c.score_final,
        }
        for c in chunks
    ]


@app.get("/v1/health")
async def health():
    """Status do sistema com contagens e lista de normas disponíveis."""
    try:
        url = os.getenv("DATABASE_URL")
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM chunks")
        chunks_total = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM embeddings")
        embeddings_total = cur.fetchone()[0]
        cur.execute("SELECT codigo, nome FROM normas WHERE vigente = TRUE ORDER BY ano, codigo")
        normas = [{"codigo": r[0], "nome": r[1]} for r in cur.fetchall()]
        cur.close()
        conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Banco inacessível: {e}")

    return {
        "status": "ok",
        "chunks_total": chunks_total,
        "embeddings_total": embeddings_total,
        "normas": normas,
    }


@app.post("/v1/ingest/upload")
async def ingest_upload(
    file: UploadFile = File(..., description="Arquivo PDF a ingerir"),
    nome: str = Form(..., description="Nome do documento (ex: IN RFB 2184/2024)"),
    tipo: str = Form(..., description="Tipo: IN | Resolucao | Parecer | Manual | Outro"),
):
    """
    Ingestão de PDF adicional (INs, Resoluções, Pareceres, Manuais).
    O PDF é processado em /tmp e não é persistido no disco após ingestão.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Apenas arquivos PDF são aceitos")

    logger.info("POST /v1/ingest/upload nome=%s tipo=%s", nome, tipo)

    # Gerar código único a partir do nome
    codigo = re.sub(r"[^A-Za-z0-9]", "_", nome)[:30].strip("_")

    conteudo = await file.read()

    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as tmp:
            tmp.write(conteudo)
            tmp.flush()
            tmp_path = Path(tmp.name)

            # Extrair texto
            texto = extrair_texto_pdf(tmp_path)
            if not texto.strip():
                raise HTTPException(status_code=400, detail="PDF sem texto extraível (pode ser imagem)")

            doc = DocumentoNorma(
                codigo=codigo,
                nome=nome,
                tipo=tipo,
                numero="0",
                ano=2024,
                arquivo=file.filename,
                texto=texto,
            )

            # Persistir norma + chunks + embeddings
            url = os.getenv("DATABASE_URL")
            conn = psycopg2.connect(url)
            cur = conn.cursor()

            cur.execute(
                """
                INSERT INTO normas (codigo, nome, tipo, numero, ano, arquivo)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (codigo) DO UPDATE SET
                    nome = EXCLUDED.nome, arquivo = EXCLUDED.arquivo, vigente = TRUE
                RETURNING id
                """,
                (doc.codigo, doc.nome, doc.tipo, doc.numero, doc.ano, doc.arquivo),
            )
            norma_id = cur.fetchone()[0]
            conn.commit()

            chunks = chunkar_documento(doc.texto)

            chunk_ids: list[int] = []
            for chunk in chunks:
                cur.execute(
                    """
                    INSERT INTO chunks (norma_id, chunk_index, texto, artigo, secao, titulo, tokens)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (norma_id, chunk_index) DO NOTHING
                    RETURNING id
                    """,
                    (norma_id, chunk.chunk_index, chunk.texto, chunk.artigo,
                     chunk.secao, chunk.titulo, chunk.tokens),
                )
                row = cur.fetchone()
                if row:
                    chunk_ids.append(row[0])
                else:
                    cur.execute(
                        "SELECT id FROM chunks WHERE norma_id=%s AND chunk_index=%s",
                        (norma_id, chunk.chunk_index),
                    )
                    chunk_ids.append(cur.fetchone()[0])
            conn.commit()

            n_emb = gerar_e_persistir_embeddings(conn, chunk_ids, chunks)
            cur.close()
            conn.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erro em /v1/ingest/upload: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    logger.info("Upload ingerido: %s | chunks=%d | embeddings=%d", nome, len(chunks), n_emb)
    return {
        "norma_id": norma_id,
        "nome": nome,
        "codigo": codigo,
        "chunks": len(chunks),
        "embeddings": n_emb,
    }


# --- Protocol schemas ---

class CriarCasoRequest(BaseModel):
    titulo: str = Field(..., min_length=10, description="Título do caso (mín. 10 chars)")
    descricao: str = Field(..., min_length=1)
    contexto_fiscal: str = Field(..., min_length=1)


class SubmeterPassoRequest(BaseModel):
    dados: dict = Field(..., description="Dados do passo conforme campos obrigatórios")
    acao: str = Field("avancar", description="'avancar' ou 'voltar'")


class ConfirmarCarimboRequest(BaseModel):
    alert_id: int
    justificativa: str = Field(..., min_length=20)


_protocol_engine = ProtocolStateEngine()
_carimbo_detector = DetectorCarimbo()


def _case_estado_to_dict(estado: CaseEstado) -> dict:
    return {
        "case_id": estado.case_id,
        "titulo": estado.titulo,
        "status": estado.status,
        "passo_atual": estado.passo_atual,
        "steps": {
            str(p): {"dados": v["dados"], "concluido": v["concluido"]}
            for p, v in estado.steps.items()
        },
        "historico": estado.historico,
        "created_at": estado.created_at,
        "updated_at": estado.updated_at,
    }


# --- Protocol endpoints ---

@app.post("/v1/cases", status_code=201)
async def criar_caso(req: CriarCasoRequest):
    """Cria um novo caso protocolar em P1/rascunho."""
    logger.info("POST /v1/cases titulo=%s", req.titulo[:60])
    try:
        case_id = _protocol_engine.criar_caso(
            titulo=req.titulo,
            descricao=req.descricao,
            contexto_fiscal=req.contexto_fiscal,
        )
    except ProtocolError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("Erro em /v1/cases: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    return {"case_id": case_id, "status": "rascunho", "passo_atual": 1}


@app.get("/v1/cases/{case_id}")
async def get_caso(case_id: int):
    """Retorna o estado completo do caso com histórico."""
    logger.info("GET /v1/cases/%d", case_id)
    try:
        estado = _protocol_engine.get_estado(case_id)
    except ProtocolError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Erro em GET /v1/cases/%d: %s", case_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    return _case_estado_to_dict(estado)


@app.post("/v1/cases/{case_id}/steps/{passo}")
async def submeter_passo(case_id: int, passo: int, req: SubmeterPassoRequest):
    """
    Submete dados de um passo e avança/retrocede o protocolo.
    No P6, executa DetectorCarimbo automaticamente se dados contiverem
    'texto_decisao' e 'texto_recomendacao'.
    """
    logger.info("POST /v1/cases/%d/steps/%d acao=%s", case_id, passo, req.acao)
    try:
        if req.acao == "voltar":
            step = _protocol_engine.voltar(case_id, passo)
            return {
                "case_id": case_id,
                "passo": step.passo,
                "concluido": step.concluido,
                "proximo_passo": step.proximo_passo,
                "carimbo": None,
            }

        step = _protocol_engine.avancar(case_id, passo, req.dados)

        # Detector de carimbo ativado no P7 (decisão final vs recomendação P6)
        carimbo_result = None
        if passo == 7:
            texto_decisao = req.dados.get("decisao_final", "")
            # Buscar recomendação do P6 para comparação
            try:
                estado = _protocol_engine.get_estado(case_id)
                p6_dados = estado.steps.get(6, {}).get("dados", {})
                if isinstance(p6_dados, dict):
                    texto_recomendacao = p6_dados.get("recomendacao", "")
                else:
                    texto_recomendacao = ""
            except Exception:
                texto_recomendacao = ""

            if texto_decisao and texto_recomendacao:
                try:
                    cr = _carimbo_detector.verificar(
                        case_id=case_id,
                        passo=passo,
                        texto_decisao=texto_decisao,
                        texto_recomendacao=texto_recomendacao,
                    )
                    carimbo_result = {
                        "score_similaridade": cr.score_similaridade,
                        "alerta": cr.alerta,
                        "mensagem": cr.mensagem,
                        "alert_id": cr.alert_id,
                    }
                except Exception as e:
                    logger.warning("Carimbo check falhou (não bloqueante): %s", e)

        return {
            "case_id": case_id,
            "passo": step.passo,
            "concluido": step.concluido,
            "proximo_passo": step.proximo_passo,
            "carimbo": carimbo_result,
        }

    except ProtocolError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("Erro em POST /v1/cases/%d/steps/%d: %s", case_id, passo, e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/cases/{case_id}/carimbo/confirmar")
async def confirmar_carimbo(case_id: int, req: ConfirmarCarimboRequest):
    """Confirma alerta de carimbo com justificativa do gestor (mín. 20 chars)."""
    logger.info("POST /v1/cases/%d/carimbo/confirmar alert_id=%d", case_id, req.alert_id)
    try:
        _carimbo_detector.confirmar(req.alert_id, req.justificativa)
    except CarimboConfirmacaoError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Erro em confirmar_carimbo: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    return {"confirmado": True, "alert_id": req.alert_id}
