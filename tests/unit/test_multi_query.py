"""
tests/unit/test_multi_query.py — Testes do Multi-Query Retrieval (RDM-024).

Zero chamadas externas.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import date

from src.rag.multi_query import (
    MULTI_QUERY_N,
    detectar_vocabulario_coloquial,
    executar_multi_query_fallback,
    gerar_variacoes_query,
    retrieve_multi_query,
)
from src.rag.retriever import ChunkResultado


def _chunk(chunk_id: int = 1, score_vetorial: float = 0.8,
           score_final: float = 0.75) -> ChunkResultado:
    return ChunkResultado(
        chunk_id=chunk_id,
        norma_codigo="LC214_2025",
        artigo="Art. 10",
        texto="Texto do chunk",
        score_vetorial=score_vetorial,
        score_bm25=0.5,
        score_final=score_final,
    )


class TestDetectarVocabularioColoquial:

    def test_imposto_novo_detectado(self):
        assert detectar_vocabulario_coloquial("minha empresa vai pagar imposto novo?") is True

    def test_cobrar_imposto_detectado(self):
        assert detectar_vocabulario_coloquial("como vão cobrar imposto sobre nota fiscal?") is True

    def test_taxa_nova_detectado(self):
        assert detectar_vocabulario_coloquial("existe taxa nova para prestadores de serviço?") is True

    def test_tributo_novo_detectado(self):
        assert detectar_vocabulario_coloquial("o tributo novo vai impactar minha empresa?") is True

    def test_query_tecnica_nao_detectada(self):
        q = "Qual a alíquota de IBS aplicável a operações de venda de mercadorias em 2028?"
        assert detectar_vocabulario_coloquial(q) is False

    def test_query_com_CBS_nao_detectada(self):
        assert detectar_vocabulario_coloquial("como funciona a CBS na reforma tributária?") is False

    def test_query_sem_termos_tecnicos_detectada(self):
        q = "quero saber sobre o tributo que vai mudar com a reforma do governo ano que vem"
        assert detectar_vocabulario_coloquial(q) is True

    def test_query_curta_sem_tecnico_nao_detectada(self):
        q = "o que muda"
        assert detectar_vocabulario_coloquial(q) is False

    def test_query_curta_com_indicador_detectada(self):
        q = "pagar imposto"
        assert detectar_vocabulario_coloquial(q) is True

    def test_query_com_split_payment_nao_detectada(self):
        q = "como funciona o split payment na reforma tributária brasileira?"
        assert detectar_vocabulario_coloquial(q) is False

    def test_query_com_fato_gerador_nao_detectada(self):
        q = "qual o fato gerador do imposto sobre bens e serviços na nova legislação?"
        assert detectar_vocabulario_coloquial(q) is False

    def test_query_vaga_longa_detectada(self):
        q = "quanto a empresa vai ter que desembolsar de imposto com essa mudança toda do governo"
        assert detectar_vocabulario_coloquial(q) is True


class TestGerarVariacoesQuery:

    @patch("src.rag.multi_query.anthropic.Anthropic")
    def test_gera_variacoes(self, mock_cls):
        mock_client = MagicMock()
        mock_cls.return_value = mock_client

        mock_resp = MagicMock()
        mock_resp.content = [MagicMock(text='{"variacoes": ["v1", "v2", "v3", "v4"]}')]
        mock_resp.usage.input_tokens = 50
        mock_resp.usage.output_tokens = 40
        mock_client.messages.create.return_value = mock_resp

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            variacoes = gerar_variacoes_query("pagar imposto novo", "claude-haiku-4-5-20251001")

        assert len(variacoes) == 4
        assert variacoes == ["v1", "v2", "v3", "v4"]

    @patch("src.rag.multi_query.anthropic.Anthropic")
    def test_json_invalido_retorna_query(self, mock_cls):
        mock_client = MagicMock()
        mock_cls.return_value = mock_client

        mock_resp = MagicMock()
        mock_resp.content = [MagicMock(text="isso não é json")]
        mock_resp.usage.input_tokens = 50
        mock_resp.usage.output_tokens = 10
        mock_client.messages.create.return_value = mock_resp

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            variacoes = gerar_variacoes_query("pagar imposto", "claude-haiku-4-5-20251001")

        assert variacoes == ["pagar imposto"]

    @patch("src.rag.multi_query.anthropic.Anthropic")
    def test_contexto_temporal_injetado(self, mock_cls):
        mock_client = MagicMock()
        mock_cls.return_value = mock_client

        mock_resp = MagicMock()
        mock_resp.content = [MagicMock(text='{"variacoes": ["v1"]}')]
        mock_resp.usage.input_tokens = 50
        mock_resp.usage.output_tokens = 10
        mock_client.messages.create.return_value = mock_resp

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            gerar_variacoes_query(
                "imposto novo em 2028", "claude-haiku-4-5-20251001",
                data_referencia=date(2028, 1, 1), regime="transicao",
            )

        call_kwargs = mock_client.messages.create.call_args[1]
        assert "2028" in call_kwargs["system"]
        assert "transicao" in call_kwargs["system"]

    @patch("src.rag.multi_query.anthropic.Anthropic")
    def test_limita_a_n_variacoes(self, mock_cls):
        mock_client = MagicMock()
        mock_cls.return_value = mock_client

        mock_resp = MagicMock()
        mock_resp.content = [MagicMock(text='{"variacoes": ["v1","v2","v3","v4","v5","v6"]}')]
        mock_resp.usage.input_tokens = 50
        mock_resp.usage.output_tokens = 30
        mock_client.messages.create.return_value = mock_resp

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            variacoes = gerar_variacoes_query("test", "claude-haiku-4-5-20251001")

        assert len(variacoes) == MULTI_QUERY_N


class TestRetrieveMultiQuery:

    @patch("src.rag.multi_query.retrieve")
    def test_fusao_deduplica_por_chunk_id(self, mock_retrieve):
        # Duas variações retornam o mesmo chunk com scores diferentes
        mock_retrieve.side_effect = [
            [_chunk(chunk_id=1, score_final=0.7)],
            [_chunk(chunk_id=1, score_final=0.9)],
        ]

        chunks, var_ok, total = retrieve_multi_query(["v1", "v2"])

        assert len(chunks) == 1
        assert chunks[0].score_final == 0.9  # mantém maior
        assert total == 2

    @patch("src.rag.multi_query.retrieve")
    def test_fusao_chunks_diferentes(self, mock_retrieve):
        mock_retrieve.side_effect = [
            [_chunk(chunk_id=1, score_final=0.8)],
            [_chunk(chunk_id=2, score_final=0.7)],
        ]

        chunks, var_ok, total = retrieve_multi_query(["v1", "v2"])

        assert len(chunks) == 2
        assert chunks[0].score_final >= chunks[1].score_final
        assert var_ok == 2

    @patch("src.rag.multi_query.retrieve")
    def test_variacao_com_erro_nao_impede(self, mock_retrieve):
        mock_retrieve.side_effect = [
            Exception("erro"),
            [_chunk(chunk_id=1, score_final=0.8)],
        ]

        chunks, var_ok, total = retrieve_multi_query(["v1", "v2"])

        assert len(chunks) == 1
        assert var_ok == 1

    @patch("src.rag.multi_query.retrieve")
    def test_ptf_propagado(self, mock_retrieve):
        mock_retrieve.return_value = [_chunk()]
        data_ref = date(2028, 1, 1)

        retrieve_multi_query(["v1"], data_referencia=data_ref)

        call_kwargs = mock_retrieve.call_args[1]
        assert call_kwargs["data_referencia"] == data_ref

    @patch("src.rag.multi_query.retrieve")
    def test_ordenacao_por_score_desc(self, mock_retrieve):
        mock_retrieve.side_effect = [
            [_chunk(chunk_id=3, score_final=0.5)],
            [_chunk(chunk_id=1, score_final=0.9)],
            [_chunk(chunk_id=2, score_final=0.7)],
        ]

        chunks, _, _ = retrieve_multi_query(["v1", "v2", "v3"])

        assert chunks[0].chunk_id == 1
        assert chunks[1].chunk_id == 2
        assert chunks[2].chunk_id == 3


class TestExecutarMultiQueryFallback:

    def test_query_tecnica_nao_ativa(self):
        chunks_iniciais = [_chunk()]
        chunks, ativado, count = executar_multi_query_fallback(
            query="Qual a alíquota de IBS em 2028?",
            chunks_iniciais=chunks_iniciais,
            model="claude-haiku-4-5-20251001",
        )
        assert ativado is False
        assert count == 0
        assert chunks == chunks_iniciais

    @patch("src.rag.multi_query.retrieve_multi_query")
    @patch("src.rag.multi_query.gerar_variacoes_query")
    def test_query_coloquial_ativa(self, mock_gerar, mock_retrieve_mq):
        chunks_iniciais = [_chunk()]
        mock_gerar.return_value = ["v1", "v2", "v3", "v4"]
        mock_retrieve_mq.return_value = ([_chunk(score_final=0.9)], 4, 20)

        chunks, ativado, count = executar_multi_query_fallback(
            query="minha empresa vai pagar imposto novo?",
            chunks_iniciais=chunks_iniciais,
            model="claude-haiku-4-5-20251001",
        )

        assert ativado is True
        assert count == 4

    @patch("src.rag.multi_query.gerar_variacoes_query", side_effect=Exception("LLM error"))
    def test_erro_retorna_chunks_iniciais(self, mock_gerar):
        chunks_iniciais = [_chunk()]
        chunks, ativado, count = executar_multi_query_fallback(
            query="pagar imposto novo",
            chunks_iniciais=chunks_iniciais,
            model="claude-haiku-4-5-20251001",
        )

        assert ativado is False
        assert count == 0
        assert chunks == chunks_iniciais

    @patch("src.rag.multi_query.retrieve_multi_query")
    @patch("src.rag.multi_query.gerar_variacoes_query")
    def test_sem_resultados_mantem_iniciais(self, mock_gerar, mock_retrieve_mq):
        chunks_iniciais = [_chunk()]
        mock_gerar.return_value = ["v1", "v2"]
        mock_retrieve_mq.return_value = ([], 0, 0)

        chunks, ativado, count = executar_multi_query_fallback(
            query="pagar imposto novo",
            chunks_iniciais=chunks_iniciais,
            model="claude-haiku-4-5-20251001",
        )

        assert ativado is False
        assert chunks == chunks_iniciais
