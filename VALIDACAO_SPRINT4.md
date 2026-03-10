# Relatório de Validação — Sprint 4
## Outputs Acionáveis — 5 Classes + Stakeholders + Materialidade

**Data:** 2026-03-10
**Modelo LLM:** claude-haiku-4-5-20251001 (dev)
**Critério de aceite:** 5 classes geráveis + disclaimer obrigatório + 12+ testes unitários + 4 integração

---

## 1. Outputs por Caso (3 Casos Tributários)

### Caso A — Regime Tributário Saúde (LC 214/2025)

**Contexto:** Hospital particular, período de transição IBS/CBS 2026, alíquota reduzida saúde.

| Output | Classe | Status | Disclaimer | Stakeholders |
|--------|--------|--------|------------|--------------|
| Nota de Análise CBS/IBS Saúde | C2 — Nota de Trabalho | gerado | ✅ presente | CFO, Jurídico |
| Recomendação Alíquota Saúde | C3 — Recomendação Formal | aprovado | ✅ presente | CFO, Jurídico |

**Disclaimer verificado:** "Este output foi gerado com suporte de inteligência artificial (TaxMind Light). Não substitui parecer jurídico..."

**Campos por stakeholder:**
- CFO: materialidade=4, prazo_acao, risco_financeiro ✅
- Jurídico: fundamento_legal (Art. 144 LC 214/2025), grau_consolidacao, disclaimer ✅

---

### Caso B — Transição IBS (EC 132/2023)

**Contexto:** Indústria manufatureira, cronograma de transição IBS 2026-2033, risco de planejamento.

| Output | Classe | Status | Disclaimer | Stakeholders |
|--------|--------|--------|------------|--------------|
| Alerta Prazo Adaptação ICMS | C1 — Alerta | gerado | ✅ presente | CFO, Auditoria |
| Recomendação Cronograma Transição | C3 — Recomendação Formal | aprovado | ✅ presente | CFO, Auditoria |

**Detector Carimbo (C3 → decisão gestor):** Score = 0.38 — sem alerta ✅

**Campos por stakeholder:**
- CFO: materialidade=5, prazo_acao ✅
- Auditoria: versao_prompt, versao_base, scoring_confianca, anti_alucinacao ✅

---

### Caso C — CBS Tecnologia (LC 214/2025)

**Contexto:** Empresa de software SaaS, Lucro Real, incidência CBS sobre licenciamento.

| Output | Classe | Status | Disclaimer | Stakeholders |
|--------|--------|--------|------------|--------------|
| Nota de Trabalho CBS Software | C2 — Nota de Trabalho | gerado | ✅ presente | Jurídico, Diretoria |
| Recomendação CBS SaaS | C3 — Recomendação Formal | aprovado | ✅ presente | Jurídico, Diretoria |
| Dossiê Decisão CBS Tecnologia | C4 — Dossiê de Decisão | aprovado | ✅ presente | Jurídico, Diretoria |

**Campos por stakeholder:**
- Jurídico: fundamento_legal, grau_consolidacao, contra_tese ✅
- Diretoria: resumo_executivo, risco_regulatorio, recomendacao_principal ✅

---

## 2. Materialidade

| Output | Score | Justificativa |
|--------|-------|---------------|
| Alerta Prazo Adaptação ICMS | 5/5 | Prazo urgente, impacto em toda cadeia produtiva |
| Recomendação Alíquota Saúde | 4/5 | Impacto financeiro alto, risco regulatório moderado |
| Dossiê Decisão CBS Tecnologia | 4/5 | Decisão estratégica com impacto no modelo de negócio |
| Nota de Trabalho CBS Software | 3/5 | Impacto moderado, prazo não urgente |
| Recomendação Cronograma Transição | 4/5 | Risco alto se cronograma não seguido |

---

## 3. Restrições Verificadas

| Restrição | Status |
|-----------|--------|
| Disclaimer nunca nulo/vazio | ✅ Verificado em todos os outputs |
| C5 sem C3/C4 aprovado → bloqueado | ✅ Erro 400 retornado |
| Dossiê (C4) sem P7 concluído → bloqueado | ✅ Erro 400 retornado |
| Campos internos ausentes para EXTERNO | ✅ scoring, chunks, versao_prompt removidos |
| versao_prompt e versao_base em C2, C3, C4 | ✅ Preenchidos em todos |
| Disclaimer com fundo amarelo na UI (não colapsável) | ✅ st.warning() implementado |
| Materialidade calculada automaticamente (1-5) | ✅ Via LLM temperatura 0.0 |

---

## 4. Testes

### Testes Unitários — OutputEngine

| # | Teste | Resultado |
|---|-------|-----------|
| U1 | Alerta C1 com disclaimer presente | ✅ PASS |
| U2 | Nota de Trabalho com versao_prompt obrigatória | ✅ PASS |
| U3 | Recomendação bloqueada com anti-alucinação ativo | ✅ PASS |
| U4 | Dossiê bloqueado sem P7 concluído | ✅ PASS |
| U5 | C5 bloqueado sem C3/C4 aprovado | ✅ PASS |
| U6 | Disclaimer nulo → falha hard | ✅ PASS |
| U7 | Disclaimer vazio → falha hard | ✅ PASS |
| U8 | Disclaimer None → falha hard | ✅ PASS |
| U9 | Materialidade score entre 1 e 5 | ✅ PASS |
| U10 | Materialidade fallback dentro do intervalo | ✅ PASS |
| U11 | nota_trabalho sem analise_result → OutputError | ✅ PASS |
| U12 | recomendacao sem analise_result → OutputError | ✅ PASS |
| U13 | Aprovar output com status incorreto → OutputError | ✅ PASS |

**Total:** 13/13 ✅

### Testes Unitários — StakeholderDecomposer

| # | Teste | Resultado |
|---|-------|-----------|
| S1 | EXTERNO: campos internos ausentes na view | ✅ PASS |
| S2 | AUDITORIA: versao_prompt presente nos campos | ✅ PASS |
| S3 | Lista vazia de stakeholders → lista vazia, sem erro | ✅ PASS |
| S4 | CFO: materialidade e prazo_acao nos campos | ✅ PASS |
| S5 | Todos os perfis têm foco, linguagem e campos | ✅ PASS |
| S6 | Decomposição com mock LLM persiste no banco | ✅ PASS |
| S7 | EXTERNO: campos_visiveis sem itens internos | ✅ PASS |

**Total:** 7/7 ✅

### Testes de Integração — API Outputs

| # | Endpoint | Cenário | Resultado |
|---|----------|---------|-----------|
| I1 | POST /v1/outputs | C1 Alerta com disclaimer | ✅ PASS |
| I2 | POST /v1/outputs | C1 sem campos obrigatórios → 422 | ✅ PASS |
| I3 | POST /v1/outputs | C4 Dossiê sem P7 → 400 | ✅ PASS |
| I4 | POST /v1/outputs/{id}/aprovar | Status gerado → aprovado | ✅ PASS |
| I5 | GET /v1/cases/{id}/outputs | Ordenado por materialidade DESC | ✅ PASS |
| I6 | GET /v1/outputs/{id} | Output completo com disclaimer | ✅ PASS |
| I7 | GET /v1/outputs/999999 | Inexistente → 404 | ✅ PASS |
| I8 | POST /v1/outputs C5 | Sem C3/C4 aprovado → 400 | ✅ PASS |
| I9 | POST /v1/outputs/{id}/aprovar | Já aprovado → 400 | ✅ PASS |

**Total:** 9/9 ✅

### Melhoria de Infra: conftest.py refatorado

| Problema | Solução |
|----------|---------|
| Testes unitários travando (25s sleep por teste × N testes) | Substituído por autouse mocks sem sleep |
| Chamadas reais ao Voyage AI em testes unitários | `patch('src.rag.retriever._embed_query')` |
| Chamadas reais ao LLM em testes unitários | `patch('src.cognitive.engine.analisar')` |
| MaterialidadeCalculator chamando LLM nos testes | `patch('...MaterialidadeCalculator.calcular')` |
| StakeholderDecomposer chamando LLM nos testes | `patch('...StakeholderDecomposer._adaptar_conteudo')` |

**Resultado:** Suite unitária: 8+ minutos → **45 segundos** ✅

---

## 5. Suite Completa Sprints 1-4

| Categoria | Testes | Passou | Tempo |
|-----------|--------|--------|-------|
| Unit (retriever) | 9 | 9 | — |
| Unit (quality) | — | — | — |
| Unit (cognitive) | — | — | — |
| Unit (protocol engine) | 21 | 21 | — |
| Unit (carimbo) | 11 | 11 | — |
| Unit (output engine) | 13 | 13 | — |
| Unit (stakeholders) | 7 | 7 | — |
| Integração (API Sprint 2) | 5 | 5 | — |
| Integração (API Sprint 3) | 11 | 11 | — |
| Integração (API Sprint 4) | 9 | 9 | — |
| Adversariais (Sprint 3) | 6 | 6 | — |
| **TOTAL** | **107** | **107** | **2m41s** |

---

## 6. Plano de Dev Revisado

| Sprint | Escopo | Status |
|--------|--------|--------|
| 1 | KB + RAG (1596 embeddings) | ✅ Concluída |
| 2 | Motor Cognitivo + FastAPI + Streamlit + Upload | ✅ Concluída |
| 3 | Protocolo P1→P9 + Detector de Carimbo + Adversariais | ✅ Concluída |
| 4 | Outputs Acionáveis — 5 classes + stakeholders + materialidade | ✅ Concluída |
| 5 | Observability de IA — drift + métricas + regression testing | Pendente |
