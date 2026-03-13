"""
rag/decomposer.py — QueryDecomposer: decompõe queries complexas em sub-perguntas.

Queries multi-facetadas geram um embedding único que dilui múltiplas dimensões
semânticas. O decomposer identifica queries compostas e as quebra em sub-perguntas
atômicas, cada uma com retrieval independente.

Inspirado em: DeepKnowledge Agent (Agno) — 500-AI-Agents-Projects.
"""

import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Callable, Optional

import anthropic
from dotenv import load_dotenv

from src.rag.retriever import ChunkResultado

load_dotenv()
logger = logging.getLogger(__name__)

MODEL_DECOMPOSER = os.getenv("MODEL_DEV", "claude-haiku-4-5-20251001")

_PROMPT_CLASSIFICAR = """\
Classifique a seguinte consulta tributária como "simples" ou "composta".

Uma consulta é COMPOSTA se aborda 2 ou mais conceitos tributários distintos \
que requerem artigos ou normas diferentes para responder.

CONSULTA: {query}

Retorne EXCLUSIVAMENTE um JSON: {{"tipo": "simples"|"composta"}}"""

_PROMPT_DECOMPOR = """\
Decomponha a seguinte consulta tributária complexa em sub-perguntas atômicas.
Cada sub-pergunta deve focar em UM ÚNICO conceito tributário.

CONSULTA ORIGINAL: {query}

Retorne EXCLUSIVAMENTE um JSON:
{{
  "sub_perguntas": [
    "sub-pergunta 1",
    "sub-pergunta 2",
    ...
  ]
}}

Regras:
- Máximo 4 sub-perguntas
- Mínimo 2 sub-perguntas
- Cada sub-pergunta deve ser auto-contida (compreensível isoladamente)
- Manter termos tributários específicos (IBS, CBS, alíquota, etc.)"""


@dataclass
class DecompositionResult:
    """Resultado da decomposição de query."""
    query_original: str
    eh_composta: bool
    sub_perguntas: list[str]
    chunks_por_subpergunta: dict[str, list[ChunkResultado]]
    chunks_merged: list[ChunkResultado]


class QueryDecomposer:

    def __init__(self, model: str = MODEL_DECOMPOSER):
        self._model = model
        self._client: Optional[anthropic.Anthropic] = None

    def _get_client(self) -> anthropic.Anthropic:
        if self._client is None:
            key = os.getenv("ANTHROPIC_API_KEY")
            if not key or key == "<PREENCHER>":
                raise EnvironmentError("ANTHROPIC_API_KEY não configurada")
            self._client = anthropic.Anthropic(api_key=key)
        return self._client

    def _chamar_llm(self, prompt: str) -> dict:
        client = self._get_client()
        resp = client.messages.create(
            model=self._model,
            max_tokens=256,
            temperature=0.0,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)
        return json.loads(raw)

    def classificar(self, query: str) -> bool:
        """Classifica query como simples ou composta. Retorna True se composta."""
        try:
            prompt = _PROMPT_CLASSIFICAR.format(query=query)
            dados = self._chamar_llm(prompt)
            eh_composta = dados.get("tipo", "simples") == "composta"
            logger.info("QueryDecomposer: query classificada como %s",
                        "composta" if eh_composta else "simples")
            return eh_composta
        except Exception as e:
            logger.warning("QueryDecomposer: falha na classificação (%s) — default simples", e)
            return False

    def decompor(self, query: str) -> list[str]:
        """Decompõe query composta em sub-perguntas atômicas."""
        try:
            prompt = _PROMPT_DECOMPOR.format(query=query)
            dados = self._chamar_llm(prompt)
            sub_perguntas = dados.get("sub_perguntas", [])
            # Garantir limites
            sub_perguntas = sub_perguntas[:4]  # max 4
            if len(sub_perguntas) < 2:
                return [query]  # fallback: query original
            logger.info("QueryDecomposer: decomposta em %d sub-perguntas", len(sub_perguntas))
            return sub_perguntas
        except Exception as e:
            logger.warning("QueryDecomposer: falha na decomposição (%s) — usando query original", e)
            return [query]

    def decompor_e_recuperar(
        self,
        query: str,
        retrieve_fn: Callable[[str], list[ChunkResultado]],
    ) -> DecompositionResult:
        """
        Pipeline completo: classificar → decompor → retrieve por sub-pergunta → merge.

        Args:
            query: Consulta original.
            retrieve_fn: Função de retrieval.
                         Assinatura: retrieve_fn(query: str) -> list[ChunkResultado]

        Returns:
            DecompositionResult com chunks merged e atribuição por sub-pergunta.
        """
        eh_composta = self.classificar(query)

        if not eh_composta:
            chunks = retrieve_fn(query)
            return DecompositionResult(
                query_original=query,
                eh_composta=False,
                sub_perguntas=[query],
                chunks_por_subpergunta={query: chunks},
                chunks_merged=chunks,
            )

        sub_perguntas = self.decompor(query)
        chunks_por_sp: dict[str, list[ChunkResultado]] = {}
        todos_chunks: list[ChunkResultado] = []

        for sp in sub_perguntas:
            try:
                chunks_sp = retrieve_fn(sp)
                chunks_por_sp[sp] = chunks_sp
                todos_chunks.extend(chunks_sp)
            except Exception as e:
                logger.warning("QueryDecomposer: falha no retrieve para '%s' (%s)", sp[:50], e)
                chunks_por_sp[sp] = []

        # Merge: deduplicar por chunk_id, manter maior score
        merged = self._merge_chunks(todos_chunks)

        logger.info("QueryDecomposer: %d sub-perguntas → %d chunks merged (de %d totais)",
                    len(sub_perguntas), len(merged), len(todos_chunks))

        return DecompositionResult(
            query_original=query,
            eh_composta=True,
            sub_perguntas=sub_perguntas,
            chunks_por_subpergunta=chunks_por_sp,
            chunks_merged=merged,
        )

    def _merge_chunks(self, chunks: list[ChunkResultado]) -> list[ChunkResultado]:
        """Deduplicar chunks por chunk_id, mantendo o de maior score_final."""
        melhores: dict[int, ChunkResultado] = {}
        for c in chunks:
            if c.chunk_id not in melhores or c.score_final > melhores[c.chunk_id].score_final:
                melhores[c.chunk_id] = c
        resultado = sorted(melhores.values(), key=lambda x: x.score_final, reverse=True)
        return resultado
