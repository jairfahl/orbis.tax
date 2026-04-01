"""
tests/unit/test_hyde.py — Testes do HyDE: Hypothetical Document Embeddings (RDM-020).

Zero chamadas externas. Testa lógica de ativação e fallback.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import date

from src.rag.hyde import (
    HYDE_THRESHOLD_SCORE,
    HYDE_TIPOS_ELEGIVEIS,
    deve_ativar_hyde,
    executar_hyde_fallback,
    gerar_documento_hipotetico,
    retrieve_com_hyde,
)
from src.rag.retriever import ChunkResultado


def _chunk(score_vetorial: float = 0.8, score_final: float = 0.75,
           texto: str = "Texto do chunk") -> ChunkResultado:
    return ChunkResultado(
        chunk_id=1,
        norma_codigo="LC214_2025",
        artigo="Art. 10",
        texto=texto,
        score_vetorial=score_vetorial,
        score_bm25=0.5,
        score_final=score_final,
    )


class TestDeveAtivarHyde:

    def test_factual_nunca_ativa(self):
        chunks = [_chunk(score_vetorial=0.65)]
        assert deve_ativar_hyde("FACTUAL", chunks) is False

    def test_comparativa_nunca_ativa(self):
        chunks = [_chunk(score_vetorial=0.60)]
        assert deve_ativar_hyde("COMPARATIVA", chunks) is False

    def test_interpretativa_score_baixo_ativa(self):
        chunks = [_chunk(score_vetorial=0.65), _chunk(score_vetorial=0.60)]
        assert deve_ativar_hyde("INTERPRETATIVA", chunks) is True

    def test_interpretativa_score_alto_nao_ativa(self):
        chunks = [_chunk(score_vetorial=0.80), _chunk(score_vetorial=0.75)]
        assert deve_ativar_hyde("INTERPRETATIVA", chunks) is False

    def test_interpretativa_score_exato_threshold_nao_ativa(self):
        chunks = [_chunk(score_vetorial=HYDE_THRESHOLD_SCORE)]
        assert deve_ativar_hyde("INTERPRETATIVA", chunks) is False

    def test_interpretativa_sem_chunks_ativa(self):
        assert deve_ativar_hyde("INTERPRETATIVA", []) is True

    def test_interpretativa_score_abaixo_threshold_ativa(self):
        chunks = [_chunk(score_vetorial=HYDE_THRESHOLD_SCORE - 0.01)]
        assert deve_ativar_hyde("INTERPRETATIVA", chunks) is True

    def test_interpretativa_minuscula_funciona(self):
        chunks = [_chunk(score_vetorial=0.65)]
        assert deve_ativar_hyde("interpretativa", chunks) is True

    def test_factual_minuscula_nao_ativa(self):
        chunks = [_chunk(score_vetorial=0.50)]
        assert deve_ativar_hyde("factual", chunks) is False

    def test_tipo_desconhecido_nao_ativa(self):
        chunks = [_chunk(score_vetorial=0.50)]
        assert deve_ativar_hyde("OUTRO", chunks) is False

    def test_multiplos_chunks_usa_max_score(self):
        """Mesmo se alguns chunks têm score baixo, max acima do threshold desativa."""
        chunks = [
            _chunk(score_vetorial=0.50),
            _chunk(score_vetorial=0.73),  # acima do threshold
            _chunk(score_vetorial=0.60),
        ]
        assert deve_ativar_hyde("INTERPRETATIVA", chunks) is False


class TestGerarDocumentoHipotetico:

    @patch("src.rag.hyde.anthropic.Anthropic")
    def test_gera_documento(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        mock_resp = MagicMock()
        mock_resp.content = [MagicMock(text="Artigo hipotético sobre IBS.")]
        mock_resp.usage.input_tokens = 50
        mock_resp.usage.output_tokens = 30
        mock_client.messages.create.return_value = mock_resp

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            resultado = gerar_documento_hipotetico("Como funciona o IBS?", "claude-haiku-4-5-20251001")

        assert "hipotético" in resultado or "IBS" in resultado
        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["temperature"] == 0.2
        assert call_kwargs["max_tokens"] == 300

    @patch("src.rag.hyde.anthropic.Anthropic")
    def test_contexto_temporal_injetado(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        mock_resp = MagicMock()
        mock_resp.content = [MagicMock(text="Documento com contexto temporal.")]
        mock_resp.usage.input_tokens = 50
        mock_resp.usage.output_tokens = 30
        mock_client.messages.create.return_value = mock_resp

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            gerar_documento_hipotetico(
                "Alíquota CBS em 2028",
                "claude-haiku-4-5-20251001",
                data_referencia=date(2028, 1, 1),
                regime="transicao",
            )

        call_kwargs = mock_client.messages.create.call_args[1]
        assert "2028" in call_kwargs["system"]
        assert "transicao" in call_kwargs["system"]


class TestExecutarHydeFallback:

    @patch("src.rag.hyde.retrieve_com_hyde")
    @patch("src.rag.hyde.gerar_documento_hipotetico")
    def test_hyde_melhora_score_usa_chunks_hyde(self, mock_gerar, mock_retrieve):
        chunks_iniciais = [_chunk(score_vetorial=0.60)]
        mock_gerar.return_value = "Documento hipotético."
        mock_retrieve.return_value = [_chunk(score_vetorial=0.85)]

        chunks, ativado = executar_hyde_fallback(
            query="Como funciona o IBS?",
            chunks_iniciais=chunks_iniciais,
            tipo_query="INTERPRETATIVA",
            model="claude-haiku-4-5-20251001",
        )

        assert ativado is True
        assert chunks[0].score_vetorial == 0.85

    @patch("src.rag.hyde.retrieve_com_hyde")
    @patch("src.rag.hyde.gerar_documento_hipotetico")
    def test_hyde_nao_melhora_mantem_inicial(self, mock_gerar, mock_retrieve):
        chunks_iniciais = [_chunk(score_vetorial=0.65)]
        mock_gerar.return_value = "Documento hipotético."
        mock_retrieve.return_value = [_chunk(score_vetorial=0.50)]  # pior

        chunks, ativado = executar_hyde_fallback(
            query="Como funciona o IBS?",
            chunks_iniciais=chunks_iniciais,
            tipo_query="INTERPRETATIVA",
            model="claude-haiku-4-5-20251001",
        )

        assert ativado is False
        assert chunks[0].score_vetorial == 0.65

    def test_factual_nao_ativa_hyde(self):
        chunks_iniciais = [_chunk(score_vetorial=0.60)]

        chunks, ativado = executar_hyde_fallback(
            query="Qual a alíquota do Art. 10?",
            chunks_iniciais=chunks_iniciais,
            tipo_query="FACTUAL",
            model="claude-haiku-4-5-20251001",
        )

        assert ativado is False
        assert chunks == chunks_iniciais

    def test_score_alto_nao_ativa_hyde(self):
        chunks_iniciais = [_chunk(score_vetorial=0.85)]

        chunks, ativado = executar_hyde_fallback(
            query="Como funciona o IBS?",
            chunks_iniciais=chunks_iniciais,
            tipo_query="INTERPRETATIVA",
            model="claude-haiku-4-5-20251001",
        )

        assert ativado is False

    @patch("src.rag.hyde.gerar_documento_hipotetico", side_effect=Exception("LLM error"))
    def test_erro_hyde_retorna_chunks_iniciais(self, mock_gerar):
        chunks_iniciais = [_chunk(score_vetorial=0.60)]

        chunks, ativado = executar_hyde_fallback(
            query="Como funciona o IBS?",
            chunks_iniciais=chunks_iniciais,
            tipo_query="INTERPRETATIVA",
            model="claude-haiku-4-5-20251001",
        )

        assert ativado is False
        assert chunks == chunks_iniciais

    @patch("src.rag.hyde.retrieve_com_hyde")
    @patch("src.rag.hyde.gerar_documento_hipotetico")
    def test_hyde_retorno_vazio_mantem_inicial(self, mock_gerar, mock_retrieve):
        chunks_iniciais = [_chunk(score_vetorial=0.60)]
        mock_gerar.return_value = "Documento hipotético."
        mock_retrieve.return_value = []

        chunks, ativado = executar_hyde_fallback(
            query="Como funciona o IBS?",
            chunks_iniciais=chunks_iniciais,
            tipo_query="INTERPRETATIVA",
            model="claude-haiku-4-5-20251001",
        )

        assert ativado is False
        assert chunks == chunks_iniciais

    @patch("src.rag.hyde.retrieve_com_hyde")
    @patch("src.rag.hyde.gerar_documento_hipotetico")
    def test_ptf_propagado_no_re_retrieval(self, mock_gerar, mock_retrieve):
        chunks_iniciais = [_chunk(score_vetorial=0.60)]
        mock_gerar.return_value = "Hipotético."
        mock_retrieve.return_value = [_chunk(score_vetorial=0.85)]
        data_ref = date(2028, 1, 1)

        executar_hyde_fallback(
            query="CBS em 2028",
            chunks_iniciais=chunks_iniciais,
            tipo_query="INTERPRETATIVA",
            model="claude-haiku-4-5-20251001",
            data_referencia=data_ref,
            regime="transicao",
        )

        # Verificar que data_referencia foi propagada ao retrieve_com_hyde
        mock_retrieve.assert_called_once()
        call_kwargs = mock_retrieve.call_args[1]
        assert call_kwargs["data_referencia"] == data_ref

    @patch("src.rag.hyde.retrieve_com_hyde")
    @patch("src.rag.hyde.gerar_documento_hipotetico")
    def test_chunks_iniciais_vazio_ativa_hyde(self, mock_gerar, mock_retrieve):
        mock_gerar.return_value = "Hipotético."
        mock_retrieve.return_value = [_chunk(score_vetorial=0.80)]

        chunks, ativado = executar_hyde_fallback(
            query="Como funciona o IBS?",
            chunks_iniciais=[],
            tipo_query="INTERPRETATIVA",
            model="claude-haiku-4-5-20251001",
        )

        assert ativado is True
        assert len(chunks) == 1
