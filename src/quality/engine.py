"""
quality/engine.py — DataQualityEngine: semáforo de 3 níveis para contexto RAG.

Avalia a consulta + chunks recuperados antes de chamar o LLM.
Status: VERDE (ok) | AMARELO (ressalva) | VERMELHO (bloqueado)
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)

# Termos que indicam contexto tributário
TERMOS_TRIBUTARIOS = [
    "ibs", "cbs", "icms", "iss", "imposto", "tributo", "alíquota", "aliquota",
    "base de cálculo", "base de calculo", "contribuinte", "fato gerador",
    "crédito", "credito", "débito", "debito", "apuração", "apuracao",
    "regime", "nota fiscal", "reforma tributária", "reforma tributaria",
    "ipi", "pis", "cofins", "irpj", "csll", "simples nacional",
    "split payment", "pagamento fracionado", "recolhimento", "fiscal",
    "tributação", "tributacao", "incidência", "incidencia", "arrecadação",
    "arrecadacao", "cashback", "não cumulatividade", "nao cumulatividade",
]

TERMOS_PARECER = [
    "emita parecer", "lavre parecer", "assine parecer",
    "elabore parecer", "redija parecer",
]


class QualidadeStatus(str, Enum):
    VERDE = "verde"
    AMARELO = "amarelo"
    VERMELHO = "vermelho"


@dataclass
class QualidadeResult:
    status: QualidadeStatus
    regras_ok: list[str] = field(default_factory=list)
    bloqueios: list[str] = field(default_factory=list)
    ressalvas: list[str] = field(default_factory=list)
    disclaimer: Optional[str] = None


def _tem_termos_tributarios(query: str) -> bool:
    q = query.lower()
    return any(t in q for t in TERMOS_TRIBUTARIOS)


def _tem_pedido_parecer(query: str) -> bool:
    q = query.lower()
    return any(t in q for t in TERMOS_PARECER)


def _menciona_periodo_anterior_2024(query: str) -> bool:
    anos = re.findall(r'\b(19\d{2}|20[01]\d|202[0-3])\b', query)
    return bool(anos)


def avaliar_qualidade(
    query: str,
    chunks: list,
) -> QualidadeResult:
    """
    Aplica todas as regras de bloqueio e ressalva.

    Args:
        query: texto da consulta
        chunks: lista de ChunkResultado (pode ser vazia)

    Returns:
        QualidadeResult com status, bloqueios e ressalvas.
    """
    bloqueios: list[str] = []
    ressalvas: list[str] = []
    regras_ok: list[str] = []
    disclaimers: list[str] = []

    # --- REGRAS DE BLOQUEIO ---

    # BL-01: query muito curta
    if len(query.strip()) < 10:
        bloqueios.append("BL-01: Query com menos de 10 caracteres")
    else:
        regras_ok.append("BL-01")

    # BL-02: sem contexto tributário
    if not _tem_termos_tributarios(query):
        bloqueios.append("BL-02: Query sem contexto tributário identificável")
    else:
        regras_ok.append("BL-02")

    # BL-03: nenhum chunk recuperado
    if not chunks:
        bloqueios.append("BL-03: Nenhum chunk recuperado pelo RAG")
    else:
        regras_ok.append("BL-03")

    # BL-04: score vetorial máximo < 0.30
    if chunks:
        max_score = max(c.score_vetorial for c in chunks)
        if max_score < 0.30:
            bloqueios.append(f"BL-04: Score vetorial máximo {max_score:.3f} < 0.30")
        else:
            regras_ok.append("BL-04")

    # BL-05: pedido de parecer formal
    if _tem_pedido_parecer(query):
        bloqueios.append("BL-05: Query contém pedido de parecer jurídico formal")
    else:
        regras_ok.append("BL-05")

    # Se há bloqueios, retornar imediatamente VERMELHO
    if bloqueios:
        logger.info("Qualidade VERMELHO: %s", bloqueios)
        return QualidadeResult(
            status=QualidadeStatus.VERMELHO,
            regras_ok=regras_ok,
            bloqueios=bloqueios,
            ressalvas=[],
            disclaimer=None,
        )

    # --- REGRAS DE RESSALVA ---

    if chunks:
        max_score = max(c.score_vetorial for c in chunks)

        # RS-01: score vetorial máximo < 0.55
        if max_score < 0.55:
            ressalvas.append("RS-01")
            disclaimers.append(
                "Fundamentação legislativa com cobertura parcial. "
                "Recomenda-se validação adicional."
            )
        else:
            regras_ok.append("RS-01")

        # RS-02: todos chunks de apenas 1 norma
        normas_presentes = {c.norma_codigo for c in chunks}
        if len(normas_presentes) == 1:
            ressalvas.append("RS-02")
            disclaimers.append(
                "Análise baseada em fonte única. Verifique normas complementares."
            )
        else:
            regras_ok.append("RS-02")

        # RS-04: nenhum artigo identificado
        if all(c.artigo is None for c in chunks):
            ressalvas.append("RS-04")
            disclaimers.append(
                "Trechos recuperados sem identificação precisa de artigo. "
                "Grounding pode ser impreciso."
            )
        else:
            regras_ok.append("RS-04")

    # RS-03: query menciona período anterior a 2024
    if _menciona_periodo_anterior_2024(query):
        ressalvas.append("RS-03")
        disclaimers.append(
            "Normas de transição podem se aplicar. "
            "Verifique vigência para o período consultado."
        )
    else:
        regras_ok.append("RS-03")

    # RS-05: múltiplas normas com possível conflito (heurística: >1 norma e score baixo)
    if chunks and len({c.norma_codigo for c in chunks}) > 1:
        scores = [c.score_vetorial for c in chunks]
        if round(max(scores) - min(scores), 4) < 0.10:
            ressalvas.append("RS-05")
            disclaimers.append(
                "Possível conflito normativo identificado. "
                "Contra-tese gerada automaticamente."
            )
        else:
            regras_ok.append("RS-05")
    else:
        regras_ok.append("RS-05")

    if ressalvas:
        status = QualidadeStatus.AMARELO
        disclaimer = " | ".join(disclaimers) if disclaimers else None
    else:
        status = QualidadeStatus.VERDE
        disclaimer = None

    logger.info("Qualidade %s: bloqueios=%s ressalvas=%s", status, bloqueios, ressalvas)
    return QualidadeResult(
        status=status,
        regras_ok=regras_ok,
        bloqueios=bloqueios,
        ressalvas=ressalvas,
        disclaimer=disclaimer,
    )
