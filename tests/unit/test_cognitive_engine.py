"""
tests/unit/test_cognitive_engine.py — testes do CognitiveEngine.
Testa apenas lógica isolada (sem chamar LLM nem banco onde possível).
"""

from dataclasses import dataclass, field
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

from src.cognitive.engine import (
    AntiAlucinacaoResult,
    _verificar_m4_consistencia,
)
from src.quality.engine import QualidadeResult, QualidadeStatus


# -----------------------------------------------------------------------
# 1. M1 falha: artigo inexistente → bloqueado = True
# -----------------------------------------------------------------------
def test_m1_falha_artigo_inexistente():
    """Verifica que artigos que não existem no banco geram flag M1:FALHA."""
    from src.cognitive.engine import _verificar_m1

    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    # Simular que o artigo não existe no banco
    mock_cur.fetchone.return_value = None

    fundamentos = ["Art. 9999 da LC 214/2025"]
    ok, flags = _verificar_m1(fundamentos, mock_conn)

    assert not ok
    assert any("M1:FALHA" in f for f in flags)


# -----------------------------------------------------------------------
# 2. M4: scoring alto + grau indefinido → flag M4:INCONSISTENCIA
# -----------------------------------------------------------------------
def test_m4_inconsistencia_scoring_alto_grau_indefinido():
    dados = {"scoring_confianca": "alto", "grau_consolidacao": "indefinido"}
    ok, flags = _verificar_m4_consistencia(dados)
    assert not ok
    assert "M4:INCONSISTENCIA" in flags


def test_m4_consistente_alto_consolidado():
    dados = {"scoring_confianca": "alto", "grau_consolidacao": "consolidado"}
    ok, flags = _verificar_m4_consistencia(dados)
    assert ok
    assert not flags


def test_m4_consistente_medio_indefinido():
    dados = {"scoring_confianca": "medio", "grau_consolidacao": "indefinido"}
    ok, flags = _verificar_m4_consistencia(dados)
    assert ok


# -----------------------------------------------------------------------
# 3. Resposta válida tem todos os campos obrigatórios
# -----------------------------------------------------------------------
def test_analise_result_campos_obrigatorios():
    """Garante que AnaliseResult tem todos os campos especificados."""
    from src.cognitive.engine import AnaliseResult
    import inspect

    fields = {f.name for f in AnaliseResult.__dataclass_fields__.values()}
    required = {
        "query", "chunks", "qualidade", "fundamento_legal",
        "grau_consolidacao", "contra_tese", "scoring_confianca",
        "resposta", "disclaimer", "anti_alucinacao",
        "prompt_version", "model_id", "latencia_ms",
    }
    assert required.issubset(fields), f"Campos faltando: {required - fields}"


# -----------------------------------------------------------------------
# Extra: AntiAlucinacaoResult inicializa com defaults corretos
# -----------------------------------------------------------------------
def test_anti_alucinacao_defaults():
    anti = AntiAlucinacaoResult()
    assert anti.m1_existencia is True
    assert anti.m2_validade is True
    assert anti.m3_pertinencia is True
    assert anti.m4_consistencia is True
    assert anti.bloqueado is False
    assert anti.flags == []
