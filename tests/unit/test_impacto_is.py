"""
tests/unit/test_impacto_is.py — Testes unitários do MP-04 (C5, G21).
"""

from src.simuladores.impacto_is import (
    PRODUTOS_IS,
    CenarioIS,
    calcular_impacto_is,
)


def test_seis_produtos_mapeados():
    assert len(PRODUTOS_IS) >= 6


def test_aliquotas_nao_confirmadas():
    for prod_id, config in PRODUTOS_IS.items():
        assert config["confirmada"] is False, f"{prod_id} marcado como confirmado"


def test_is_calculado_por_fora():
    # IS "por fora" → preco_com_is = preco + IS
    c = CenarioIS(produto="tabaco", preco_venda_atual=10.0,
                  volume_mensal=1000, custo_producao=5.0, elasticidade="media")
    r = calcular_impacto_is(c)
    assert abs(r.preco_com_is - (10.0 + r.is_por_unidade)) < 0.001


def test_absorver_reduz_margem():
    c = CenarioIS(produto="bebidas_alcoolicas", preco_venda_atual=20.0,
                  volume_mensal=500, custo_producao=10.0, elasticidade="media")
    r = calcular_impacto_is(c)
    assert r.absorver_margem["nova_margem"] < r.margem_atual


def test_ressalvas_presentes_com_estimada():
    c = CenarioIS(produto="veiculos", preco_venda_atual=50_000.0,
                  volume_mensal=10, custo_producao=30_000.0, elasticidade="baixa")
    r = calcular_impacto_is(c)
    assert len(r.ressalvas) > 0
    assert "ESTIMADA" in r.ressalvas[0].upper()


def test_aliquota_customizada_sobrescreve_base():
    c = CenarioIS(produto="tabaco", preco_venda_atual=10.0,
                  volume_mensal=100, custo_producao=5.0,
                  elasticidade="media", aliquota_customizada=0.05)
    r = calcular_impacto_is(c)
    assert abs(r.aliquota_usada - 0.05) < 0.001
    assert abs(r.is_por_unidade - 0.50) < 0.001


def test_repassar_reduz_volume():
    c = CenarioIS(produto="bebidas_acucaradas", preco_venda_atual=5.0,
                  volume_mensal=1000, custo_producao=2.0, elasticidade="alta")
    r = calcular_impacto_is(c)
    assert r.repassar_consumidor["volume_pos_repasse"] < 1000
