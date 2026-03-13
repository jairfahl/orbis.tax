"""
tests/unit/test_adaptive.py — Testes unitários para retrieval adaptativo.

Valida classificação de queries e parâmetros gerados por tipo.
Sem chamadas externas (puro regex/heurística).
"""

import pytest

from src.rag.adaptive import (
    QueryTipo,
    RetrievalParams,
    classificar_query,
    obter_params_adaptativos,
)


# ---------------------------------------------------------------------------
# Classificação de queries
# ---------------------------------------------------------------------------

class TestClassificarQuery:

    @pytest.mark.parametrize("query", [
        "Qual a alíquota do IBS em 2027?",
        "Art. 10 da LC 214/2025",
        "aliquota de 0,9% para CBS",
        "Qual o prazo de transição até 2032?",
        "NCM 2202 tem redução de alíquota?",
        "CFOP 5101 aplica split payment?",
    ])
    def test_factual(self, query):
        assert classificar_query(query) == QueryTipo.FACTUAL

    @pytest.mark.parametrize("query", [
        "Como funciona o split payment na reforma tributária?",
        "Por que o IBS substitui o ICMS?",
        "Qual o impacto da reforma para empresas de serviços?",
        "De que forma a CBS afeta o setor de saúde?",
        "Explique o cashback do IBS para famílias de baixa renda",
    ])
    def test_interpretativa(self, query):
        assert classificar_query(query) == QueryTipo.INTERPRETATIVA

    @pytest.mark.parametrize("query", [
        "Diferença entre EC 132 e LC 214 para serviços",
        "Compare o tratamento do Simples na EC 132/2023 e LC 214/2025",
        "IBS versus CBS: qual a distinção para importação?",
        "Diferença entre o regime atual e o novo regime tributário",
    ])
    def test_comparativa(self, query):
        assert classificar_query(query) == QueryTipo.COMPARATIVA

    def test_comparativa_tem_prioridade_sobre_factual(self):
        """Query com artigo + comparação deve ser COMPARATIVA."""
        query = "Diferença entre Art. 10 da LC 214 e Art. 5 da EC 132"
        assert classificar_query(query) == QueryTipo.COMPARATIVA

    def test_query_generica_default_interpretativa(self):
        """Query sem padrões reconhecidos → INTERPRETATIVA (mais seguro)."""
        query = "reforma tributária Brasil"
        assert classificar_query(query) == QueryTipo.INTERPRETATIVA


# ---------------------------------------------------------------------------
# Parâmetros adaptativos
# ---------------------------------------------------------------------------

class TestObterParamsAdaptativos:

    def test_factual_menos_chunks_mais_cosine(self):
        params = obter_params_adaptativos("Qual a alíquota do IBS?", top_k_base=5)
        assert params.top_k <= 5
        assert params.cosine_weight > 0.7
        assert params.bm25_weight < 0.3
        assert not params.forcar_multi_norma

    def test_interpretativa_mais_chunks_mais_bm25(self):
        params = obter_params_adaptativos("Como funciona o split payment?", top_k_base=5)
        assert params.top_k >= 5
        assert params.cosine_weight < 0.7
        assert params.bm25_weight > 0.3
        assert not params.forcar_multi_norma

    def test_comparativa_forca_multi_norma(self):
        params = obter_params_adaptativos("Diferença entre EC 132 e LC 214")
        assert params.forcar_multi_norma is True

    def test_pesos_somam_um(self):
        """Pesos cosine + bm25 devem somar 1.0 para todos os tipos."""
        queries = [
            "Art. 10 da LC 214",
            "Como funciona o cashback?",
            "Diferença entre IBS e CBS",
        ]
        for q in queries:
            params = obter_params_adaptativos(q)
            assert abs(params.cosine_weight + params.bm25_weight - 1.0) < 1e-9

    def test_top_k_minimo_3(self):
        """top_k nunca deve ser menor que 3, mesmo com base baixo."""
        params = obter_params_adaptativos("Qual a alíquota do IBS?", top_k_base=3)
        assert params.top_k >= 3

    def test_respeita_top_k_base(self):
        """Parâmetros adaptativos devem ser relativos ao top_k_base."""
        params_5 = obter_params_adaptativos("Como funciona o cashback?", top_k_base=5)
        params_8 = obter_params_adaptativos("Como funciona o cashback?", top_k_base=8)
        assert params_8.top_k >= params_5.top_k
