"""
tests/unit/test_reestruturacao_rt.py — Testes unitários do MP-03 (C5, G20).
"""

from src.simuladores.reestruturacao_rt import (
    BENEFICIO_ICMS_UF,
    PHASEOUT_ICMS,
    UnidadeOperacional,
    analisar_reestruturacao,
)


def test_27_ufs_mapeadas():
    assert len(BENEFICIO_ICMS_UF) == 27


def test_phaseout_completo_em_2033():
    assert PHASEOUT_ICMS[2033] == 0.00


def test_phaseout_integral_em_2026():
    assert PHASEOUT_ICMS[2026] == 1.00


def test_unidade_incentivada_alto_impacto_recomenda_encerrar_ou_revisar():
    # AM tem benefício de 18% — sobre faturamento de 10M = 1.8M > 30% do custo fixo 1M
    u = UnidadeOperacional(
        uf="AM", tipo="CD",
        custo_fixo_anual=1_000_000.0,
        faturamento_anual=10_000_000.0,
        beneficio_icms_justifica=True,
    )
    r = analisar_reestruturacao([u])
    assert r.unidades[0].recomendacao in ["revisar", "encerrar"]


def test_unidade_nao_incentivada_sempre_manter():
    u = UnidadeOperacional(
        uf="SP", tipo="escritório",
        custo_fixo_anual=500_000.0,
        faturamento_anual=5_000_000.0,
        beneficio_icms_justifica=False,
    )
    r = analisar_reestruturacao([u])
    assert r.unidades[0].recomendacao == "manter"


def test_economia_total_soma_unidades():
    u1 = UnidadeOperacional(uf="SP", tipo="CD",
                             custo_fixo_anual=1_000_000.0, faturamento_anual=5_000_000.0)
    u2 = UnidadeOperacional(uf="MG", tipo="filial",
                             custo_fixo_anual=500_000.0, faturamento_anual=2_000_000.0)
    r = analisar_reestruturacao([u1, u2])
    esperado = (5_000_000.0 * 0.05) + (2_000_000.0 * 0.07)
    assert abs(r.economia_total_perdida_anual - esperado) < 0.01


def test_ressalvas_presentes():
    u = UnidadeOperacional(uf="RJ", tipo="planta",
                           custo_fixo_anual=1_000_000.0, faturamento_anual=5_000_000.0)
    r = analisar_reestruturacao([u])
    assert len(r.ressalvas) > 0
