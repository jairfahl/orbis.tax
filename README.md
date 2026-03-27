# TaxMind Light

Sistema de análise tributária com RAG e protocolo de decisão para a Reforma Tributária brasileira (EC 132/2023, LC 214/2025, LC 227/2026).

## O que é o TaxMind Light?

O TaxMind Light é uma ferramenta de suporte à decisão tributária composta por dois modos de uso:

- **Consulta rápida** — perguntas pontuais sobre a Reforma Tributária, respondidas com fundamentação legal via RAG
- **Protocolo de Decisão (6 passos)** — processo estruturado para análise, recomendação e decisão sobre cenários tributários complexos

## Funcionalidades

| Aba | Função |
|-----|--------|
| **Consultar** | Consulta rápida à base de conhecimento com indicadores de qualidade, fundamentação legal e ação recomendada |
| **Adicionar Norma** | Upload de PDFs (INs, Resoluções, Pareceres), detecção de duplicidade por hash MD5, ingestão assíncrona, listagem e exclusão de documentos, monitor de fontes oficiais |
| **Protocolo de Decisão** | Protocolo de 6 passos: registrar & classificar → estruturar riscos → análise TaxMind → posição do gestor → decidir → ciclo pós-decisão |
| **Documentos** | Geração de documentos acionáveis (Alerta, Nota de Trabalho, Recomendação Formal, Dossiê de Decisão, Material para Compartilhamento) com visões por stakeholder |

## Stack Técnica

| Componente | Tecnologia |
|------------|------------|
| Linguagem | Python 3.12 |
| Banco de dados | PostgreSQL 16 + pgvector (Docker Compose) |
| Embeddings | voyage-3 (1024 dim) via VoyageAI API |
| LLM | claude-haiku-4-5 (dev) / claude-sonnet-4-6 (prod) |
| API | FastAPI (uvicorn) |
| UI | Streamlit |
| Busca vetorial | pgvector com índice HNSW (cosine, m=16, ef=64) |
| Re-ranking | BM25 em memória (score híbrido: 0.7 cosine + 0.3 BM25) |

## Pré-requisitos

- Python 3.12+
- Docker + Docker Compose
- Chave VoyageAI API (voyage-3)
- Chave Anthropic API (Claude)

## Setup

### 1. Configurar variáveis de ambiente

```bash
cp .env.example .env
# Editar .env e preencher ANTHROPIC_API_KEY e VOYAGE_API_KEY
```

### 2. Subir tudo com Docker Compose

```bash
docker compose up -d --build
docker compose ps   # aguardar todos os serviços "Up" e DB "healthy"
```

Isso sobe 3 serviços:
- **db** — PostgreSQL 16 + pgvector (porta 5436)
- **api** — FastAPI/uvicorn (porta 8020)
- **ui** — Streamlit (porta 8521, com hot-reload via volume mount)

Acesse `http://localhost:8521` no navegador.

### 3. Rodar a ingestão inicial dos PDFs (primeira vez)

```bash
python src/ingest/run_ingest.py
```

### 4. Rodar os testes

```bash
pytest tests/unit/ -v
```

### Comandos úteis

```bash
docker compose down              # parar todos os serviços
docker compose up -d             # subir novamente
docker compose restart api       # reiniciar apenas a API
docker compose logs api --tail 50  # ver logs da API
```

## Arquitetura

```
PDF (upload ou PDF_SOURCE_DIR)
      │
      ▼
  loader.py ──► pdfplumber ──► texto extraído
      │
      ▼
 chunker.py ──► chunking hierárquico (artigo → parágrafo → sliding window)
      │
      ▼
 embedder.py ──► voyage-3 (batch 32, retry 3x)
      │
      ▼
PostgreSQL/pgvector ──► HNSW index (1024 dim)
      │
      ▼
 retriever.py ──► busca vetorial + BM25 re-ranking + deduplicação por artigo
      │
      ▼
 engine.py (cognitivo) ──► Claude LLM com anti-alucinação (M1-M4)
      │
      ▼
 Streamlit UI ◄──► FastAPI (19+ endpoints)
```

## Estrutura de Pastas

```
taxmind-light/
├── Dockerfile
├── docker-compose.yml
├── .env
├── requirements.txt
├── db/
│   └── init.sql
├── src/
│   ├── api/
│   │   └── main.py              # FastAPI — 19+ endpoints
│   ├── cognitive/
│   │   └── engine.py            # Motor cognitivo (Claude LLM)
│   ├── db/
│   │   └── pool.py              # Connection pool centralizado (ThreadedConnectionPool)
│   ├── ingest/
│   │   ├── loader.py            # Extração de texto dos PDFs
│   │   ├── chunker.py           # Chunking jurídico hierárquico
│   │   ├── embedder.py          # Embeddings voyage-3
│   │   └── run_ingest.py        # Pipeline de ingestão
│   ├── monitor/
│   │   ├── checker.py           # Verificação de fontes oficiais
│   │   └── sources.py           # Detectores por tipo de fonte
│   ├── observability/
│   │   ├── collector.py         # Métricas de uso
│   │   ├── drift.py             # Detecção de drift (2σ)
│   │   ├── regression.py        # Regression testing
│   │   └── usage.py             # Rastreamento de consumo de API
│   ├── outputs/
│   │   ├── engine.py            # Geração de documentos (5 classes)
│   │   ├── materialidade.py     # Cálculo de materialidade
│   │   └── stakeholders.py      # Decomposição por stakeholder
│   ├── protocol/
│   │   ├── engine.py            # Máquina de estados (6 passos)
│   │   └── carimbo.py           # Detector de terceirização cognitiva
│   ├── quality/
│   │   └── engine.py            # DataQualityEngine (BL-01, BL-02, BL-03)
│   └── rag/
│       ├── retriever.py         # Retrieval híbrido (vetorial + BM25)
│       └── spd.py               # SPD-RAG multi-norma
├── ui/
│   └── app.py                   # Streamlit (4 abas)
└── tests/
    └── unit/                    # Testes unitários (137+)
```

## Protocolo de Decisão — 6 Passos

| Passo | Nome | Responsável |
|-------|------|-------------|
| 1 | Registrar & Classificar | Usuário |
| 2 | Estruturar riscos e dados | Usuário |
| 3 | Análise tributária | TaxMind (RAG + LLM) |
| 4 | Posição do gestor (hipótese) | Usuário |
| 5 | Decidir | Usuário (com recomendação TaxMind) |
| 6 | Ciclo Pós-Decisão | Usuário |

## API — Principais Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/v1/health` | Status do sistema |
| GET | `/v1/credits` | Saldo de créditos de API |
| POST | `/v1/analyze` | Consulta RAG + LLM |
| GET | `/v1/chunks` | Busca de chunks |
| POST | `/v1/ingest/upload` | Upload assíncrono de PDF |
| POST | `/v1/ingest/check-duplicate` | Verificação de duplicidade |
| GET | `/v1/ingest/jobs/{job_id}` | Polling de ingestão |
| GET | `/v1/ingest/normas` | Listar documentos na base |
| DELETE | `/v1/ingest/normas/{norma_id}` | Remover documento da base |
| POST | `/v1/cases` | Criar caso |
| GET | `/v1/cases` | Listar casos |
| GET | `/v1/cases/{id}` | Detalhes do caso |
| POST | `/v1/cases/{id}/steps/{passo}` | Submeter passo |
| POST | `/v1/cases/{id}/carimbo/confirmar` | Confirmar independência decisória |
| GET | `/v1/cases/{id}/outputs` | Documentos do caso |
| POST | `/v1/outputs` | Gerar documento acionável |
| POST | `/v1/outputs/{id}/aprovar` | Aprovar documento |
| GET | `/v1/observability/metrics` | Métricas de uso |
| GET | `/v1/observability/drift` | Detecção de drift |
| POST | `/v1/observability/regression` | Validação automática |
| POST | `/v1/observability/baseline` | Registrar referência |
| GET | `/v1/observability/budget-pressure` | Budget de contexto |
| POST | `/v1/monitor/verificar` | Verificar fontes oficiais |
| GET | `/v1/monitor/pendentes` | Documentos pendentes |
| GET | `/v1/monitor/contagem` | Contagem de novos docs |

## UX

- Todos os campos possuem tooltip (?) imediatamente ao lado do label com explicação sobre o campo
- Placeholders genéricos orientativos (sem exemplos que enviezem o preenchimento)
- Hot-reload: edições no código local refletem no browser com refresh (volume mount Docker)
- Aba "Qualidade do Sistema" oculta durante fase de testes com usuários (reativável no código)

## Regras do Projeto

- PDFs **nunca** são copiados para este repositório
- Único vector store: pgvector (sem LangChain, FAISS, ChromaDB)
- Embedding model: voyage-3 exclusivamente
- Índice HNSW obrigatório
- Testes unitários nunca fazem chamadas externas (mocks obrigatórios)
- Anti-alucinação: 4 mecanismos (M1-M4) em toda resposta do LLM
