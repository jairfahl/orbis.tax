"""
tests/unit/test_decomposer.py — Testes unitários para QueryDecomposer.

Sem chamadas externas — mocks para LLM e retrieve.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.rag.decomposer import DecompositionResult, QueryDecomposer
from src.rag.retriever import ChunkResultado


def _make_chunk(chunk_id: int, score: float = 0.7) -> ChunkResultado:
    return ChunkResultado(
        chunk_id=chunk_id,
        norma_codigo="LC214_2025",
        artigo=f"Art. {chunk_id}",
        texto=f"Texto do chunk {chunk_id}.",
        score_vetorial=score,
        score_bm25=score * 0.5,
        score_final=score,
    )


@pytest.fixture
def decomposer():
    return QueryDecomposer(model="claude-haiku-4-5-20251001")


class TestQueryDecomposer:

    @patch.object(QueryDecomposer, "_chamar_llm")
    def test_query_simples_retorna_sem_decomposicao(self, mock_llm, decomposer):
        mock_llm.return_value = {"tipo": "simples"}
        mock_retrieve = MagicMock(return_value=[_make_chunk(1), _make_chunk(2)])

        result = decomposer.decompor_e_recuperar("Qual a alíquota do IBS?", mock_retrieve)
        assert not result.eh_composta
        assert len(result.sub_perguntas) == 1
        assert len(result.chunks_merged) == 2
        mock_retrieve.assert_called_once()

    @patch.object(QueryDecomposer, "_chamar_llm")
    def test_query_composta_decompoe_e_merge(self, mock_llm, decomposer):
        mock_llm.side_effect = [
            {"tipo": "composta"},
            {"sub_perguntas": [
                "Qual o impacto do IBS para serviços?",
                "Como funciona o Simples Nacional na reforma?",
            ]},
        ]
        # Cada sub-pergunta retorna chunks diferentes
        mock_retrieve = MagicMock(side_effect=[
            [_make_chunk(1), _make_chunk(2)],
            [_make_chunk(3), _make_chunk(4)],
        ])

        result = decomposer.decompor_e_recuperar(
            "Impacto do IBS no Simples para serviços", mock_retrieve
        )
        assert result.eh_composta
        assert len(result.sub_perguntas) == 2
        assert len(result.chunks_merged) == 4
        assert mock_retrieve.call_count == 2

    @patch.object(QueryDecomposer, "_chamar_llm")
    def test_merge_dedup_por_chunk_id(self, mock_llm, decomposer):
        """Chunks com mesmo ID são deduplicados, mantendo maior score."""
        mock_llm.side_effect = [
            {"tipo": "composta"},
            {"sub_perguntas": ["Pergunta A", "Pergunta B"]},
        ]
        mock_retrieve = MagicMock(side_effect=[
            [_make_chunk(1, score=0.6), _make_chunk(2, score=0.5)],
            [_make_chunk(1, score=0.8), _make_chunk(3, score=0.7)],  # chunk 1 duplicado com score maior
        ])

        result = decomposer.decompor_e_recuperar("Query complexa", mock_retrieve)
        ids = [c.chunk_id for c in result.chunks_merged]
        assert ids.count(1) == 1  # sem duplicata
        # Chunk 1 deve ter o maior score (0.8)
        chunk_1 = [c for c in result.chunks_merged if c.chunk_id == 1][0]
        assert chunk_1.score_final == 0.8

    @patch.object(QueryDecomposer, "_chamar_llm")
    def test_max_4_subperguntas(self, mock_llm, decomposer):
        mock_llm.side_effect = [
            {"tipo": "composta"},
            {"sub_perguntas": ["P1", "P2", "P3", "P4", "P5", "P6"]},  # 6 > max 4
        ]
        sub = decomposer.decompor("query complexa")
        assert len(sub) <= 4

    @patch.object(QueryDecomposer, "_chamar_llm")
    def test_menos_de_2_subperguntas_fallback(self, mock_llm, decomposer):
        """Se decomposição gera menos de 2 sub-perguntas, usa query original."""
        mock_llm.return_value = {"sub_perguntas": ["Apenas uma"]}
        sub = decomposer.decompor("query")
        assert sub == ["query"]

    @patch.object(QueryDecomposer, "_chamar_llm")
    def test_falha_classificacao_default_simples(self, mock_llm, decomposer):
        mock_llm.side_effect = RuntimeError("API error")
        assert decomposer.classificar("query") is False

    @patch.object(QueryDecomposer, "_chamar_llm")
    def test_falha_decomposicao_retorna_original(self, mock_llm, decomposer):
        mock_llm.side_effect = RuntimeError("API error")
        sub = decomposer.decompor("query original")
        assert sub == ["query original"]

    @patch.object(QueryDecomposer, "_chamar_llm")
    def test_falha_retrieve_subpergunta_graceful(self, mock_llm, decomposer):
        """Falha no retrieve de uma sub-pergunta não bloqueia as outras."""
        mock_llm.side_effect = [
            {"tipo": "composta"},
            {"sub_perguntas": ["Pergunta A", "Pergunta B"]},
        ]
        mock_retrieve = MagicMock(side_effect=[
            [_make_chunk(1)],
            RuntimeError("retrieve error"),
        ])

        result = decomposer.decompor_e_recuperar("Query", mock_retrieve)
        assert len(result.chunks_merged) >= 1  # pelo menos os da Pergunta A

    @patch.object(QueryDecomposer, "_chamar_llm")
    def test_chunks_merged_ordenados_por_score(self, mock_llm, decomposer):
        mock_llm.side_effect = [
            {"tipo": "composta"},
            {"sub_perguntas": ["A", "B"]},
        ]
        mock_retrieve = MagicMock(side_effect=[
            [_make_chunk(1, score=0.5)],
            [_make_chunk(2, score=0.9)],
        ])

        result = decomposer.decompor_e_recuperar("Query", mock_retrieve)
        scores = [c.score_final for c in result.chunks_merged]
        assert scores == sorted(scores, reverse=True)
