"""
ui/pages/simulador_reestruturacao.py — UI do MP-03: Simulador de Reestruturação RT.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.simuladores.reestruturacao_rt import (
    BENEFICIO_ICMS_UF,
    UnidadeOperacional,
    analisar_reestruturacao,
)


def render_simulador_reestruturacao() -> None:
    st.header("🏭 Reestruturação RT — MP-03")
    st.caption(
        "Avalia se unidades operacionais criadas por incentivos de ICMS "
        "ainda fazem sentido após a extinção da guerra fiscal (IBS no destino)."
    )
    st.warning(
        "⚠ Alíquotas de ICMS por UF são estimativas de mercado. "
        "Valores reais dependem do regime estadual específico de cada empresa."
    )

    st.subheader("Informe suas unidades operacionais")
    n_unidades = st.number_input("Número de unidades a analisar", 1, 10, 2)

    unidades: list[UnidadeOperacional] = []
    for i in range(n_unidades):
        with st.expander(f"Unidade {i + 1}", expanded=(i == 0)):
            col1, col2 = st.columns(2)
            with col1:
                uf = st.selectbox(
                    "UF", options=sorted(BENEFICIO_ICMS_UF.keys()),
                    key=f"uf_{i}",
                )
                tipo = st.selectbox(
                    "Tipo", ["CD", "planta", "filial", "escritório"],
                    key=f"tipo_{i}",
                )
            with col2:
                fat = st.number_input(
                    "Faturamento Anual (R$)", min_value=0.0,
                    value=10_000_000.0, step=500_000.0,
                    format="%.0f", key=f"fat_{i}",
                )
                custo = st.number_input(
                    "Custo Fixo Anual (R$)", min_value=0.0,
                    value=2_000_000.0, step=100_000.0,
                    format="%.0f", key=f"custo_{i}",
                )
            incentivo = st.checkbox(
                "Foi criada por incentivo fiscal de ICMS?",
                value=True, key=f"inc_{i}",
            )
            unidades.append(UnidadeOperacional(
                uf=uf, tipo=tipo,
                faturamento_anual=fat,
                custo_fixo_anual=custo,
                beneficio_icms_justifica=incentivo,
            ))

    if st.button("Analisar", type="primary"):
        resultado = analisar_reestruturacao(unidades)

        st.divider()
        col1, col2, col3 = st.columns(3)
        col1.metric("Economia ICMS Perdida/ano",
                    f"R$ {resultado.economia_total_perdida_anual:,.0f}")
        col2.metric("Unidades p/ Revisar", resultado.unidades_revisar)
        col3.metric("Unidades p/ Encerrar", resultado.unidades_encerrar)

        _BADGE = {"manter": "✅ Manter", "revisar": "🟡 Revisar", "encerrar": "🔴 Encerrar"}
        dados = [
            {
                "UF": r.uf,
                "Tipo": r.tipo,
                "Benefício ICMS/ano": f"R$ {r.beneficio_icms_atual:,.0f}",
                "Benefício 2033": "R$ 0",
                "Perda/ano": f"R$ {r.economia_icms_perdida:,.0f}",
                "Recomendação": _BADGE.get(r.recomendacao, r.recomendacao),
                "Decisão crítica em": r.ano_decisao_critica,
            }
            for r in resultado.unidades
        ]
        st.dataframe(pd.DataFrame(dados), use_container_width=True, hide_index=True)

        for r in resultado.unidades:
            if r.recomendacao != "manter":
                st.caption(f"**{r.uf} ({r.tipo}):** {r.justificativa}")

        with st.expander("⚠ Ressalvas"):
            for res in resultado.ressalvas:
                st.caption(f"• {res}")
