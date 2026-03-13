"""
rag/adaptive.py — Retrieval adaptativo por tipo de query.

Classifica queries em FACTUAL, INTERPRETATIVA ou COMPARATIVA via heurísticas
regex (sem chamada LLM) e ajusta parâmetros de retrieval para cada tipo.

Inspirado em: Adaptive RAG (LangGraph) — 500-AI-Agents-Projects.
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class QueryTipo(str, Enum):
    FACTUAL = "factual"
    INTERPRETATIVA = "interpretativa"
    COMPARATIVA = "comparativa"


@dataclass
class RetrievalParams:
    """Parâmetros ajustados de retrieval para o tipo de query."""
    top_k: int
    rerank_top_n: int
    cosine_weight: float
    bm25_weight: float
    forcar_multi_norma: bool = False


# Padrões regex para classificação
_PADROES_FACTUAL = [
    r'\bArt\.\s*\d+',                       # referência a artigo específico
    r'\balíquota\b.*\d',                     # alíquota com valor numérico
    r'\baliquota\b.*\d',
    r'\b\d+[,\.]\d+\s*%',                   # percentual explícito
    r'\b(NCM|CFOP|CNAE)\s*\d',              # códigos fiscais
    r'\bprazo\b.*\b\d{4}\b',               # prazo com ano
    r'\bdata\b.*\b\d{4}\b',                # data com ano
    r'\b(qual|quando)\b.*\balíquota\b',     # "qual a alíquota"
    r'\b(qual|quando)\b.*\baliquota\b',
]

_PADROES_COMPARATIVA = [
    r'\bdiferen[çc]a\b',
    r'\bcompar',
    r'\bversus\b',
    r'\b vs\.?\b',
    r'\bentre\b.*(EC|LC)\s*\d+.*\be\b.*(EC|LC)\s*\d+',  # "entre EC 132 e LC 214"
]

_PADROES_INTERPRETATIVA = [
    r'\bcomo\b',
    r'\bpor qu[eê]\b',
    r'\bqual\s+(o\s+)?impacto\b',
    r'\bqual\s+(o\s+)?efeito\b',
    r'\bde que forma\b',
    r'\bfunciona\b',
    r'\bexplique\b',
    r'\bimpact[ao]\b',
]


def classificar_query(query: str) -> QueryTipo:
    """
    Classifica a query por tipo usando heurísticas regex.

    Prioridade: COMPARATIVA > FACTUAL > INTERPRETATIVA (default).
    """
    q = query.strip()

    # Comparativa tem prioridade (pode conter termos factuais e interpretativos)
    for padrao in _PADROES_COMPARATIVA:
        if re.search(padrao, q, re.IGNORECASE):
            logger.info("Query classificada como COMPARATIVA: %s", q[:60])
            return QueryTipo.COMPARATIVA

    # Factual: referências específicas (artigos, alíquotas, códigos)
    for padrao in _PADROES_FACTUAL:
        if re.search(padrao, q, re.IGNORECASE):
            logger.info("Query classificada como FACTUAL: %s", q[:60])
            return QueryTipo.FACTUAL

    # Interpretativa: perguntas abertas
    for padrao in _PADROES_INTERPRETATIVA:
        if re.search(padrao, q, re.IGNORECASE):
            logger.info("Query classificada como INTERPRETATIVA: %s", q[:60])
            return QueryTipo.INTERPRETATIVA

    # Default: interpretativa (mais contexto é mais seguro)
    logger.info("Query sem padrão claro, default INTERPRETATIVA: %s", q[:60])
    return QueryTipo.INTERPRETATIVA


def obter_params_adaptativos(
    query: str,
    top_k_base: int = 5,
    rerank_top_n_base: int = 15,
) -> RetrievalParams:
    """
    Retorna parâmetros de retrieval ajustados ao tipo da query.

    Args:
        query: Texto da consulta.
        top_k_base: top_k padrão (usado como referência, não como valor fixo).
        rerank_top_n_base: rerank_top_n padrão.

    Returns:
        RetrievalParams com valores ajustados.
    """
    tipo = classificar_query(query)

    if tipo == QueryTipo.FACTUAL:
        return RetrievalParams(
            top_k=max(3, top_k_base - 2),
            rerank_top_n=max(10, rerank_top_n_base - 5),
            cosine_weight=0.8,
            bm25_weight=0.2,
        )

    if tipo == QueryTipo.COMPARATIVA:
        return RetrievalParams(
            top_k=top_k_base,
            rerank_top_n=rerank_top_n_base + 5,
            cosine_weight=0.7,
            bm25_weight=0.3,
            forcar_multi_norma=True,
        )

    # INTERPRETATIVA (default)
    return RetrievalParams(
        top_k=min(7, top_k_base + 2),
        rerank_top_n=rerank_top_n_base + 10,
        cosine_weight=0.6,
        bm25_weight=0.4,
    )
