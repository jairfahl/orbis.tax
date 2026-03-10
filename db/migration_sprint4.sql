-- migration_sprint4.sql — Tabelas de Outputs Acionáveis
-- Executar: psql $DATABASE_URL -f db/migration_sprint4.sql

-- Enums
DO $$ BEGIN
    CREATE TYPE output_class AS ENUM (
        'alerta',
        'nota_trabalho',
        'recomendacao_formal',
        'dossie_decisao',
        'material_compartilhavel'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE output_status AS ENUM (
        'rascunho',
        'gerado',
        'aprovado',
        'publicado',
        'revogado'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE stakeholder_tipo AS ENUM (
        'cfo',
        'juridico',
        'compras',
        'auditoria',
        'diretoria',
        'externo'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Tabela principal de outputs
CREATE TABLE IF NOT EXISTS outputs (
    id              SERIAL PRIMARY KEY,
    case_id         INTEGER         NOT NULL REFERENCES cases(id),
    passo_origem    INTEGER         NOT NULL CHECK (passo_origem BETWEEN 1 AND 9),
    classe          output_class    NOT NULL,
    status          output_status   NOT NULL DEFAULT 'rascunho',
    titulo          VARCHAR(300)    NOT NULL,
    conteudo        JSONB           NOT NULL DEFAULT '{}',
    materialidade   INTEGER         CHECK (materialidade BETWEEN 1 AND 5),
    disclaimer      TEXT            NOT NULL,
    versao_prompt   VARCHAR(50),
    versao_base     VARCHAR(50),
    created_at      TIMESTAMPTZ     DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     DEFAULT NOW()
);

-- Decomposição por stakeholder
CREATE TABLE IF NOT EXISTS output_stakeholders (
    id              SERIAL PRIMARY KEY,
    output_id       INTEGER         NOT NULL REFERENCES outputs(id) ON DELETE CASCADE,
    stakeholder     stakeholder_tipo NOT NULL,
    resumo          TEXT            NOT NULL,
    campos_visiveis TEXT[]          NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ     DEFAULT NOW()
);

-- Aprovações
CREATE TABLE IF NOT EXISTS output_aprovacoes (
    id              SERIAL PRIMARY KEY,
    output_id       INTEGER         NOT NULL REFERENCES outputs(id) ON DELETE CASCADE,
    aprovado_por    VARCHAR(100)    NOT NULL,
    aprovado_em     TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    observacao      TEXT
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_outputs_case_id      ON outputs (case_id);
CREATE INDEX IF NOT EXISTS idx_outputs_classe       ON outputs (classe);
CREATE INDEX IF NOT EXISTS idx_outputs_materialidade ON outputs (materialidade DESC);
CREATE INDEX IF NOT EXISTS idx_output_stk_output_id ON output_stakeholders (output_id);
CREATE INDEX IF NOT EXISTS idx_output_apr_output_id ON output_aprovacoes (output_id);
