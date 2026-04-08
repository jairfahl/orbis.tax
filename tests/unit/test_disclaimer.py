"""
tests/unit/test_disclaimer.py — Testes unitários do disclaimer obrigatório (D2, G15).
"""

from src.outputs.disclaimer import (
    DISCLAIMER_COMPACTO,
    DISCLAIMER_DOSSIE,
    DISCLAIMER_TEXTO,
    obter_disclaimer,
    validar_disclaimer_presente,
)


def test_disclaimer_padrao_nao_vazio():
    assert len(DISCLAIMER_TEXTO) > 50


def test_disclaimer_contem_termos_obrigatorios():
    assert "não constitui parecer" in DISCLAIMER_TEXTO.lower()
    assert "responsabilidade do profissional" in DISCLAIMER_TEXTO.lower()
    assert "inteligência artificial" in DISCLAIMER_TEXTO.lower()


def test_obter_disclaimer_padrao():
    assert obter_disclaimer("padrao") == DISCLAIMER_TEXTO


def test_obter_disclaimer_compacto():
    d = obter_disclaimer("compacto")
    assert d == DISCLAIMER_COMPACTO
    assert len(d) < len(DISCLAIMER_TEXTO)


def test_obter_disclaimer_dossie():
    d = obter_disclaimer("dossie")
    assert d == DISCLAIMER_DOSSIE
    assert len(d) > len(DISCLAIMER_TEXTO)


def test_obter_disclaimer_modo_invalido_retorna_padrao():
    assert obter_disclaimer("inexistente") == DISCLAIMER_TEXTO


def test_validar_presente_quando_tem_inteligencia_artificial():
    texto = "Análise gerada por inteligência artificial com base legal."
    assert validar_disclaimer_presente(texto) is True


def test_validar_ausente_quando_sem_disclaimer():
    texto = "Análise sobre CBS e IBS na transição 2026."
    assert validar_disclaimer_presente(texto) is False


def test_validar_presente_com_responsabilidade_do_profissional():
    texto = "A decisão é responsabilidade do profissional competente."
    assert validar_disclaimer_presente(texto) is True


def test_disclaimer_dossie_contem_aviso_legal():
    assert "AVISO LEGAL" in DISCLAIMER_DOSSIE
    assert len(DISCLAIMER_DOSSIE) > len(DISCLAIMER_TEXTO)
