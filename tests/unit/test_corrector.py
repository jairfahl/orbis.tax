"""
tests/unit/test_corrector.py — Testes unitários para Corrective RAG (CRAG).

Todos os mocks via patch — sem chamadas externas.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.rag.corrector import CorrectorRAG, CorrectorResult
from src.rag.retriever import ChunkResultado


def _make_chunk(chunk_id: int, norma: str = "LC214_2025", artigo: str = "Art. 10",
                score: float = 0.7) -> ChunkResultado:
    return ChunkResultado(
        chunk_id=chunk_id,
        norma_codigo=norma,
        artigo=artigo,
        texto=f"Texto do chunk {chunk_id} sobre tributação.",
        score_vetorial=score,
        score_bm25=score * 0.5,
        score_final=score,
    )


@pytest.fixture
def corrector():
    return CorrectorRAG(model="claude-haiku-4-5-20251001")


@pytest.fixture
def chunks_3():
    return [_make_chunk(1), _make_chunk(2), _make_chunk(3)]


class TestCorrectorRAG:

    @patch.object(CorrectorRAG, "_chamar_llm")
    def test_todos_relevantes_mantem_todos(self, mock_llm, corrector, chunks_3):
        mock_llm.return_value = {
            "avaliacoes": [
                {"id": 1, "relevancia": "relevante"},
                {"id": 2, "relevancia": "relevante"},
                {"id": 3, "relevancia": "relevante"},
            ],
            "query_reformulada": None,
        }
        result = corrector.corrigir("consulta tributária IBS", chunks_3)
        assert len(result.chunks_filtrados) == 3
        assert result.chunks_removidos == 0
        assert not result.usou_reformulacao

    @patch.object(CorrectorRAG, "_chamar_llm")
    def test_remove_irrelevantes(self, mock_llm, corrector, chunks_3):
        mock_llm.return_value = {
            "avaliacoes": [
                {"id": 1, "relevancia": "relevante"},
                {"id": 2, "relevancia": "irrelevante"},
                {"id": 3, "relevancia": "parcial"},
            ],
            "query_reformulada": None,
        }
        result = corrector.corrigir("consulta tributária IBS", chunks_3)
        assert len(result.chunks_filtrados) == 2
        assert result.chunks_removidos == 1
        # Chunk 2 foi removido
        ids = [c.chunk_id for c in result.chunks_filtrados]
        assert 2 not in ids

    @patch.object(CorrectorRAG, "_chamar_llm")
    def test_parcial_mantido(self, mock_llm, corrector, chunks_3):
        """Chunks parciais devem ser mantidos (apenas irrelevantes são removidos)."""
        mock_llm.return_value = {
            "avaliacoes": [
                {"id": 1, "relevancia": "parcial"},
                {"id": 2, "relevancia": "parcial"},
                {"id": 3, "relevancia": "parcial"},
            ],
            "query_reformulada": None,
        }
        result = corrector.corrigir("consulta tributária IBS", chunks_3)
        assert len(result.chunks_filtrados) == 3
        assert result.chunks_removidos == 0

    @patch.object(CorrectorRAG, "_chamar_llm")
    def test_re_retrieval_quando_poucos_relevantes(self, mock_llm, corrector):
        """Se < 2 chunks restam, dispara re-retrieval com query reformulada."""
        chunks = [_make_chunk(1), _make_chunk(2)]
        mock_llm.return_value = {
            "avaliacoes": [
                {"id": 1, "relevancia": "irrelevante"},
                {"id": 2, "relevancia": "irrelevante"},
            ],
            "query_reformulada": "alíquota IBS reforma tributária",
        }
        novos = [_make_chunk(10, artigo="Art. 20"), _make_chunk(11, artigo="Art. 21")]
        mock_retrieve = MagicMock(return_value=novos)

        result = corrector.corrigir("consulta vaga", chunks, retrieve_fn=mock_retrieve)
        assert result.usou_reformulacao is True
        mock_retrieve.assert_called_once_with("alíquota IBS reforma tributária")
        assert len(result.chunks_filtrados) >= 1  # novos chunks adicionados

    @patch.object(CorrectorRAG, "_chamar_llm")
    def test_sem_re_retrieval_sem_funcao(self, mock_llm, corrector):
        """Sem retrieve_fn, não faz re-retrieval mesmo com poucos chunks."""
        chunks = [_make_chunk(1)]
        mock_llm.return_value = {
            "avaliacoes": [{"id": 1, "relevancia": "irrelevante"}],
            "query_reformulada": "query reformulada",
        }
        result = corrector.corrigir("consulta vaga", chunks, retrieve_fn=None)
        assert result.usou_reformulacao is False
        assert len(result.chunks_filtrados) == 0

    @patch.object(CorrectorRAG, "_chamar_llm")
    def test_falha_llm_retorna_originais(self, mock_llm, corrector, chunks_3):
        """Se LLM falhar, retorna chunks originais (graceful degradation)."""
        mock_llm.side_effect = RuntimeError("API error")
        result = corrector.corrigir("consulta tributária IBS", chunks_3)
        assert len(result.chunks_filtrados) == 3
        assert result.chunks_removidos == 0

    def test_chunks_vazios(self, corrector):
        """Lista vazia de chunks retorna resultado vazio."""
        result = corrector.corrigir("consulta", [])
        assert len(result.chunks_filtrados) == 0
        assert result.chunks_removidos == 0

    @patch.object(CorrectorRAG, "_chamar_llm")
    def test_dedup_no_re_retrieval(self, mock_llm, corrector):
        """Re-retrieval não duplica chunks já existentes."""
        chunks = [_make_chunk(1)]
        mock_llm.return_value = {
            "avaliacoes": [{"id": 1, "relevancia": "irrelevante"}],
            "query_reformulada": "query reformulada",
        }
        # Re-retrieval retorna chunk com mesmo ID
        novos = [_make_chunk(1), _make_chunk(5)]
        mock_retrieve = MagicMock(return_value=novos)

        result = corrector.corrigir("consulta", chunks, retrieve_fn=mock_retrieve)
        ids = [c.chunk_id for c in result.chunks_filtrados]
        assert ids.count(1) <= 1  # sem duplicatas
