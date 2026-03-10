"""
outputs/stakeholders.py — StakeholderDecomposer.

Gera views adaptadas por perfil de stakeholder a partir de um output existente.
Campos internos (scoring, chunking) são PROIBIDOS para StakeholderTipo.EXTERNO.
"""

import json
import logging
import os
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import anthropic
import psycopg2
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

MODEL_DEV = os.getenv("MODEL_DEV", "claude-haiku-4-5-20251001")

CAMPOS_INTERNOS_PROIBIDOS_EXTERNO = {
    "scoring_confianca", "anti_alucinacao", "chunks_usados",
    "versao_prompt", "versao_base", "score_vetorial", "score_bm25",
    "chunk_id", "model_id", "latencia_ms",
}


class StakeholderTipo(str, Enum):
    CFO = "cfo"
    JURIDICO = "juridico"
    COMPRAS = "compras"
    AUDITORIA = "auditoria"
    DIRETORIA = "diretoria"
    EXTERNO = "externo"


PERFIS_STAKEHOLDER = {
    StakeholderTipo.CFO: {
        "foco": "impacto financeiro, materialidade, prazos",
        "linguagem": "executiva, quantitativa",
        "campos_visiveis": ["materialidade", "impacto_estimado", "prazo_acao", "risco_financeiro"],
    },
    StakeholderTipo.JURIDICO: {
        "foco": "compliance, rastreabilidade, dispositivos legais",
        "linguagem": "técnico-jurídica",
        "campos_visiveis": ["fundamento_legal", "dispositivos", "grau_consolidacao", "contra_tese", "disclaimer"],
    },
    StakeholderTipo.COMPRAS: {
        "foco": "impacto em fornecedores, NCM, CFOP, alíquotas",
        "linguagem": "operacional",
        "campos_visiveis": ["aliquotas_impactadas", "cfop_envolvidos", "fornecedores_tipo", "prazo_adaptacao"],
    },
    StakeholderTipo.AUDITORIA: {
        "foco": "rastreabilidade total, versão da base, scoring, anti-alucinação",
        "linguagem": "técnica, auditável",
        "campos_visiveis": ["versao_prompt", "versao_base", "scoring_confianca", "anti_alucinacao", "chunks_usados"],
    },
    StakeholderTipo.DIRETORIA: {
        "foco": "decisão estratégica, risco regulatório, reputação",
        "linguagem": "executiva sintética",
        "campos_visiveis": ["resumo_executivo", "risco_regulatorio", "recomendacao_principal", "prazo_decisao"],
    },
    StakeholderTipo.EXTERNO: {
        "foco": "mínimo necessário para compartilhamento seguro",
        "linguagem": "neutra, sem dados internos",
        "campos_visiveis": ["titulo", "recomendacao_principal", "fundamento_legal", "disclaimer"],
    },
}

_PROMPT_ADAPTAR = """\
Você é um especialista em comunicação tributária adaptando um output para {stakeholder}.

Perfil do stakeholder:
- Foco: {foco}
- Linguagem: {linguagem}

Conteúdo original do output:
{conteudo}

Gere um resumo adaptado para este stakeholder em no máximo 3 parágrafos.
Use a linguagem e foco indicados. Seja conciso e direto.
NÃO inclua dados internos técnicos (scores, embeddings, versões de modelo) a menos que o stakeholder seja auditoria.
Retorne apenas o texto do resumo, sem cabeçalhos."""


@dataclass
class StakeholderView:
    output_id: int
    stakeholder: StakeholderTipo
    resumo: str
    campos_visiveis: list[str]
    db_id: Optional[int] = None


def _filtrar_campos_externo(conteudo: dict) -> dict:
    """Remove campos internos proibidos para stakeholder EXTERNO."""
    return {k: v for k, v in conteudo.items() if k not in CAMPOS_INTERNOS_PROIBIDOS_EXTERNO}


class StakeholderDecomposer:

    def __init__(self, model: str = MODEL_DEV):
        self._model = model
        self._client: Optional[anthropic.Anthropic] = None

    def _get_client(self) -> anthropic.Anthropic:
        if self._client is None:
            key = os.getenv("ANTHROPIC_API_KEY")
            if not key or key == "<PREENCHER>":
                raise EnvironmentError("ANTHROPIC_API_KEY não configurada")
            self._client = anthropic.Anthropic(api_key=key)
        return self._client

    def _adaptar_conteudo(
        self,
        stakeholder: StakeholderTipo,
        conteudo: dict,
    ) -> str:
        """Gera resumo adaptado via LLM."""
        perfil = PERFIS_STAKEHOLDER[stakeholder]

        # Filtrar campos proibidos para EXTERNO
        if stakeholder == StakeholderTipo.EXTERNO:
            conteudo = _filtrar_campos_externo(conteudo)

        conteudo_str = json.dumps(conteudo, ensure_ascii=False, indent=2)
        prompt = _PROMPT_ADAPTAR.format(
            stakeholder=stakeholder.value,
            foco=perfil["foco"],
            linguagem=perfil["linguagem"],
            conteudo=conteudo_str,
        )

        try:
            client = self._get_client()
            msg = client.messages.create(
                model=self._model,
                max_tokens=512,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}],
            )
            return msg.content[0].text.strip()
        except Exception as e:
            logger.warning("Falha ao adaptar conteúdo para %s: %s", stakeholder, e)
            return f"[Resumo adaptado indisponível — {stakeholder.value}]"

    def decompor(
        self,
        output_id: int,
        stakeholders: list[StakeholderTipo],
        conteudo: dict,
        conn: Optional[psycopg2.extensions.connection] = None,
    ) -> list[StakeholderView]:
        """
        Para cada stakeholder:
          1. Filtra campos_visiveis conforme perfil
          2. Adapta linguagem via LLM (temperatura 0.1)
          3. Persiste em output_stakeholders (se conn fornecido)
        """
        if not stakeholders:
            return []

        views: list[StakeholderView] = []
        close_conn = False

        if conn is None:
            url = os.getenv("DATABASE_URL")
            conn = psycopg2.connect(url)
            close_conn = True

        cur = conn.cursor()

        try:
            for stk in stakeholders:
                perfil = PERFIS_STAKEHOLDER[stk]
                resumo = self._adaptar_conteudo(stk, conteudo)
                campos = perfil["campos_visiveis"]

                cur.execute(
                    """
                    INSERT INTO output_stakeholders (output_id, stakeholder, resumo, campos_visiveis)
                    VALUES (%s, %s::stakeholder_tipo, %s, %s)
                    RETURNING id
                    """,
                    (output_id, stk.value, resumo, campos),
                )
                db_id = cur.fetchone()[0]
                conn.commit()

                views.append(StakeholderView(
                    output_id=output_id,
                    stakeholder=stk,
                    resumo=resumo,
                    campos_visiveis=campos,
                    db_id=db_id,
                ))
                logger.info("StakeholderView criada: output_id=%d stakeholder=%s", output_id, stk.value)
        finally:
            cur.close()
            if close_conn:
                conn.close()

        return views
