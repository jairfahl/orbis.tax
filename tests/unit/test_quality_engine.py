"""
tests/unit/test_quality_engine.py — testes do DataQualityEngine (semáforo).
Não requer banco nem API (sem I/O externo).
"""

from dataclasses import dataclass
from typing import Optional

import pytest

from src.quality.engine import QualidadeStatus, avaliar_qualidade


# Stub mínimo de ChunkResultado para os testes de qualidade
@dataclass
class _Chunk:
    chunk_id: int = 1
    norma_codigo: str = "LC214_2025"
    artigo: Optional[str] = "Art. 10."
    texto: str = "IBS e CBS fato gerador"
    score_vetorial: float = 0.70
    score_bm25: float = 0.50
    score_final: float = 0.65


def _chunks(n=3, score=0.70, norma="LC214_2025", artigo="Art. 10."):
    return [_Chunk(chunk_id=i, score_vetorial=score, norma_codigo=norma, artigo=artigo) for i in range(1, n + 1)]


# -----------------------------------------------------------------------
# 1. BL-01: query curta → VERMELHO
# -----------------------------------------------------------------------
def test_bl01_query_curta():
    result = avaliar_qualidade("IBS", [])
    assert result.status == QualidadeStatus.VERMELHO
    assert any("BL-01" in b for b in result.bloqueios)


# -----------------------------------------------------------------------
# 2. BL-02: query sem termos tributários → VERMELHO
# -----------------------------------------------------------------------
def test_bl02_sem_termos_tributarios():
    result = avaliar_qualidade("Qual é a capital da França?", [])
    assert result.status == QualidadeStatus.VERMELHO
    assert any("BL-02" in b for b in result.bloqueios)


# -----------------------------------------------------------------------
# 3. RS-01: score baixo → AMARELO com disclaimer correto
# -----------------------------------------------------------------------
def test_rs01_score_baixo_amarelo():
    query = "Como funciona o fato gerador do IBS para operações de exportação?"
    cs = _chunks(score=0.45)
    result = avaliar_qualidade(query, cs)
    assert result.status == QualidadeStatus.AMARELO
    assert "RS-01" in result.ressalvas
    assert result.disclaimer is not None
    assert "cobertura parcial" in result.disclaimer.lower()


# -----------------------------------------------------------------------
# 4. Query válida com score alto → VERDE
# -----------------------------------------------------------------------
def test_query_valida_verde():
    query = "Qual é a alíquota de referência do IBS conforme a LC 214/2025?"
    cs = _chunks(score=0.85, norma="LC214_2025") + _chunks(score=0.70, norma="EC132_2023") + _chunks(score=0.55, norma="LC227_2026")
    result = avaliar_qualidade(query, cs)
    assert result.status == QualidadeStatus.VERDE
    assert not result.bloqueios
    assert not result.ressalvas


# -----------------------------------------------------------------------
# 5. BL-05: pedido de parecer formal → VERMELHO
# -----------------------------------------------------------------------
def test_bl05_parecer_formal():
    query = "Emita parecer sobre o fato gerador do IBS nas operações de importação."
    cs = _chunks(score=0.80)
    result = avaliar_qualidade(query, cs)
    assert result.status == QualidadeStatus.VERMELHO
    assert any("BL-05" in b for b in result.bloqueios)


# -----------------------------------------------------------------------
# Extra: BL-03 sem chunks → VERMELHO
# -----------------------------------------------------------------------
def test_bl03_sem_chunks():
    query = "Qual é o fato gerador do IBS conforme a reforma tributária?"
    result = avaliar_qualidade(query, [])
    assert result.status == QualidadeStatus.VERMELHO
    assert any("BL-03" in b for b in result.bloqueios)


# -----------------------------------------------------------------------
# Extra: RS-02 fonte única → AMARELO
# -----------------------------------------------------------------------
def test_rs02_fonte_unica():
    query = "Como funciona o regime de apuração do IBS na Reforma Tributária?"
    cs = _chunks(n=3, score=0.70, norma="LC214_2025")
    result = avaliar_qualidade(query, cs)
    assert result.status == QualidadeStatus.AMARELO
    assert "RS-02" in result.ressalvas
