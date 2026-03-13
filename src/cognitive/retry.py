"""
cognitive/retry.py — StructuredRetry: retry inteligente para chamadas LLM com saída JSON.

Em vez de falhar em JSONDecodeError ou campos faltantes, re-chama o LLM com
feedback específico sobre o erro, permitindo auto-correção.

Inspirado em: Extraction with Retries (LangGraph) — 500-AI-Agents-Projects.
"""

import json
import logging
import re
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class StructuredRetry:
    """Wrapper de retry para chamadas LLM que esperam JSON estruturado."""

    def __init__(
        self,
        max_retries_parse: int = 2,
        max_retries_schema: int = 1,
        campos_obrigatorios: Optional[list[str]] = None,
        ranges: Optional[dict[str, tuple[float, float]]] = None,
    ):
        """
        Args:
            max_retries_parse: Max retries para JSONDecodeError.
            max_retries_schema: Max retries para campos obrigatórios faltantes.
            campos_obrigatorios: Lista de campos que devem existir no JSON.
            ranges: Dict campo → (min, max) para auto-clamping.
        """
        self.max_retries_parse = max_retries_parse
        self.max_retries_schema = max_retries_schema
        self.campos_obrigatorios = campos_obrigatorios or []
        self.ranges = ranges or {}

    def executar(
        self,
        chamar_llm_fn: Callable[..., str],
        **kwargs,
    ) -> dict:
        """
        Executa chamada LLM com retry estruturado.

        Args:
            chamar_llm_fn: Função que chama o LLM e retorna o texto raw da resposta.
                           Deve aceitar um kwarg opcional 'instrucao_extra' (str).
            **kwargs: Argumentos adicionais passados para chamar_llm_fn.

        Returns:
            Dict parseado do JSON retornado pelo LLM.

        Raises:
            RuntimeError: Se todos os retries falharem.
        """
        raw = ""
        instrucao_extra = ""

        # Fase 1: Retry para parse JSON
        for tentativa in range(1 + self.max_retries_parse):
            try:
                raw = chamar_llm_fn(instrucao_extra=instrucao_extra, **kwargs)
                dados = self._parse_json(raw)
                break
            except json.JSONDecodeError as e:
                if tentativa < self.max_retries_parse:
                    instrucao_extra = (
                        f"\n\nAVISO: Sua resposta anterior não era JSON válido. "
                        f"Erro: {e.msg} na posição {e.pos}. "
                        f"Retorne APENAS o objeto JSON especificado, sem texto adicional."
                    )
                    logger.warning("StructuredRetry: JSONDecodeError (tentativa %d/%d) — retrying",
                                   tentativa + 1, self.max_retries_parse)
                else:
                    raise RuntimeError(
                        f"LLM retornou JSON inválido após {self.max_retries_parse + 1} tentativas. "
                        f"Último erro: {e.msg} posição {e.pos}."
                    ) from e
        else:
            raise RuntimeError("StructuredRetry: loop encerrado sem resultado")

        # Fase 2: Validar campos obrigatórios
        campos_faltantes = [c for c in self.campos_obrigatorios if c not in dados]
        if campos_faltantes:
            for tentativa_schema in range(self.max_retries_schema):
                instrucao_extra = (
                    f"\n\nAVISO: Sua resposta JSON está incompleta. "
                    f"Campos obrigatórios faltantes: {', '.join(campos_faltantes)}. "
                    f"Retorne o JSON completo com todos os campos especificados."
                )
                logger.warning("StructuredRetry: campos faltantes %s — retrying", campos_faltantes)
                try:
                    raw = chamar_llm_fn(instrucao_extra=instrucao_extra, **kwargs)
                    dados = self._parse_json(raw)
                    campos_faltantes = [c for c in self.campos_obrigatorios if c not in dados]
                    if not campos_faltantes:
                        break
                except (json.JSONDecodeError, RuntimeError):
                    pass

            if campos_faltantes:
                logger.warning("StructuredRetry: campos ainda faltantes após retries: %s",
                               campos_faltantes)

        # Fase 3: Auto-clamping de valores fora de range
        for campo, (vmin, vmax) in self.ranges.items():
            if campo in dados:
                try:
                    valor = float(dados[campo])
                    if valor < vmin or valor > vmax:
                        valor_clamped = max(vmin, min(vmax, valor))
                        logger.warning("StructuredRetry: %s=%s fora de [%s, %s] → clamped para %s",
                                       campo, dados[campo], vmin, vmax, valor_clamped)
                        dados[campo] = valor_clamped
                except (TypeError, ValueError):
                    pass

        return dados

    def _parse_json(self, raw: str) -> dict:
        """Parse JSON com tolerância a markdown code fences."""
        text = raw.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\n?", "", text)
            text = re.sub(r"\n?```$", "", text)
        return json.loads(text)
