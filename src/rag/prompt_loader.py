"""
rag/prompt_loader.py — Progressive Loading de system prompts.

Carrega apenas as seções relevantes do prompt conforme query_tipo e quality_gate,
otimizando o context budget (12.100 tokens, ESP-09 Seção 4).

Delimitadores:
  ## [SUMMARY]     — regras essenciais (~600 tokens)
  ## [FULL]        — especificações completas, few-shot, edge cases
  ## [FULL:antialucinacao] — mecanismos anti-alucinação

Regras:
  FACTUAL          → [SUMMARY]
  INTERPRETATIVA   → [SUMMARY] + [FULL]
  COMPARATIVA      → [SUMMARY] + [FULL] + [FULL:antialucinacao]
  quality_gate AMARELO|VERMELHO → adiciona [FULL:antialucinacao]
"""

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

_SECTION_PATTERN = re.compile(
    r"^## \[(SUMMARY|FULL:antialucinacao|FULL)\]\s*$",
    re.MULTILINE,
)

# Seções que cada query_tipo carrega
_SECOES_POR_TIPO: dict[str, list[str]] = {
    "FACTUAL": ["SUMMARY"],
    "INTERPRETATIVA": ["SUMMARY", "FULL"],
    "COMPARATIVA": ["SUMMARY", "FULL", "FULL:antialucinacao"],
}

_QUALITY_GATES_FORCAM_ANTI = {"AMARELO", "VERMELHO"}


@dataclass
class PromptLoadResult:
    conteudo_carregado: str
    secoes_carregadas: list[str] = field(default_factory=list)
    tokens_por_secao: dict[str, int] = field(default_factory=dict)
    retrocompativel: bool = False


def _estimar_tokens(texto: str) -> int:
    """Aproximação de tokens: palavras * 1.3."""
    return int(len(texto.split()) * 1.3)


def _extrair_secoes(conteudo: str) -> dict[str, str]:
    """Extrai seções delimitadas por ## [NOME] do conteúdo."""
    secoes: dict[str, str] = {}
    matches = list(_SECTION_PATTERN.finditer(conteudo))

    if not matches:
        return secoes

    for i, match in enumerate(matches):
        nome = match.group(1)
        inicio = match.end()
        fim = matches[i + 1].start() if i + 1 < len(matches) else len(conteudo)
        secoes[nome] = conteudo[inicio:fim].strip()

    return secoes


def carregar_secoes_prompt(
    conteudo: str,
    query_tipo: str,
    quality_gate: str,
) -> PromptLoadResult:
    """
    Extrai e concatena as seções relevantes do prompt conforme query_tipo e quality_gate.

    Retrocompatível: se o prompt não contiver delimitadores [SUMMARY]/[FULL],
    retorna o conteúdo inteiro sem modificação.
    """
    # Retrocompatibilidade: sem delimitadores → retornar tudo
    if "## [SUMMARY]" not in conteudo:
        return PromptLoadResult(
            conteudo_carregado=conteudo,
            secoes_carregadas=["ALL"],
            tokens_por_secao={"ALL": _estimar_tokens(conteudo)},
            retrocompativel=True,
        )

    secoes = _extrair_secoes(conteudo)
    if not secoes:
        return PromptLoadResult(
            conteudo_carregado=conteudo,
            secoes_carregadas=["ALL"],
            tokens_por_secao={"ALL": _estimar_tokens(conteudo)},
            retrocompativel=True,
        )

    # Determinar seções necessárias
    tipo_upper = query_tipo.upper() if query_tipo else "INTERPRETATIVA"
    secoes_necessarias = list(_SECOES_POR_TIPO.get(tipo_upper, ["SUMMARY", "FULL"]))

    # Quality gate AMARELO/VERMELHO força anti-alucinação
    gate_upper = quality_gate.upper() if quality_gate else ""
    if gate_upper in _QUALITY_GATES_FORCAM_ANTI and "FULL:antialucinacao" not in secoes_necessarias:
        secoes_necessarias.append("FULL:antialucinacao")

    # Montar conteúdo
    partes: list[str] = []
    secoes_carregadas: list[str] = []
    tokens_por_secao: dict[str, int] = {}

    for nome in secoes_necessarias:
        texto = secoes.get(nome)
        if texto:
            partes.append(texto)
            secoes_carregadas.append(nome)
            tokens_por_secao[nome] = _estimar_tokens(texto)

    conteudo_final = "\n\n".join(partes)

    logger.info(
        "PromptLoader: query_tipo=%s gate=%s secoes=%s tokens_total=%d",
        tipo_upper, gate_upper, secoes_carregadas,
        sum(tokens_por_secao.values()),
    )

    return PromptLoadResult(
        conteudo_carregado=conteudo_final,
        secoes_carregadas=secoes_carregadas,
        tokens_por_secao=tokens_por_secao,
    )


def gerar_context_budget_log(
    prompt_version: str,
    query_tipo: str,
    load_result: PromptLoadResult,
    chunks_texto: str,
    overhead_texto: str = "",
    budget_total: int = 12100,
) -> str:
    """Gera log estruturado do budget de contexto consumido."""
    lines = [f"[PROMPT:COMPOSE:START] {prompt_version} query_tipo={query_tipo}"]

    for secao, tokens in load_result.tokens_por_secao.items():
        lines.append(f"  [SECTION:LOADED] [{secao}] {tokens} tokens")

    tokens_chunks = _estimar_tokens(chunks_texto)
    lines.append(f"  [RAG:CHUNKS] {tokens_chunks} tokens")

    tokens_overhead = _estimar_tokens(overhead_texto) if overhead_texto else 0
    if tokens_overhead:
        lines.append(f"  [OVERHEAD] instrucoes_saida {tokens_overhead} tokens")

    total = sum(load_result.tokens_por_secao.values()) + tokens_chunks + tokens_overhead
    disponivel = max(0, budget_total - total)
    lines.append(f"[PROMPT:COMPOSE:COMPLETE] Total: {total} tokens | Budget disponivel: {disponivel} tokens")

    return "\n".join(lines)
