"""
ui/pages/simulador_is.py — UI do MP-04: Calculadora de Impacto IS.
"""

from __future__ import annotations

import streamlit as st

from src.simuladores.impacto_is import (
    PRODUTOS_IS,
    CenarioIS,
    calcular_impacto_is,
)


def render_calculadora_is() -> None:
    st.header("⚡ Calculadora IS — MP-04")
    st.caption("Impacto do Imposto Seletivo na cadeia de preços.")
    st.error(
        "🔴 **Alíquotas do IS não regulamentadas.** "
        "Este simulador usa estimativas de mercado. "
        "Valores definitivos dependem de lei ordinária específica. "
        "Fundamentação: EC 132/2023 + LC 214/2025, arts. 411–453."
    )

    with st.form("form_is"):
        col1, col2 = st.columns(2)
        with col1:
            produto = st.selectbox(
                "Produto",
                options=list(PRODUTOS_IS.keys()),
                format_func=lambda x: PRODUTOS_IS[x]["label"],
            )
            preco = st.number_input("Preço de Venda Atual (R$/un)", 0.01, 10_000.0, 10.0)
            volume = st.number_input("Volume Mensal (unidades)", 1, 10_000_000, 10_000)

        with col2:
            custo = st.number_input("Custo de Produção (R$/un)", 0.0, 10_000.0, 5.0)
            elasticidade = st.selectbox(
                "Elasticidade de Demanda",
                ["alta", "media", "baixa"],
                format_func=lambda x: {
                    "alta": "Alta (-15% de volume se repassar)",
                    "media": "Média (-8%)",
                    "baixa": "Baixa (-3%)",
                }.get(x, x),
            )
            aliquota_pct = st.number_input(
                "Alíquota customizada (% — deixe 0 para usar estimativa)",
                0.0, 100.0, 0.0,
            )
            aliquota_custom: float | None = aliquota_pct / 100 if aliquota_pct > 0 else None

        submitted = st.form_submit_button("Calcular", type="primary")

    if submitted:
        cenario = CenarioIS(
            produto=produto,
            preco_venda_atual=preco,
            volume_mensal=volume,
            custo_producao=custo,
            elasticidade=elasticidade,
            aliquota_customizada=aliquota_custom,
        )
        r = calcular_impacto_is(cenario)

        st.divider()
        col1, col2, col3 = st.columns(3)
        col1.metric(
            "IS por Unidade",
            f"R$ {r.is_por_unidade:.2f}",
            delta=f"+{r.aliquota_usada:.0%} sobre preço atual",
        )
        col2.metric(
            "Impacto Margem/mês",
            f"R$ {abs(r.impacto_margem_mensal):,.0f}",
            delta=f"{r.delta_margem:+.2f}/un",
        )
        col3.metric("IS Total/mês", f"R$ {r.is_total_mensal:,.0f}")

        st.caption(
            f"Base legal: {r.base_legal} | "
            f"Alíquota: {r.aliquota_usada:.0%} ({r.status_aliquota})"
        )

        st.subheader("Comparativo de Estratégias")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**📤 Repassar ao Consumidor**")
            st.caption(f"Preço final: R$ {r.repassar_consumidor['preco_final']:.2f}")
            st.caption(
                f"Redução estimada de volume: "
                f"-{r.repassar_consumidor['reducao_volume_estimada_pct']:.0%}"
            )
            st.caption(
                f"Volume pós-repasse: "
                f"{r.repassar_consumidor['volume_pos_repasse']:,} un"
            )
            st.info("Margem preservada — risco de perda de mercado.")
        with col2:
            st.markdown("**📥 Absorver na Margem**")
            st.caption(f"Preço mantido: R$ {r.absorver_margem['preco_final']:.2f}")
            st.caption(
                f"Nova margem: R$ {r.absorver_margem['nova_margem']:.2f}/un "
                f"({r.absorver_margem['nova_margem_pct']:.1%})"
            )
            st.warning("Volume mantido — compressão de margem.")

        with st.expander("⚠ Ressalvas"):
            for res in r.ressalvas:
                st.caption(f"• {res}")
