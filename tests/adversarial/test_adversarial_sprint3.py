"""
tests/adversarial/test_adversarial_sprint3.py — Testes adversariais Sprint 3.
Validam comportamentos críticos de segurança e integridade do protocolo.
Executa com: pytest tests/adversarial/test_adversarial_sprint3.py -v

Requer banco rodando. Alguns testes envolvem chamadas reais à API.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from src.api.main import app
from src.protocol.engine import ProtocolError, ProtocolStateEngine, _validar_dados_passo
from src.protocol.carimbo import CarimboConfirmacaoError, DetectorCarimbo, _cosseno

client = TestClient(app)


# ---------------------------------------------------------------------------
# A1 — Salto de passo (tentar ir de P1 direto para P3)
# ---------------------------------------------------------------------------
def test_a1_nao_permite_salto_de_passo():
    """
    Adversarial: tentar avançar P1 com dados de P3 não deve pular para P3.
    O passo de destino é sempre determinado pelas transições, não pelos dados.
    """
    resp = client.post("/v1/cases", json={
        "titulo": "A1 teste salto de passo adversarial",
        "descricao": "desc",
        "contexto_fiscal": "ctx",
    })
    assert resp.status_code == 201
    case_id = resp.json()["case_id"]

    # Submeter P1 com dados válidos — deve ir para P2, não P3
    resp2 = client.post(f"/v1/cases/{case_id}/steps/1", json={
        "dados": {
            "titulo": "A1 teste salto de passo adversarial",
            "descricao": "desc",
            "contexto_fiscal": "ctx",
            "riscos": ["risco falso"],  # campo de P3 injetado
        },
        "acao": "avancar",
    })
    assert resp2.status_code == 200
    assert resp2.json()["passo"] == 2, "Deve avançar para P2, não saltar para P3"


# ---------------------------------------------------------------------------
# A2 — P6 bloqueado sem P5 (gestor não pode ver recomendação antes da hipótese)
# ---------------------------------------------------------------------------
def test_a2_p6_bloqueado_sem_p5():
    """
    Adversarial: tentar avançar para P6 sem concluir P5 deve ser bloqueado.
    Regra crítica de integridade cognitiva.
    """
    engine = ProtocolStateEngine()
    case_id = engine.criar_caso(
        titulo="A2 teste bloqueio P6 sem P5 hipotese",
        descricao="desc",
        contexto_fiscal="ctx",
    )
    # Avançar até P5
    engine.avancar(case_id, 1, {
        "titulo": "A2 teste bloqueio P6 sem P5 hipotese",
        "descricao": "desc",
        "contexto_fiscal": "ctx",
    })
    engine.avancar(case_id, 2, {
        "premissas": ["p1", "p2"],
        "periodo_fiscal": "2025",
    })
    engine.avancar(case_id, 3, {
        "riscos": ["risco fiscal"],
        "dados_qualidade": "ok",
    })
    engine.avancar(case_id, 4, {
        "query_analise": "query",
        "analise_result": "resultado",
    })

    # Verificar via pode_avancar
    pode, motivo = engine.pode_avancar(case_id, 5)
    assert not pode, "P6 não deve ser permitido sem P5 concluído"

    # Tentar avançar diretamente deve lançar ProtocolError
    with pytest.raises(ProtocolError):
        engine.avancar(case_id, 5, {"hipotese_gestor": ""})  # campo vazio → bloqueio


# ---------------------------------------------------------------------------
# A3 — Injeção de dados nulos / vazios em campos obrigatórios
# ---------------------------------------------------------------------------
def test_a3_campos_nulos_bloqueados():
    """
    Adversarial: submeter campos com valores None/vazio deve ser bloqueado.
    """
    resp = client.post("/v1/cases", json={
        "titulo": "A3 campos nulos adversarial teste",
        "descricao": "desc",
        "contexto_fiscal": "ctx",
    })
    case_id = resp.json()["case_id"]

    # Tentar avançar P1 com titulo nulo
    resp2 = client.post(f"/v1/cases/{case_id}/steps/1", json={
        "dados": {
            "titulo": "",
            "descricao": "desc",
            "contexto_fiscal": "ctx",
        },
        "acao": "avancar",
    })
    assert resp2.status_code == 422, "Campos vazios devem ser rejeitados"


# ---------------------------------------------------------------------------
# A4 — Carimbo não dispara com decisões independentes (score < 0.70)
# ---------------------------------------------------------------------------
@patch("src.protocol.carimbo._embed")
def test_a4_carimbo_nao_dispara_decisao_independente(mock_embed):
    """
    Adversarial: decisão genuinamente diferente da recomendação não deve
    acionar o alerta de carimbo.
    """
    # Vetores ortogonais = decisão totalmente diferente
    mock_embed.side_effect = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]

    detector = DetectorCarimbo()
    result = detector.verificar(
        case_id=999,
        passo=7,
        texto_decisao="Optamos por não adotar nenhuma das recomendações da IA.",
        texto_recomendacao="Recomendamos adotar o regime tributário simplificado do IBS.",
    )
    assert not result.alerta, "Decisão independente não deve acionar carimbo"
    assert result.score_similaridade < 0.70


# ---------------------------------------------------------------------------
# A5 — Carimbo dispara e exige justificativa mínima
# ---------------------------------------------------------------------------
@patch("src.protocol.carimbo._embed")
@patch("src.protocol.carimbo.psycopg2.connect")
def test_a5_carimbo_exige_justificativa_minima(mock_connect, mock_embed):
    """
    Adversarial: após alerta de carimbo, justificativa curta deve ser rejeitada.
    """
    mock_embed.side_effect = [[1.0, 0.0], [0.98, 0.02]]
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    mock_cur.fetchone.return_value = (7,)
    mock_connect.return_value = mock_conn

    detector = DetectorCarimbo()
    result = detector.verificar(
        case_id=1,
        passo=7,
        texto_decisao="Adotamos integralmente a recomendação do sistema.",
        texto_recomendacao="Recomendamos adotar integralmente a decisão tributária.",
    )
    assert result.alerta

    # Justificativa abaixo do mínimo deve falhar
    with pytest.raises(CarimboConfirmacaoError):
        detector.confirmar(result.alert_id, "Curta")


# ---------------------------------------------------------------------------
# A6 — Retrocesso não apaga dados de passos anteriores
# ---------------------------------------------------------------------------
def test_a6_retrocesso_preserva_dados_passos_anteriores():
    """
    Adversarial: voltar de P2 para P1 não deve apagar os dados já salvos em P1.
    """
    engine = ProtocolStateEngine()
    case_id = engine.criar_caso(
        titulo="A6 retrocesso preserva dados anteriores",
        descricao="desc",
        contexto_fiscal="ctx",
    )
    # Avançar para P2
    engine.avancar(case_id, 1, {
        "titulo": "A6 retrocesso preserva dados anteriores",
        "descricao": "desc",
        "contexto_fiscal": "ctx",
    })
    # Voltar para P1
    engine.voltar(case_id, 2)
    # Verificar que os dados de P1 ainda existem
    estado = engine.get_estado(case_id)
    assert 1 in estado.steps, "Dados do P1 devem ser preservados após retrocesso"
    dados_p1 = estado.steps[1].get("dados", {})
    # Os dados salvos devem conter o título
    if isinstance(dados_p1, dict):
        assert dados_p1.get("titulo") == "A6 retrocesso preserva dados anteriores"
