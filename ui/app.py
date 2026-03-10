"""
ui/app.py — Interface Streamlit para TaxMind Light.
Aba 1: Consultar · Aba 2: Carregar Documento · Aba 3: Protocolo P1→P9
Consome a FastAPI em http://localhost:8000.
"""

import os

import httpx
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")

st.set_page_config(
    page_title="TaxMind Light — Reforma Tributária",
    page_icon="⚖️",
    layout="wide",
)


# --- Buscar normas disponíveis do /v1/health ---
@st.cache_data(ttl=30)
def _buscar_normas_disponiveis() -> dict[str, str]:
    """Retorna dict {nome_display: codigo} buscado dinamicamente da API."""
    try:
        hr = httpx.get(f"{API_BASE}/v1/health", timeout=3)
        normas = hr.json().get("normas", [])
        return {n["nome"]: n["codigo"] for n in normas}
    except Exception:
        # Fallback estático se API offline
        return {
            "EC 132/2023": "EC132_2023",
            "LC 214/2025": "LC214_2025",
            "LC 227/2026": "LC227_2026",
        }


# --- Sidebar ---
st.sidebar.title("⚖️ TaxMind Light")
st.sidebar.caption("Reforma Tributária · Base dinâmica de normas")

normas_disponiveis = _buscar_normas_disponiveis()

normas_sel = st.sidebar.multiselect(
    "Filtrar por norma",
    options=list(normas_disponiveis.keys()),
    default=list(normas_disponiveis.keys()),
)
norma_filter = [normas_disponiveis[n] for n in normas_sel] if normas_sel else None

top_k = st.sidebar.slider("Top-K chunks", min_value=1, max_value=5, value=3)

st.sidebar.divider()

# Health check na sidebar
try:
    hr = httpx.get(f"{API_BASE}/v1/health", timeout=3)
    hdata = hr.json()
    st.sidebar.success(
        f"API online · {hdata['chunks_total']:,} chunks · "
        f"{hdata['embeddings_total']:,} embeddings · "
        f"{len(hdata.get('normas', []))} normas"
    )
except Exception:
    st.sidebar.error("API offline — certifique-se que o servidor FastAPI está rodando")

# --- Abas ---
aba1, aba2, aba3 = st.tabs(["Consultar", "Carregar Documento", "Protocolo P1→P9"])


# ===========================================================================
# ABA 1 — Consultar
# ===========================================================================
with aba1:
    st.title("TaxMind Light — Reforma Tributária")
    st.caption("Análise tributária com grounding legislativo · Sem pareceres jurídicos formais")

    query = st.text_area(
        "Sua consulta tributária",
        placeholder="Ex: Como funciona o split payment para e-commerce com plataforma digital intermediária?",
        height=100,
    )

    if st.button("Analisar", type="primary", disabled=not query.strip()):
        with st.spinner("Analisando..."):
            try:
                resp = httpx.post(
                    f"{API_BASE}/v1/analyze",
                    json={"query": query, "norma_filter": norma_filter, "top_k": top_k},
                    timeout=60,
                )
            except httpx.ConnectError:
                st.error("Não foi possível conectar à API. Verifique se o servidor FastAPI está rodando em localhost:8000.")
                st.stop()

        if resp.status_code == 400:
            err = resp.json()
            st.error("🔴 **Consulta Bloqueada**")
            st.write("**Motivos:**")
            for b in err.get("detail", {}).get("bloqueios", []):
                st.write(f"- {b}")
            st.stop()

        if resp.status_code != 200:
            st.error(f"Erro da API: {resp.status_code} — {resp.text[:300]}")
            st.stop()

        data = resp.json()
        status = data["qualidade"]["status"]
        scoring = data["scoring_confianca"]
        latencia = data["latencia_ms"]

        col1, col2, col3 = st.columns(3)
        with col1:
            if status == "verde":
                st.success("🟢 Qualidade: VERDE")
            elif status == "amarelo":
                st.warning("🟡 Qualidade: AMARELO")
            else:
                st.error("🔴 Qualidade: VERMELHO")
        with col2:
            badge = {"alto": "🟢 Alto", "medio": "🟡 Médio", "baixo": "🔴 Baixo"}.get(scoring, scoring)
            st.metric("Confiança", badge)
        with col3:
            st.metric("Latência", f"{latencia} ms")

        st.divider()

        disc = data.get("disclaimer")
        if disc:
            st.warning(f"⚠️ {disc}")

        st.subheader("Análise")
        if data["anti_alucinacao"]["bloqueado"]:
            st.error("❌ Resposta bloqueada pelo sistema anti-alucinação.")
        st.write(data["resposta"])

        grau = data["grau_consolidacao"]
        grau_icon = {"consolidado": "✅", "divergente": "⚠️", "indefinido": "❓"}.get(grau, "")
        st.caption(f"Grau de consolidação: {grau_icon} {grau.capitalize()}")

        if data["fundamento_legal"]:
            st.subheader("📋 Fundamento Legal")
            for art in data["fundamento_legal"]:
                st.write(f"- {art}")

        if data.get("contra_tese"):
            with st.expander("⚖️ Contra-tese"):
                st.write(data["contra_tese"])

        st.subheader("🔍 Verificação Anti-Alucinação")
        anti = data["anti_alucinacao"]
        ac1, ac2, ac3, ac4 = st.columns(4)
        ac1.metric("M1 Existência", "✓" if anti["m1_existencia"] else "✗")
        ac2.metric("M2 Validade", "✓" if anti["m2_validade"] else "⚠")
        ac3.metric("M3 Pertinência", "✓" if anti["m3_pertinencia"] else "✗")
        ac4.metric("M4 Consistência", "✓" if anti["m4_consistencia"] else "✗")
        if anti["flags"]:
            st.caption(f"Flags: {', '.join(anti['flags'])}")

        with st.expander(f"📄 Chunks utilizados ({len(data['chunks'])})"):
            for i, chunk in enumerate(data["chunks"], 1):
                st.markdown(
                    f"**[{i}]** `{chunk['norma_codigo']}` | "
                    f"`{chunk['artigo'] or 'artigo não identificado'}` "
                    f"| score={chunk['score_final']:.3f}"
                )
                st.text(chunk["texto"][:400] + ("..." if len(chunk["texto"]) > 400 else ""))
                if i < len(data["chunks"]):
                    st.divider()

        st.caption(f"Modelo: {data['model_id']} · Prompt: {data['prompt_version']}")


# ===========================================================================
# ABA 2 — Carregar Documento
# ===========================================================================
with aba2:
    st.title("Carregar Documento")
    st.caption("Adicione INs, Resoluções, Pareceres ou Manuais à base de conhecimento.")

    uploaded_file = st.file_uploader("Selecione o arquivo PDF", type=["pdf"])
    nome_doc = st.text_input(
        "Nome do documento",
        placeholder="Ex: IN RFB 2184/2024",
    )
    tipo_doc = st.selectbox(
        "Tipo",
        options=["IN", "Resolução", "Parecer", "Manual", "Outro"],
    )

    st.info(
        "Após ingerido, o documento estará disponível automaticamente "
        "nas consultas da Aba 1."
    )

    pode_ingerir = uploaded_file is not None and nome_doc.strip()

    if st.button("Ingerir Documento", type="primary", disabled=not pode_ingerir):
        with st.spinner(f"Processando '{nome_doc}'... (pode levar alguns minutos)"):
            try:
                resp = httpx.post(
                    f"{API_BASE}/v1/ingest/upload",
                    files={"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")},
                    data={"nome": nome_doc.strip(), "tipo": tipo_doc},
                    timeout=300,
                )
            except httpx.ConnectError:
                st.error("Não foi possível conectar à API.")
                st.stop()

        if resp.status_code == 200:
            r = resp.json()
            st.success(
                f"✅ **{r['nome']}** ingerido com sucesso — "
                f"{r['chunks']} chunks, {r['embeddings']} embeddings"
            )
            st.caption(f"Código interno: `{r['codigo']}` · norma_id={r['norma_id']}")
            # Invalidar cache de normas para que a Aba 1 atualize o multiselect
            _buscar_normas_disponiveis.clear()
            st.info("Recarregue a página para ver o novo documento no filtro da Aba 1.")
        else:
            try:
                detalhe = resp.json().get("detail", resp.text[:200])
            except Exception:
                detalhe = resp.text[:200]
            st.error(f"❌ Erro ao ingerir documento: {detalhe}")


# ===========================================================================
# ABA 3 — Protocolo P1→P9
# ===========================================================================
PASSO_NOME = {
    1: "P1 · Registrar",
    2: "P2 · Contextualizar",
    3: "P3 · Estruturar",
    4: "P4 · Analisar",
    5: "P5 · Formular Hipótese",
    6: "P6 · Recomendar",
    7: "P7 · Decidir",
    8: "P8 · Monitorar",
    9: "P9 · Aprender",
}
STATUS_BADGE = {
    "rascunho": "🔵",
    "em_analise": "🟡",
    "aguardando_hipotese": "🟠",
    "decidido": "🟢",
    "em_monitoramento": "🔵",
    "aprendizado_extraido": "✅",
}

with aba3:
    st.title("Protocolo de Decisão Tributária P1→P9")
    st.caption(
        "Registre, analise e documente decisões tributárias com rastreabilidade completa. "
        "P5 (hipótese do gestor) deve ser concluído antes de ver a recomendação da IA (P6)."
    )

    # ------ Seção: Criar novo caso ------
    with st.expander("➕ Criar Novo Caso", expanded=False):
        with st.form("form_criar_caso"):
            titulo_caso = st.text_input("Título do caso (mín. 10 chars)", placeholder="Ex: Apuração CBS — CNPJ 12.345.678/0001-90")
            descricao_caso = st.text_area("Descrição", placeholder="Descreva o contexto do caso...", height=80)
            contexto_fiscal = st.text_input("Contexto fiscal", placeholder="Ex: Empresa de serviços de TI — Lucro Presumido")
            submitted_criar = st.form_submit_button("Criar Caso", type="primary")

        if submitted_criar:
            if not titulo_caso.strip() or len(titulo_caso.strip()) < 10:
                st.error("Título deve ter no mínimo 10 caracteres.")
            elif not descricao_caso.strip() or not contexto_fiscal.strip():
                st.error("Preencha todos os campos.")
            else:
                try:
                    r = httpx.post(
                        f"{API_BASE}/v1/cases",
                        json={"titulo": titulo_caso.strip(), "descricao": descricao_caso.strip(),
                              "contexto_fiscal": contexto_fiscal.strip()},
                        timeout=10,
                    )
                    if r.status_code == 201:
                        d = r.json()
                        st.success(f"✅ Caso criado — ID: **{d['case_id']}** · Status: {d['status']}")
                        st.info(f"Guarde o Case ID: `{d['case_id']}` para continuar o protocolo.")
                    else:
                        st.error(f"Erro: {r.json().get('detail', r.text[:200])}")
                except httpx.ConnectError:
                    st.error("API offline.")

    st.divider()

    # ------ Seção: Consultar estado do caso ------
    st.subheader("Consultar / Avançar Caso")
    case_id_input = st.number_input("Case ID", min_value=1, step=1, value=1)

    col_load, col_refresh = st.columns([1, 4])
    with col_load:
        load_case = st.button("Carregar Caso")

    if load_case or st.session_state.get("_proto_case_id") == case_id_input:
        st.session_state["_proto_case_id"] = case_id_input
        try:
            r = httpx.get(f"{API_BASE}/v1/cases/{case_id_input}", timeout=10)
        except httpx.ConnectError:
            st.error("API offline.")
            st.stop()

        if r.status_code == 404:
            st.warning(f"Caso {case_id_input} não encontrado.")
        elif r.status_code != 200:
            st.error(f"Erro: {r.text[:200]}")
        else:
            caso = r.json()
            passo_atual = caso["passo_atual"]
            status = caso["status"]
            badge = STATUS_BADGE.get(status, "")

            st.markdown(f"### {badge} {caso['titulo']}")
            st.caption(f"Passo atual: **{PASSO_NOME.get(passo_atual, str(passo_atual))}** · Status: `{status}`")

            # Progresso visual
            progress_val = (passo_atual - 1) / 8.0
            st.progress(progress_val, text=f"Passo {passo_atual}/9")

            # Histórico colapsado
            with st.expander("📜 Histórico de transições"):
                for h in caso["historico"]:
                    st.caption(
                        f"`{h['created_at'][:19]}` — P{h['passo_de'] or '?'} → P{h['passo_para']} "
                        f"({h['status_de'] or 'início'} → {h['status_para']}) — {h['motivo'] or ''}"
                    )

            st.divider()

            # ------ Formulário de avanço por passo ------
            st.subheader(f"Submeter dados — {PASSO_NOME.get(passo_atual, str(passo_atual))}")

            with st.form(f"form_passo_{passo_atual}"):
                dados_passo = {}

                if passo_atual == 1:
                    dados_passo["titulo"] = st.text_input("Título", value=caso["titulo"])
                    dados_passo["descricao"] = st.text_area("Descrição")
                    dados_passo["contexto_fiscal"] = st.text_input("Contexto fiscal")

                elif passo_atual == 2:
                    premissa1 = st.text_input("Premissa 1")
                    premissa2 = st.text_input("Premissa 2")
                    premissa3 = st.text_input("Premissa 3 (opcional)")
                    dados_passo["premissas"] = [p for p in [premissa1, premissa2, premissa3] if p.strip()]
                    dados_passo["periodo_fiscal"] = st.text_input("Período fiscal", placeholder="Ex: 2025-01 a 2025-12")

                elif passo_atual == 3:
                    risco1 = st.text_input("Risco identificado 1")
                    risco2 = st.text_input("Risco identificado 2 (opcional)")
                    dados_passo["riscos"] = [r for r in [risco1, risco2] if r.strip()]
                    dados_passo["dados_qualidade"] = st.text_area("Qualidade dos dados", placeholder="Descreva a qualidade dos dados disponíveis...")

                elif passo_atual == 4:
                    dados_passo["query_analise"] = st.text_area(
                        "Query para análise cognitiva",
                        placeholder="Ex: Qual a alíquota do IBS para serviços de TI sob Lucro Presumido?",
                        height=80,
                    )
                    dados_passo["analise_result"] = st.text_area(
                        "Resultado da análise (cole o output do /v1/analyze)",
                        height=120,
                    )

                elif passo_atual == 5:
                    st.info("Esta é a hipótese do gestor — registre ANTES de ver a recomendação da IA (P6).")
                    dados_passo["hipotese_gestor"] = st.text_area(
                        "Sua hipótese de decisão",
                        placeholder="Descreva sua hipótese independente sobre como resolver este caso...",
                        height=120,
                    )

                elif passo_atual == 6:
                    dados_passo["recomendacao"] = st.text_area(
                        "Recomendação baseada na análise da IA",
                        height=120,
                    )

                elif passo_atual == 7:
                    st.warning("⚠️ A decisão final será comparada com a recomendação da IA para verificação de carimbo.")
                    dados_passo["decisao_final"] = st.text_area(
                        "Decisão final do gestor",
                        height=120,
                    )
                    dados_passo["decisor"] = st.text_input("Nome do decisor responsável")

                elif passo_atual == 8:
                    dados_passo["resultado_real"] = st.text_area("Resultado real observado", height=80)
                    dados_passo["data_revisao"] = st.text_input("Data de revisão", placeholder="YYYY-MM-DD")

                elif passo_atual == 9:
                    dados_passo["padrao_extraido"] = st.text_area(
                        "Padrão extraído para aprendizado futuro",
                        placeholder="Descreva o padrão aprendido com este caso...",
                        height=100,
                    )

                col_av, col_vo = st.columns([2, 1])
                with col_av:
                    btn_avancar = st.form_submit_button("Avançar →", type="primary")
                with col_vo:
                    btn_voltar = st.form_submit_button("← Voltar")

            if btn_avancar or btn_voltar:
                acao = "voltar" if btn_voltar else "avancar"
                try:
                    r2 = httpx.post(
                        f"{API_BASE}/v1/cases/{case_id_input}/steps/{passo_atual}",
                        json={"dados": dados_passo, "acao": acao},
                        timeout=120,
                    )
                except httpx.ConnectError:
                    st.error("API offline.")
                    st.stop()

                if r2.status_code == 422:
                    st.error(f"Erro de validação: {r2.json().get('detail', '')}")
                elif r2.status_code != 200:
                    st.error(f"Erro {r2.status_code}: {r2.text[:200]}")
                else:
                    d2 = r2.json()
                    novo_passo = d2["passo"]
                    st.success(f"✅ Movido para {PASSO_NOME.get(novo_passo, str(novo_passo))}")

                    # Exibir alerta de carimbo se presente
                    carimbo = d2.get("carimbo")
                    if carimbo and carimbo.get("alerta"):
                        st.warning(f"🔔 **Alerta Carimbo** — {carimbo['mensagem']}")
                        st.caption(f"Score de similaridade: {carimbo['score_similaridade']:.0%} · alert_id={carimbo['alert_id']}")

                        with st.form("form_confirmar_carimbo"):
                            justificativa = st.text_area(
                                "Justificativa (mín. 20 chars) — confirme que esta é sua posição independente",
                                height=80,
                            )
                            if st.form_submit_button("Confirmar Decisão Independente"):
                                try:
                                    rc = httpx.post(
                                        f"{API_BASE}/v1/cases/{case_id_input}/carimbo/confirmar",
                                        json={"alert_id": carimbo["alert_id"], "justificativa": justificativa},
                                        timeout=10,
                                    )
                                    if rc.status_code == 200:
                                        st.success("Carimbo confirmado com justificativa registrada.")
                                    else:
                                        st.error(rc.json().get("detail", rc.text[:200]))
                                except httpx.ConnectError:
                                    st.error("API offline.")

                    # Forçar recarga do caso
                    st.session_state["_proto_case_id"] = case_id_input
                    st.rerun()
