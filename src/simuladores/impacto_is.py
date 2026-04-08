"""
MP-04 — Calculadora de Impacto IS (Imposto Seletivo).
DC v7, Seção: Métodos Proprietários — Capítulo RT.

Calcula o impacto do IS na cadeia de preços para produtos seletivos.
ATENÇÃO: alíquotas do IS ainda não regulamentadas por lei específica.
Cálculo usa faixas estimadas com ressalva explícita obrigatória.
Fundamentação: EC 132/2023 + LC 214/2025, arts. 411–453.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ── PRODUTOS SUJEITOS AO IS (art. 412, LC 214/2025) ─────────────────────────
# Alíquotas estimadas — sujeitas a regulamentação por lei ordinária
PRODUTOS_IS: dict[str, dict] = {
    "tabaco": {
        "label": "Produtos do Tabaco",
        "aliquota_estimada_min": 0.10,
        "aliquota_estimada_max": 0.30,
        "aliquota_base": 0.20,
        "base_legal": "LC 214/2025, art. 412, I",
        "confirmada": False,
    },
    "bebidas_alcoolicas": {
        "label": "Bebidas Alcoólicas",
        "aliquota_estimada_min": 0.05,
        "aliquota_estimada_max": 0.15,
        "aliquota_base": 0.10,
        "base_legal": "LC 214/2025, art. 412, II",
        "confirmada": False,
    },
    "bebidas_acucaradas": {
        "label": "Bebidas Açucaradas",
        "aliquota_estimada_min": 0.02,
        "aliquota_estimada_max": 0.08,
        "aliquota_base": 0.04,
        "base_legal": "LC 214/2025, art. 412, III",
        "confirmada": False,
    },
    "veiculos": {
        "label": "Veículos Automotores",
        "aliquota_estimada_min": 0.01,
        "aliquota_estimada_max": 0.05,
        "aliquota_base": 0.02,
        "base_legal": "LC 214/2025, art. 412, IV",
        "confirmada": False,
    },
    "embarcacoes": {
        "label": "Embarcações e Aeronaves",
        "aliquota_estimada_min": 0.01,
        "aliquota_estimada_max": 0.05,
        "aliquota_base": 0.02,
        "base_legal": "LC 214/2025, art. 412, V",
        "confirmada": False,
    },
    "minerais": {
        "label": "Extração de Minérios",
        "aliquota_estimada_min": 0.01,
        "aliquota_estimada_max": 0.03,
        "aliquota_base": 0.01,
        "base_legal": "LC 214/2025, art. 412, VI",
        "confirmada": False,
    },
}


@dataclass
class CenarioIS:
    produto: str
    preco_venda_atual: float
    volume_mensal: int
    custo_producao: float
    elasticidade: str                           # 'alta' | 'media' | 'baixa'
    aliquota_customizada: Optional[float] = None


@dataclass
class ResultadoIS:
    produto_label: str
    base_legal: str
    aliquota_usada: float
    status_aliquota: str                        # 'estimada' | 'confirmada'

    is_por_unidade: float
    preco_com_is: float
    margem_atual: float
    margem_com_is: float
    delta_margem: float

    receita_atual_mensal: float
    receita_com_is_mensal: float
    is_total_mensal: float
    impacto_margem_mensal: float

    repassar_consumidor: dict = field(default_factory=dict)
    absorver_margem: dict = field(default_factory=dict)
    ressalvas: list[str] = field(default_factory=list)


def calcular_impacto_is(cenario: CenarioIS) -> ResultadoIS:
    """Calcula o impacto do IS para um produto/cenário."""
    config = PRODUTOS_IS.get(cenario.produto, {})
    aliquota = cenario.aliquota_customizada or config.get("aliquota_base", 0.10)
    status = "confirmada" if config.get("confirmada") else "estimada"

    # IS calculado "por fora" (sobre preço sem IS)
    is_unit = cenario.preco_venda_atual * aliquota
    preco_com_is = cenario.preco_venda_atual + is_unit

    margem_atual = cenario.preco_venda_atual - cenario.custo_producao

    # Cenário 1: repassar IS ao consumidor
    preco_repassado = preco_com_is
    margem_repassado = preco_repassado - cenario.custo_producao - is_unit  # margem preservada

    # Cenário 2: absorver IS na margem
    margem_absorvido = cenario.preco_venda_atual - cenario.custo_producao - is_unit

    reducao_volume = {"alta": 0.15, "media": 0.08, "baixa": 0.03}.get(cenario.elasticidade, 0.08)

    receita_atual = cenario.preco_venda_atual * cenario.volume_mensal
    is_total = is_unit * cenario.volume_mensal
    receita_com_is = preco_com_is * cenario.volume_mensal * (1 - reducao_volume)

    ressalvas = [
        f"Alíquota IS de {aliquota:.0%} é ESTIMADA — "
        f"sujeita a regulamentação por lei ordinária. {config.get('base_legal', '')}",
        "O IS incide 'por fora' do preço (aumenta o preço final ao consumidor).",
        f"Elasticidade '{cenario.elasticidade}' estimada — "
        "redução de volume real depende do mercado específico.",
    ]

    return ResultadoIS(
        produto_label=config.get("label", cenario.produto),
        base_legal=config.get("base_legal", ""),
        aliquota_usada=aliquota,
        status_aliquota=status,

        is_por_unidade=is_unit,
        preco_com_is=preco_com_is,
        margem_atual=margem_atual,
        margem_com_is=margem_absorvido,
        delta_margem=margem_absorvido - margem_atual,

        receita_atual_mensal=receita_atual,
        receita_com_is_mensal=receita_com_is,
        is_total_mensal=is_total,
        impacto_margem_mensal=(margem_absorvido - margem_atual) * cenario.volume_mensal,

        repassar_consumidor={
            "preco_final": preco_repassado,
            "reducao_volume_estimada_pct": reducao_volume,
            "volume_pos_repasse": int(cenario.volume_mensal * (1 - reducao_volume)),
            "margem_mantida": True,
        },
        absorver_margem={
            "preco_final": cenario.preco_venda_atual,
            "reducao_volume": 0,
            "nova_margem": margem_absorvido,
            "nova_margem_pct": margem_absorvido / cenario.preco_venda_atual
                               if cenario.preco_venda_atual > 0 else 0,
        },
        ressalvas=ressalvas,
    )
