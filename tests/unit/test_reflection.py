"""
tests/unit/test_reflection.py — Testes unitários para ReflectionLoop.

Sem chamadas externas — mocks para LLM e CognitiveEngine.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.cognitive.reflection import CriticaResult, ReflectionLoop, ReflectionResult


def _make_analise(bloqueado=False, resposta="Recomendação tributária fixture."):
    """Cria AnaliseResult mock."""
    from src.cognitive.engine import AnaliseResult, AntiAlucinacaoResult
    from src.quality.engine import QualidadeResult, QualidadeStatus

    return AnaliseResult(
        query="Qual o impacto do IBS para serviços?",
        chunks=[],
        qualidade=QualidadeResult(status=QualidadeStatus.VERDE),
        fundamento_legal=["Art. 9 LC 214/2025"],
        grau_consolidacao="consolidado",
        contra_tese=None,
        scoring_confianca="alto",
        resposta=resposta,
        disclaimer=None,
        anti_alucinacao=AntiAlucinacaoResult(bloqueado=bloqueado),
        prompt_version="v1.0.0-sprint2",
        model_id="claude-haiku-4-5-20251001",
        latencia_ms=150,
    )


@pytest.fixture
def loop():
    return ReflectionLoop(model="claude-haiku-4-5-20251001", max_iteracoes=2)


class TestReflectionLoop:

    @patch.object(ReflectionLoop, "_criticar")
    def test_aprovada_primeira_iteracao(self, mock_criticar, loop):
        mock_criticar.return_value = CriticaResult(
            aprovado=True, dimensoes={}, sugestoes=[]
        )
        analise = _make_analise()
        result = loop.refletir(analise)
        assert result.iteracoes == 1
        assert result.disclaimer_reflexao is None
        assert len(result.criticas) == 1
        assert result.analise_final.resposta == analise.resposta

    @patch.object(ReflectionLoop, "_criticar")
    def test_reprovada_sem_re_analisar_fn(self, mock_criticar, loop):
        """Sem re_analisar_fn, retorna com disclaimer."""
        mock_criticar.return_value = CriticaResult(
            aprovado=False,
            dimensoes={"acao_concreta": {"ok": False, "critica": "Ação vaga"}},
            sugestoes=["Especificar prazo"],
        )
        analise = _make_analise()
        result = loop.refletir(analise, re_analisar_fn=None)
        assert result.disclaimer_reflexao is not None
        assert "ressalvas" in result.disclaimer_reflexao

    @patch.object(ReflectionLoop, "_criticar")
    def test_reprovada_re_gera_e_aprova(self, mock_criticar, loop):
        """Reprovada na 1a iteração, re-gerada e aprovada na 2a."""
        mock_criticar.side_effect = [
            CriticaResult(
                aprovado=False,
                dimensoes={"acao_concreta": {"ok": False, "critica": "Vago"}},
                sugestoes=["Detalhar ação"],
            ),
            CriticaResult(aprovado=True, dimensoes={}, sugestoes=[]),
        ]
        analise_v2 = _make_analise(resposta="Recomendação melhorada v2.")
        mock_re_analisar = MagicMock(return_value=analise_v2)

        result = loop.refletir(_make_analise(), re_analisar_fn=mock_re_analisar)
        assert result.iteracoes == 2
        assert result.analise_final.resposta == "Recomendação melhorada v2."
        assert result.disclaimer_reflexao is None
        mock_re_analisar.assert_called_once()

    @patch.object(ReflectionLoop, "_criticar")
    def test_max_iteracoes_respeitado(self, mock_criticar, loop):
        """Se sempre reprovada, para após max_iteracoes."""
        mock_criticar.return_value = CriticaResult(
            aprovado=False,
            dimensoes={},
            sugestoes=["Melhorar"],
        )
        mock_re_analisar = MagicMock(return_value=_make_analise())

        result = loop.refletir(_make_analise(), re_analisar_fn=mock_re_analisar)
        assert result.iteracoes == 2  # max_iteracoes
        assert result.disclaimer_reflexao is not None

    def test_analise_bloqueada_skip_reflexao(self, loop):
        """Análise bloqueada por anti-alucinação não entra no loop."""
        analise = _make_analise(bloqueado=True)
        result = loop.refletir(analise)
        assert result.iteracoes == 0
        assert "bloqueada" in result.disclaimer_reflexao

    @patch.object(ReflectionLoop, "_criticar")
    def test_erro_na_critica_encerra_graciosamente(self, mock_criticar, loop):
        mock_criticar.side_effect = RuntimeError("API error")
        result = loop.refletir(_make_analise())
        assert result.iteracoes == 0
        assert result.analise_final is not None

    @patch.object(ReflectionLoop, "_criticar")
    def test_re_analise_bloqueada_mantem_melhor(self, mock_criticar, loop):
        """Se re-análise vier bloqueada, mantém a anterior."""
        mock_criticar.side_effect = [
            CriticaResult(aprovado=False, dimensoes={}, sugestoes=[]),
            CriticaResult(aprovado=True, dimensoes={}, sugestoes=[]),
        ]
        analise_original = _make_analise(resposta="Original boa.")
        analise_bloqueada = _make_analise(bloqueado=True, resposta="Bloqueada.")
        mock_re_analisar = MagicMock(return_value=analise_bloqueada)

        result = loop.refletir(analise_original, re_analisar_fn=mock_re_analisar)
        # Deve manter a original, não a bloqueada
        assert result.analise_final.resposta == "Original boa."

    @patch.object(ReflectionLoop, "_criticar")
    def test_sugestoes_no_disclaimer(self, mock_criticar, loop):
        mock_criticar.return_value = CriticaResult(
            aprovado=False,
            dimensoes={},
            sugestoes=["Adicionar prazo", "Citar artigo específico"],
        )
        result = loop.refletir(_make_analise())
        assert "Adicionar prazo" in result.disclaimer_reflexao
        assert "Citar artigo" in result.disclaimer_reflexao
