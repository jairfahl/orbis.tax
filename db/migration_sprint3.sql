-- migration_sprint3.sql — Tabelas do Protocolo P1→P9 e Detector de Carimbo
-- Executar manualmente: psql $DATABASE_URL -f db/migration_sprint3.sql

-- Enum de status
DO $$ BEGIN
    CREATE TYPE case_status AS ENUM (
        'rascunho',
        'em_analise',
        'aguardando_hipotese',
        'decidido',
        'em_monitoramento',
        'aprendizado_extraido'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Casos protocolares
CREATE TABLE IF NOT EXISTS cases (
    id          SERIAL PRIMARY KEY,
    titulo      VARCHAR(500) NOT NULL,
    descricao   TEXT,
    status      case_status  NOT NULL DEFAULT 'rascunho',
    passo_atual INTEGER      NOT NULL DEFAULT 1,
    created_at  TIMESTAMPTZ  DEFAULT NOW(),
    updated_at  TIMESTAMPTZ  DEFAULT NOW()
);

-- Passos do protocolo
CREATE TABLE IF NOT EXISTS case_steps (
    id         SERIAL PRIMARY KEY,
    case_id    INTEGER      NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    passo      INTEGER      NOT NULL CHECK (passo BETWEEN 1 AND 9),
    dados      JSONB        NOT NULL DEFAULT '{}',
    concluido  BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ  DEFAULT NOW(),
    updated_at TIMESTAMPTZ  DEFAULT NOW(),
    UNIQUE (case_id, passo)
);

-- Histórico de transições de estado
CREATE TABLE IF NOT EXISTS case_state_history (
    id          SERIAL PRIMARY KEY,
    case_id     INTEGER      NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    status_de   case_status,
    status_para case_status  NOT NULL,
    passo_de    INTEGER,
    passo_para  INTEGER      NOT NULL,
    motivo      TEXT,
    created_at  TIMESTAMPTZ  DEFAULT NOW()
);

-- Alertas de carimbo (terceirização cognitiva)
CREATE TABLE IF NOT EXISTS carimbo_alerts (
    id                  SERIAL PRIMARY KEY,
    case_id             INTEGER      NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    passo               INTEGER      NOT NULL,
    score_similaridade  FLOAT        NOT NULL,
    texto_decisao       TEXT         NOT NULL,
    texto_recomendacao  TEXT         NOT NULL,
    confirmado          BOOLEAN      NOT NULL DEFAULT FALSE,
    justificativa       TEXT,
    created_at          TIMESTAMPTZ  DEFAULT NOW()
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_case_steps_case_id     ON case_steps (case_id);
CREATE INDEX IF NOT EXISTS idx_case_history_case_id   ON case_state_history (case_id);
CREATE INDEX IF NOT EXISTS idx_carimbo_alerts_case_id ON carimbo_alerts (case_id);
