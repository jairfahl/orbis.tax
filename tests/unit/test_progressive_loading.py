"""
Testes unitários para progressive loading de system prompts.
Zero chamadas externas — tudo com mocks/fixtures.
"""

import pytest

from src.rag.prompt_loader import (
    PromptLoadResult,
    carregar_secoes_prompt,
    gerar_context_budget_log,
)


PROMPT_COM_SECOES = """## [SUMMARY]
Você é um especialista em tributação. Regras essenciais aqui.
Formato JSON obrigatório.

## [FULL]
Linguagem corporativa detalhada. Estilo do campo resposta.
Exemplos formatados e proibidos. Few-shot completo.
Regras adicionais de estilo e formatação.

## [FULL:antialucinacao]
M1-EXISTÊNCIA: cite apenas artigos dos trechos.
M2-VALIDADE: verifique vigência.
M3-PERTINÊNCIA: declare limitação se score baixo.
M4-CONSISTÊNCIA: coerência entre scoring e grau.
"""

PROMPT_SEM_SECOES = """Você é um assistente tributário.
Responda em JSON com os campos: resposta, fundamento_legal, nivel_confianca.
Nunca invente artigos."""


class TestCarregarSecoesPrompt:

    def test_factual_apenas_summary(self):
        result = carregar_secoes_prompt(PROMPT_COM_SECOES, "FACTUAL", "VERDE")
        assert "SUMMARY" in result.secoes_carregadas
        assert "FULL" not in result.secoes_carregadas
        assert "FULL:antialucinacao" not in result.secoes_carregadas
        assert "especialista em tributação" in result.conteudo_carregado
        assert "Linguagem corporativa" not in result.conteudo_carregado
        assert "M1-EXISTÊNCIA" not in result.conteudo_carregado

    def test_interpretativa_summary_e_full(self):
        result = carregar_secoes_prompt(PROMPT_COM_SECOES, "INTERPRETATIVA", "VERDE")
        assert "SUMMARY" in result.secoes_carregadas
        assert "FULL" in result.secoes_carregadas
        assert "FULL:antialucinacao" not in result.secoes_carregadas
        assert "especialista em tributação" in result.conteudo_carregado
        assert "Linguagem corporativa" in result.conteudo_carregado
        assert "M1-EXISTÊNCIA" not in result.conteudo_carregado

    def test_comparativa_todas_secoes(self):
        result = carregar_secoes_prompt(PROMPT_COM_SECOES, "COMPARATIVA", "VERDE")
        assert "SUMMARY" in result.secoes_carregadas
        assert "FULL" in result.secoes_carregadas
        assert "FULL:antialucinacao" in result.secoes_carregadas
        assert "especialista em tributação" in result.conteudo_carregado
        assert "Linguagem corporativa" in result.conteudo_carregado
        assert "M1-EXISTÊNCIA" in result.conteudo_carregado

    def test_quality_gate_amarelo_forca_antialucinacao(self):
        result = carregar_secoes_prompt(PROMPT_COM_SECOES, "FACTUAL", "AMARELO")
        assert "SUMMARY" in result.secoes_carregadas
        assert "FULL:antialucinacao" in result.secoes_carregadas
        assert "M1-EXISTÊNCIA" in result.conteudo_carregado

    def test_retrocompatibilidade_sem_delimitadores(self):
        result = carregar_secoes_prompt(PROMPT_SEM_SECOES, "COMPARATIVA", "VERMELHO")
        assert result.retrocompativel is True
        assert result.conteudo_carregado == PROMPT_SEM_SECOES
        assert "ALL" in result.secoes_carregadas


class TestContextBudgetLog:

    def test_gera_log_estruturado(self):
        load_result = PromptLoadResult(
            conteudo_carregado="conteudo",
            secoes_carregadas=["SUMMARY", "FULL"],
            tokens_por_secao={"SUMMARY": 100, "FULL": 200},
        )
        log = gerar_context_budget_log(
            prompt_version="v1.0.0",
            query_tipo="INTERPRETATIVA",
            load_result=load_result,
            chunks_texto="chunk1 chunk2 chunk3",
        )
        assert "[PROMPT:COMPOSE:START]" in log
        assert "v1.0.0" in log
        assert "[SECTION:LOADED] [SUMMARY] 100 tokens" in log
        assert "[SECTION:LOADED] [FULL] 200 tokens" in log
        assert "[RAG:CHUNKS]" in log
        assert "[PROMPT:COMPOSE:COMPLETE]" in log
        assert "Budget disponivel:" in log

    def test_quality_gate_vermelho_forca_antialucinacao(self):
        result = carregar_secoes_prompt(PROMPT_COM_SECOES, "INTERPRETATIVA", "VERMELHO")
        assert "FULL:antialucinacao" in result.secoes_carregadas
