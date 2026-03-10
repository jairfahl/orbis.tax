"""
api/main.py — FastAPI: 3 endpoints do motor cognitivo TaxMind Light.

POST /v1/analyze  — análise tributária completa
GET  /v1/chunks   — busca RAG direta
GET  /v1/health   — status do sistema
"""

import logging
import os
from typing import Optional

import psycopg2
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.cognitive.engine import MODEL_DEV, AnaliseResult, analisar
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
    """Status do sistema com contagens do banco."""
    try:
        url = os.getenv("DATABASE_URL")
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM chunks")
        chunks_total = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM embeddings")
        embeddings_total = cur.fetchone()[0]
        cur.close()
        conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Banco inacessível: {e}")

    return {
        "status": "ok",
        "chunks_total": chunks_total,
        "embeddings_total": embeddings_total,
    }
