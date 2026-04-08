"""
tests/unit/test_detector_carimbo.py — Testes unitários do Detector de Carimbo léxico.

Verifica threshold, cálculo de similaridade, detecção e mensagens (G05).
Nenhuma chamada externa — stdlib apenas (difflib.SequenceMatcher).
"""

from src.cognitive.detector_carimbo import (
    THRESHOLD_CARIMBO,
    calcular_similaridade,
    detectar_carimbo,
)


def test_threshold_correto():
    assert THRESHOLD_CARIMBO == 0.70


def test_textos_identicos():
    r = calcular_similaridade("abc def ghi", "abc def ghi")
    assert r == 1.0


def test_textos_completamente_diferentes():
    r = calcular_similaridade("IBS CBS tributo reforma", "gato cachorro árvore jardim")
    assert r < 0.30


def test_carimbo_detectado():
    ia = "O crédito de IBS é aproveitável conforme art. 28 da LC 214/2025 sem restrições"
    gestor = "o credito de ibs é aproveitavel conforme art 28 da lc 214 2025 sem restricoes"
    resultado = detectar_carimbo(gestor, ia)
    assert resultado["carimbo_detectado"] is True
    assert resultado["similaridade"] >= THRESHOLD_CARIMBO
    assert resultado["mensagem"] != ""


def test_carimbo_nao_detectado():
    ia = "Recomendo aproveitar o crédito de IBS integralmente neste período de transição."
    gestor = "Prefiro aguardar regulamentação do CGIBS antes de aproveitar qualquer crédito."
    resultado = detectar_carimbo(gestor, ia)
    assert resultado["carimbo_detectado"] is False
    assert resultado["mensagem"] == ""


def test_texto_vazio_gestor():
    resultado = detectar_carimbo("", "recomendação da IA com conteúdo tributário")
    assert resultado["similaridade"] == 0.0
    assert resultado["carimbo_detectado"] is False


def test_texto_vazio_ia():
    resultado = detectar_carimbo("decisão do gestor sobre créditos", "")
    assert resultado["similaridade"] == 0.0
    assert resultado["carimbo_detectado"] is False


def test_normalizar_case_insensitive():
    r1 = calcular_similaridade("IBS CBS Tributo Reforma", "ibs cbs tributo reforma")
    assert r1 > 0.90


def test_mensagem_contem_percentual_quando_detectado():
    ia = "crédito aproveitável conforme legislação vigente sem ressalvas"
    gestor = "credito aproveitavel conforme legislacao vigente sem ressalvas"
    resultado = detectar_carimbo(gestor, ia)
    assert resultado["carimbo_detectado"] is True
    # Mensagem deve conter o percentual formatado
    assert "%" in resultado["mensagem"]


def test_similaridade_retorna_arredondada():
    r = calcular_similaridade("abc", "abc def ghi")
    assert isinstance(r, float)
    resultado = detectar_carimbo("abc", "abc def ghi")
    # Verificar que similaridade está arredondada a 4 casas
    assert resultado["similaridade"] == round(resultado["similaridade"], 4)
