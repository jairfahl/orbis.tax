# TaxMind Light

Sistema de análise tributária com RAG e protocolo de decisão para a Reforma Tributária brasileira (EC 132/2023, LC 214/2025, LC 227/2026).

## O que é o TaxMind Light?

O TaxMind Light é uma ferramenta de suporte à decisão tributária composta por dois modos de uso:

- **Consulta rápida** — perguntas pontuais sobre a Reforma Tributária, respondidas com fundamentação legal via RAG
- **Protocolo P1→P9** — processo estruturado de 9 passos para análise, recomendação e decisão sobre cenários tributários complexos

## Funcionalidades

| Aba | Função |
|-----|--------|
| **Consultar** | Consulta rápida à base de conhecimento com indicadores de qualidade, fundamentação legal e ação recomendada |
| **Adicionar Norma** | Upload de PDFs (INs, Resoluções, Pareceres), detecção de duplicidade por hash MD5, ingestão assíncrona, listagem e exclusão de documentos |
| **Protocolo P1→P9** | Protocolo de decisão tributária: identificação do problema → análise → recomendação TaxMind → decisão → acompanhamento → aprendizado |
| **Documentos** | Geração de documentos a partir dos casos (Consulta, Parecer, Relatório, Memorando, Comparativo) |
| **Qualidade do Sistema** | Métricas de observabilidade, detecção de drift, regression testing |

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
- **api** — FastAPI/uvicorn (porta 8000)
- **ui** — Streamlit (porta 8501)

Acesse `http://localhost:8501` no navegador.

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
│   │   ├── engine.py            # Máquina de estados P1→P9
│   │   └── carimbo.py           # Detector de terceirização cognitiva
│   ├── quality/
│   │   └── engine.py            # DataQualityEngine (BL-01, BL-02, BL-03)
│   └── rag/
│       ├── retriever.py         # Retrieval híbrido (vetorial + BM25)
│       └── spd.py               # SPD-RAG multi-norma
├── ui/
│   └── app.py                   # Streamlit (5 abas)
└── tests/
    └── unit/                    # Testes unitários (137+)
```

## Protocolo P1→P9

| Passo | Nome | Responsável |
|-------|------|-------------|
| P1 | Identificar o problema | Usuário |
| P2 | Mapear o cenário da empresa | Usuário |
| P3 | Avaliar riscos e dados | Usuário |
| P4 | Análise tributária | TaxMind (RAG + LLM) |
| P5 | Posição do gestor | Usuário |
| P6 | Recomendação TaxMind | TaxMind (auto-populado da análise P4) |
| P7 | Decisão e responsável | Usuário |
| P8 | Acompanhamento | Usuário |
| P9 | Registro de aprendizado | Usuário |

## API — Principais Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/v1/health` | Status do sistema |
| POST | `/v1/analyze` | Consulta RAG + LLM |
| GET | `/v1/chunks` | Busca de chunks |
| POST | `/v1/ingest/upload` | Upload assíncrono de PDF |
| POST | `/v1/ingest/check-duplicate` | Verificação de duplicidade |
| GET | `/v1/ingest/jobs/{job_id}` | Polling de ingestão |
| GET | `/v1/ingest/normas` | Listar documentos na base |
| DELETE | `/v1/ingest/normas/{norma_id}` | Remover documento da base |
| POST | `/v1/protocol/cases` | Criar caso |
| POST | `/v1/protocol/cases/{id}/steps` | Submeter passo |
| GET | `/v1/protocol/cases/{id}` | Detalhes do caso |
| POST | `/v1/documents/generate` | Gerar documento |
| GET | `/v1/observability/metrics` | Métricas de uso |
| GET | `/v1/observability/drift` | Detecção de drift |

## Regras do Projeto

- PDFs **nunca** são copiados para este repositório
- Único vector store: pgvector (sem LangChain, FAISS, ChromaDB)
- Embedding model: voyage-3 exclusivamente
- Índice HNSW obrigatório
- Testes unitários nunca fazem chamadas externas (mocks obrigatórios)
- Anti-alucinação: 4 mecanismos (M1-M4) em toda resposta do LLM
