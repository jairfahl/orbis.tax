"""
tests/integration/test_protocol_api.py — Testes de integração dos endpoints de protocolo.
Requer banco rodando com tabelas Sprint 3 criadas.
Executa com: pytest tests/integration/test_protocol_api.py -v
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from src.api.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def _criar_caso_fixture(titulo="Caso teste integração protocolo API", descricao="Descrição de teste",
                         contexto_fiscal="Lucro Presumido") -> int:
    """Cria um caso e retorna o case_id."""
    resp = client.post("/v1/cases", json={
        "titulo": titulo,
        "descricao": descricao,
        "contexto_fiscal": contexto_fiscal,
    })
    assert resp.status_code == 201, f"Falha ao criar caso: {resp.text}"
    return resp.json()["case_id"]


# ---------------------------------------------------------------------------
# 1. POST /v1/cases — criar caso válido
# ---------------------------------------------------------------------------
def test_criar_caso_valido():
    resp = client.post("/v1/cases", json={
        "titulo": "Caso de integração válido Sprint3",
        "descricao": "Descrição detalhada do caso",
        "contexto_fiscal": "Empresa de TI — Lucro Real",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert "case_id" in data
    assert data["status"] == "rascunho"
    assert data["passo_atual"] == 1
    assert isinstance(data["case_id"], int)
    assert data["case_id"] > 0


def test_criar_caso_titulo_curto():
    resp = client.post("/v1/cases", json={
        "titulo": "Curto",
        "descricao": "desc",
        "contexto_fiscal": "ctx",
    })
    assert resp.status_code in (422, 400), f"Esperado 422/400, obtido {resp.status_code}"


def test_criar_caso_campos_ausentes():
    resp = client.post("/v1/cases", json={"titulo": "Apenas título longo suficiente"})
    assert resp.status_code == 422  # Pydantic validation


# ---------------------------------------------------------------------------
# 2. GET /v1/cases/{case_id} — estado completo
# ---------------------------------------------------------------------------
def test_get_caso_existente():
    case_id = _criar_caso_fixture("Caso get estado completo teste")
    resp = client.get(f"/v1/cases/{case_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["case_id"] == case_id
    assert data["passo_atual"] == 1
    assert data["status"] == "rascunho"
    assert "steps" in data
    assert "historico" in data
    assert isinstance(data["historico"], list)
    assert len(data["historico"]) >= 1


def test_get_caso_inexistente():
    resp = client.get("/v1/cases/999999")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 3. POST /v1/cases/{case_id}/steps/{passo} — avanço de passo
# ---------------------------------------------------------------------------
def test_submeter_passo1_valido():
    case_id = _criar_caso_fixture("Caso submeter passo um valido teste")
    resp = client.post(f"/v1/cases/{case_id}/steps/1", json={
        "dados": {
            "titulo": "Caso submeter passo um valido teste",
            "descricao": "Descrição",
            "contexto_fiscal": "Lucro Presumido",
        },
        "acao": "avancar",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["passo"] == 2
    assert data["case_id"] == case_id


def test_submeter_passo1_dados_invalidos():
    case_id = _criar_caso_fixture("Caso dados invalidos passo 1 teste")
    resp = client.post(f"/v1/cases/{case_id}/steps/1", json={
        "dados": {
            "titulo": "Curto",  # < 10 chars → ProtocolError
            "descricao": "desc",
            "contexto_fiscal": "ctx",
        },
        "acao": "avancar",
    })
    assert resp.status_code == 422


def test_submeter_passo_voltar():
    case_id = _criar_caso_fixture("Caso voltar passo protocolo teste")
    # Avançar para P2
    client.post(f"/v1/cases/{case_id}/steps/1", json={
        "dados": {
            "titulo": "Caso voltar passo protocolo teste",
            "descricao": "desc",
            "contexto_fiscal": "ctx",
        },
        "acao": "avancar",
    })
    # Voltar para P1
    resp = client.post(f"/v1/cases/{case_id}/steps/2", json={
        "dados": {},
        "acao": "voltar",
    })
    assert resp.status_code == 200
    assert resp.json()["passo"] == 1


# ---------------------------------------------------------------------------
# 4. POST /v1/cases/{case_id}/carimbo/confirmar
# ---------------------------------------------------------------------------
def test_confirmar_carimbo_justificativa_curta():
    resp = client.post("/v1/cases/1/carimbo/confirmar", json={
        "alert_id": 1,
        "justificativa": "Curta",
    })
    assert resp.status_code == 422


def test_confirmar_carimbo_alert_inexistente():
    resp = client.post("/v1/cases/1/carimbo/confirmar", json={
        "alert_id": 999999,
        "justificativa": "Justificativa longa suficiente para o teste de protocolo",
    })
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 5. Fluxo completo P1→P3 (smoke test)
# ---------------------------------------------------------------------------
def test_fluxo_p1_p2_p3():
    case_id = _criar_caso_fixture("Fluxo completo P1 ate P3 smoke test")

    # P1 → P2
    r1 = client.post(f"/v1/cases/{case_id}/steps/1", json={
        "dados": {
            "titulo": "Fluxo completo P1 ate P3 smoke test",
            "descricao": "Descrição detalhada",
            "contexto_fiscal": "Lucro Real",
        },
        "acao": "avancar",
    })
    assert r1.status_code == 200
    assert r1.json()["passo"] == 2

    # P2 → P3
    r2 = client.post(f"/v1/cases/{case_id}/steps/2", json={
        "dados": {
            "premissas": ["Empresa optante pelo Lucro Real", "Período 2025-01 a 2025-12"],
            "periodo_fiscal": "2025-01 a 2025-12",
        },
        "acao": "avancar",
    })
    assert r2.status_code == 200
    assert r2.json()["passo"] == 3

    # P3 → P4
    r3 = client.post(f"/v1/cases/{case_id}/steps/3", json={
        "dados": {
            "riscos": ["Risco de autuação por alíquota incorreta"],
            "dados_qualidade": "Dados completos e auditados",
        },
        "acao": "avancar",
    })
    assert r3.status_code == 200
    assert r3.json()["passo"] == 4

    # Verificar estado final
    estado = client.get(f"/v1/cases/{case_id}").json()
    assert estado["passo_atual"] == 4
    assert estado["status"] == "em_analise"
    assert len(estado["historico"]) >= 4
