"""
tests/unit/test_retry.py — Testes unitários para StructuredRetry.

Sem chamadas externas — testa lógica de retry, validação e clamping.
"""

import json

import pytest

from src.cognitive.retry import StructuredRetry


def _make_llm_fn(responses: list[str]):
    """Cria uma função LLM mock que retorna respostas em sequência."""
    call_count = [0]

    def fn(instrucao_extra="", **kwargs):
        idx = min(call_count[0], len(responses) - 1)
        call_count[0] += 1
        return responses[idx]

    fn.call_count = call_count
    return fn


class TestStructuredRetry:

    def test_json_valido_primeira_tentativa(self):
        retry = StructuredRetry()
        llm_fn = _make_llm_fn(['{"resposta": "ok", "score": 0.8}'])
        result = retry.executar(llm_fn)
        assert result["resposta"] == "ok"
        assert llm_fn.call_count[0] == 1

    def test_json_invalido_retry_sucesso(self):
        retry = StructuredRetry(max_retries_parse=2)
        llm_fn = _make_llm_fn([
            "isso não é json",
            '{"resposta": "corrigido"}',
        ])
        result = retry.executar(llm_fn)
        assert result["resposta"] == "corrigido"
        assert llm_fn.call_count[0] == 2

    def test_json_invalido_todos_retries_falham(self):
        retry = StructuredRetry(max_retries_parse=1)
        llm_fn = _make_llm_fn(["não é json", "ainda não é json"])
        with pytest.raises(RuntimeError, match="JSON inválido"):
            retry.executar(llm_fn)

    def test_campos_obrigatorios_presentes(self):
        retry = StructuredRetry(campos_obrigatorios=["resposta", "score"])
        llm_fn = _make_llm_fn(['{"resposta": "ok", "score": 0.9}'])
        result = retry.executar(llm_fn)
        assert "resposta" in result
        assert "score" in result

    def test_campos_obrigatorios_faltantes_retry(self):
        retry = StructuredRetry(
            campos_obrigatorios=["resposta", "score"],
            max_retries_schema=1,
        )
        llm_fn = _make_llm_fn([
            '{"resposta": "ok"}',  # falta score
            '{"resposta": "ok", "score": 0.8}',  # completo
        ])
        result = retry.executar(llm_fn)
        assert "score" in result

    def test_clamping_valor_acima_range(self):
        retry = StructuredRetry(ranges={"nivel_confianca": (0.0, 1.0)})
        llm_fn = _make_llm_fn(['{"nivel_confianca": 1.5}'])
        result = retry.executar(llm_fn)
        assert result["nivel_confianca"] == 1.0

    def test_clamping_valor_abaixo_range(self):
        retry = StructuredRetry(ranges={"nivel_confianca": (0.0, 1.0)})
        llm_fn = _make_llm_fn(['{"nivel_confianca": -0.3}'])
        result = retry.executar(llm_fn)
        assert result["nivel_confianca"] == 0.0

    def test_clamping_valor_dentro_range_nao_altera(self):
        retry = StructuredRetry(ranges={"nivel_confianca": (0.0, 1.0)})
        llm_fn = _make_llm_fn(['{"nivel_confianca": 0.7}'])
        result = retry.executar(llm_fn)
        assert result["nivel_confianca"] == 0.7

    def test_markdown_code_fence_tolerado(self):
        retry = StructuredRetry()
        llm_fn = _make_llm_fn(['```json\n{"resposta": "ok"}\n```'])
        result = retry.executar(llm_fn)
        assert result["resposta"] == "ok"

    def test_instrucao_extra_passada_no_retry(self):
        """Verifica que instrucao_extra é passada na segunda chamada."""
        instrucoes_recebidas = []

        def llm_fn(instrucao_extra="", **kwargs):
            instrucoes_recebidas.append(instrucao_extra)
            if len(instrucoes_recebidas) == 1:
                return "não é json"
            return '{"ok": true}'

        retry = StructuredRetry(max_retries_parse=1)
        retry.executar(llm_fn)
        assert instrucoes_recebidas[0] == ""
        assert "JSON válido" in instrucoes_recebidas[1]

    def test_range_campo_inexistente_ignorado(self):
        retry = StructuredRetry(ranges={"campo_fantasma": (0, 10)})
        llm_fn = _make_llm_fn(['{"outro": 5}'])
        result = retry.executar(llm_fn)
        assert "campo_fantasma" not in result

    def test_range_valor_nao_numerico_ignorado(self):
        retry = StructuredRetry(ranges={"score": (0, 1)})
        llm_fn = _make_llm_fn(['{"score": "alto"}'])
        result = retry.executar(llm_fn)
        assert result["score"] == "alto"  # não tenta clampar string
