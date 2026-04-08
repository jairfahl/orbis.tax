"""
tests/unit/test_vigencia_checker.py — Testes unitários do Verificador de Vigência (G08).

Verifica marcos RT, status de vigência e integração com o checker de resposta.
Nenhuma chamada externa — datas fixas, stdlib apenas.
"""

from datetime import date

import pytest

from src.rag.vigencia_checker import (
    MARCOS_VIGENCIA_RT,
    AlertaVigencia,
    alertas_para_dict,
    verificar_vigencia_chunks,
    verificar_vigencia_norma,
    verificar_vigencia_resposta,
)


# ---------------------------------------------------------------------------
# verificar_vigencia_norma
# ---------------------------------------------------------------------------

def test_lc_214_vigente_em_2026():
    r = verificar_vigencia_norma("LC_214_2025", date(2026, 4, 1))
    assert r.status == "vigente"
    assert r.alerta is False


def test_cbs_teste_expirado_em_2027():
    r = verificar_vigencia_norma("CBS_TESTE", date(2027, 1, 1))
    assert r.status == "revogada"
    assert r.alerta is True


def test_split_payment_nao_vigente_em_2026():
    r = verificar_vigencia_norma("SPLIT_PAYMENT_OBRIGATORIO", date(2026, 4, 1))
    assert r.status == "nao_vigente_ainda"
    assert r.alerta is True


def test_nfe_debito_nao_vigente_antes_maio_2026():
    r = verificar_vigencia_norma("NFE_DEBITO_CREDITO", date(2026, 4, 1))
    assert r.status == "nao_vigente_ainda"
    assert r.alerta is True


def test_nfe_debito_vigente_apos_maio_2026():
    r = verificar_vigencia_norma("NFE_DEBITO_CREDITO", date(2026, 5, 5))
    assert r.status == "vigente"
    assert r.alerta is False


def test_norma_nao_mapeada():
    r = verificar_vigencia_norma("NORMA_INEXISTENTE", date(2026, 4, 1))
    assert r.status == "nao_mapeada"
    assert r.alerta is False


def test_alias_codigo_banco_ec_132():
    """Código do banco 'EC_132' deve resolver para 'EC_132_2023'."""
    r = verificar_vigencia_norma("EC_132", date(2026, 4, 1))
    assert r.status == "vigente"
    assert r.alerta is False


def test_alias_codigo_banco_lc_214():
    r = verificar_vigencia_norma("LC_214", date(2026, 4, 1))
    assert r.status == "vigente"
    assert r.alerta is False


# ---------------------------------------------------------------------------
# verificar_vigencia_resposta
# ---------------------------------------------------------------------------

def test_verificar_resposta_com_norma_vigente():
    resposta = "Conforme LC 214/2025, o creditamento de IBS é permitido."
    alertas = verificar_vigencia_resposta(resposta, date(2026, 4, 1))
    assert isinstance(alertas, list)
    # LC 214 está vigente em 2026 → sem alertas por ela
    alertas_codigos = [a.codigo for a in alertas]
    assert "LC_214_2025" not in alertas_codigos


def test_verificar_resposta_split_payment_em_2026():
    """Resposta mencionando split payment em data de 2026 deve gerar alerta."""
    resposta = "O split payment obrigatório se aplica a partir de 2027."
    alertas = verificar_vigencia_resposta(resposta, date(2026, 4, 1))
    alertas_codigos = [a.codigo for a in alertas]
    assert "SPLIT_PAYMENT_OBRIGATORIO" in alertas_codigos


def test_verificar_chunks_sem_normas_mapeadas():
    alertas = verificar_vigencia_chunks(["NORMA_DESCONHECIDA"], date(2026, 4, 1))
    assert alertas == []


def test_verificar_chunks_lc_214_vigente():
    alertas = verificar_vigencia_chunks(["LC_214"], date(2026, 4, 1))
    assert all(not a.alerta for a in alertas)


# ---------------------------------------------------------------------------
# MARCOS estrutura
# ---------------------------------------------------------------------------

def test_todos_marcos_tem_vigente_desde():
    for codigo, norma in MARCOS_VIGENCIA_RT.items():
        assert "vigente_desde" in norma, f"{codigo} sem vigente_desde"
        assert isinstance(norma["vigente_desde"], date), f"{codigo}: vigente_desde não é date"


def test_alertas_para_dict_serializa():
    alerta = AlertaVigencia(
        codigo="TEST",
        nome="Teste",
        status="nao_vigente_ainda",
        mensagem="⚠ Teste",
        alerta=True,
        vigente_desde="2027-01-01",
    )
    d = alertas_para_dict([alerta])
    assert len(d) == 1
    assert d[0]["codigo"] == "TEST"
    assert d[0]["alerta"] is True
