# CORPUS_GOVERNANCE.md
# Tribus-AI Light — Governança do Corpus Tributário
**Versão:** 1.0
**Data:** Abril 2026
**Responsável atual:** PO (Jair Fahl) — até contratação de Corpus Manager
**Localização:** `/downloads/tribus-ai-light/CORPUS_GOVERNANCE.md`

---

## 1. Objetivo

Garantir que o corpus do Tribus-AI reflita a legislação tributária vigente com latência
máxima de **7 dias corridos** entre a publicação oficial de uma norma e sua disponibilidade
para consulta na plataforma.

Sem governança ativa, o maior risco do produto não é técnico — é o corpus desatualizado
gerando respostas incorretas sobre a Reforma Tributária em plena transição regulatória
(2026–2033).

---

## 2. Fontes Monitoradas

### 2.1 Fontes Primárias Obrigatórias (verificar 2x por semana)

| Fonte | URL | O que monitorar | Frequência |
|---|---|---|---|
| Diário Oficial da União — Seção 1 | https://www.in.gov.br/leiturajornal | Atos com termos: "IBS", "CBS", "IS", "Comitê Gestor", "LC 214", "LC 227", "Reforma Tributária" | 2x/semana (seg e qui) |
| Comitê Gestor do IBS | https://www.gov.br/comitegestoribs | Resoluções, Portarias, Instruções Normativas do CG-IBS | 2x/semana |
| Receita Federal — Legislação | https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/legislacao | INs RFB relativas a CBS e IS | 2x/semana |
| Planalto — LC e Decretos | https://www.planalto.gov.br/ccivil_03/leis/lcp/ | Leis Complementares e Decretos Regulamentadores | 2x/semana |

### 2.2 Fontes Secundárias (verificar 1x por semana)

| Fonte | URL | O que monitorar |
|---|---|---|
| SEFAZ portais estaduais (SP, RJ, MG, RS, BA) | Variável por estado | Alíquotas IBS estaduais/municipais, convênios |
| JOTA Tributário | https://www.jota.info/tributos-e-empresas/tributario | Interpretações relevantes, teses emergentes |
| CARF — Acórdãos | https://carf.economia.gov.br | Acórdãos relevantes CBS/IBS quando disponíveis |

### 2.3 Alertas Automatizáveis (implementar quando houver capacidade)

- RSS do DOU Seção 1 filtrado por termos tributários
- Google Alerts: "CBS IBS", "Comitê Gestor IBS", "Instrução Normativa RFB CBS"

---

## 3. Critérios de Ingestão

### 3.1 O que ENTRA no corpus

| Tipo de documento | Critério |
|---|---|
| Lei Complementar | Qualquer LC que altere CBS, IBS ou IS |
| Instrução Normativa RFB | Quando trata de CBS, IS ou obrigações acessórias da Reforma |
| Resolução CG-IBS | Toda resolução do Comitê Gestor (escopo total) |
| Portaria / Decreto Regulamentador | Quando regulamenta artigos de LC 214/2025 ou LC 227/2026 |
| Parecer Normativo | Quando emite interpretação oficial vinculante |
| Acórdão CARF / STJ / STF | Quando forma precedente relevante em CBS/IBS |
| Convênio CONFAZ (residual) | Apenas os que impactam transição ICMS → IBS (2026–2032) |

### 3.2 O que NÃO entra

- Notícias, artigos de opinião, posts de blog (mesmo de especialistas)
- Minutas e anteprojetos não publicados no DOU
- Normas sem vigência definida (aguardar publicação final)
- Normas de outros tributos sem conexão com a Reforma (ex: IRPJ isolado)

### 3.3 Metadados obrigatórios por norma

Todo documento ingerido deve ter os seguintes metadados preenchidos
**antes** da indexação (o PTF depende disso):

```
norm_tipo:         [LEI_COMPLEMENTAR | INSTRUCAO_NORMATIVA | RESOLUCAO | DECRETO | ACORDAO | PARECER]
numero:            número oficial da norma
ano:               ano de publicação
ementa:            texto oficial da ementa
tributos:          [CBS | IBS | IS | TODOS]
vigencia_inicio:   data de início da vigência (formato: AAAA-MM-DD)
vigencia_fim:      NULL se ainda vigente | data se revogada
regime:            [ATUAL | TRANSICAO | POS_REFORMA]
grau_consolidacao: [EMERGENTE | ESTAVEL | CONSOLIDADO]
fonte_url:         URL do documento oficial
data_ingestao:     data em que foi incluído no corpus
```

### 3.4 Normas revogadas

**Nunca deletar.** Marcar `vigencia_fim` com a data de revogação.
O PTF usa `vigencia_inicio` e `vigencia_fim` para filtrar documentos pelo período de referência do caso.
Deletar normas revogadas quebra consultas retrospectivas.

---

## 4. Processo de Ingestão

### 4.1 Fluxo padrão (executar via Claude Code no terminal)

```bash
# Passo 1: Baixar o PDF do documento oficial
# (salvar em /downloads/tribus-ai-light/corpus/incoming/)

# Passo 2: Executar pipeline de ingestão (ESP-10)
cd /downloads/tribus-ai-light
python src/ingestion/ingest.py \
  --file corpus/incoming/<nome_do_arquivo>.pdf \
  --norm-tipo INSTRUCAO_NORMATIVA \
  --numero "001" \
  --ano 2026 \
  --tributos CBS IBS \
  --vigencia-inicio 2026-04-01 \
  --regime TRANSICAO \
  --fonte-url "https://www.in.gov.br/..."

# Passo 3: Validar ingestão
python src/ingestion/validate_corpus.py --norm-id <id_retornado>

# Passo 4: Verificar contagem de chunks no banco
docker exec tribus-ai-db psql -U taxmind -d taxmind_db -c \
  "SELECT norm_id, COUNT(*) as chunks, COUNT(embedding) as embeddings
   FROM chunks WHERE norm_id = '<id>' GROUP BY norm_id;"
```

### 4.2 Critério de sucesso da ingestão

- `chunks` > 0
- `embeddings` = `chunks` (sem embeddings faltando)
- Norma aparece em query de teste relevante ao seu conteúdo

### 4.3 Ingestão de norma revogadora

Quando uma norma B revoga a norma A:

```bash
# 1. Ingerir norma B normalmente
# 2. Atualizar vigencia_fim da norma A
docker exec tribus-ai-db psql -U taxmind -d taxmind_db -c \
  "UPDATE norms SET vigencia_fim = '2026-XX-XX', grau_consolidacao = 'CONSOLIDADO'
   WHERE id = '<id_norma_A>';"
```

---

## 5. Atualização de `grau_consolidacao`

| Situação | grau_consolidacao |
|---|---|
| Norma publicada há menos de 30 dias, sem regulamentação complementar | EMERGENTE |
| Norma com regulamentação parcial ou interpretação ainda em formação | ESTAVEL |
| Norma com regulamentação completa e jurisprudência assentada | CONSOLIDADO |

Revisar o `grau_consolidacao` de normas existentes sempre que uma nova norma complementar
for ingerida.

---

## 6. Checklist Semanal do Corpus Manager

Execute toda **segunda-feira** antes das 10h:

```
[ ] Verificar DOU Seção 1 (seg + qui da semana anterior)
[ ] Verificar portal Comitê Gestor IBS
[ ] Verificar RFB — novas INs
[ ] Verificar Planalto — novas LCs ou Decretos
[ ] Para cada norma nova identificada:
    [ ] Avaliar critério de ingestão (Seção 3.1)
    [ ] Preencher metadados (Seção 3.3)
    [ ] Executar pipeline de ingestão (Seção 4.1)
    [ ] Validar resultado (Seção 4.2)
    [ ] Atualizar normas revogadas se aplicável (Seção 4.3)
    [ ] Revisar grau_consolidacao de normas relacionadas (Seção 5)
[ ] Registrar no log de curadoria (Seção 7)
```

---

## 7. Log de Curadoria

Registrar toda ingestão e atualização no arquivo:
`/downloads/tribus-ai-light/corpus/CURADORIA_LOG.md`

Formato de entrada:

```
## 2026-04-07

### Ingerido
- IN RFB 001/2026 — CBS: alíquotas para serviços digitais
  chunks: 47 | embeddings: 47 | regime: TRANSICAO | vigencia: 2026-04-01

### Atualizado
- LC 214/2025 art. 53: grau_consolidacao EMERGENTE → ESTAVEL
  (motivado pela IN RFB 001/2026 que regulamenta o artigo)

### Descartado
- Notícia JOTA sobre PL de reforma do IS: não é norma publicada
```

---

## 8. Alertas de Qualidade do Corpus

Executar mensalmente:

```bash
# Normas sem embedding (falha silenciosa de ingestão)
docker exec tribus-ai-db psql -U taxmind -d taxmind_db -c \
  "SELECT n.id, n.norm_tipo, n.numero, n.ano
   FROM norms n
   LEFT JOIN chunks c ON c.norm_id = n.id
   WHERE c.id IS NULL;"

# Normas EMERGENTE com mais de 60 dias (candidatas a revisão de grau)
docker exec tribus-ai-db psql -U taxmind -d taxmind_db -c \
  "SELECT id, norm_tipo, numero, ano, vigencia_inicio
   FROM norms
   WHERE grau_consolidacao = 'EMERGENTE'
   AND vigencia_inicio < NOW() - INTERVAL '60 days';"

# Normas sem vigencia_fim que foram revogadas implicitamente
-- (executar manualmente após comparar com legislação atual)
```

---

## 9. Escopo Futuro (Corpus Manager contratado)

Quando houver Corpus Manager dedicado, adicionar:

- Monitoramento diário automatizado (RSS + alertas)
- Validação cruzada com especialista tributário antes de ingestão
- Ontologia de remissões (`remissao_norm_id`) para RAR
- Indexação de acórdãos CARF e STJ em escala
- Fine-tuning dataset curation (pré-requisito para Onda 3 SLM)

---

*Este documento é o único registro oficial do processo de governança do corpus.
Qualquer alteração no processo deve ser versionada aqui antes de ser aplicada.*
