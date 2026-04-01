-- Migration: 029_lockfile_table.sql
-- Prompt Integrity Lockfile (RDM-029)

CREATE TABLE IF NOT EXISTS prompt_lockfiles (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lockfile_hash    CHAR(64)      NOT NULL,
    taxmind_version  VARCHAR(20)   NOT NULL,
    prompt_ids       TEXT[]        NOT NULL,
    lockfile_json    JSONB         NOT NULL,
    gate_origem      VARCHAR(50),
    criado_em        TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    criado_por       VARCHAR(100)  NOT NULL,
    ativo            BOOLEAN       NOT NULL DEFAULT TRUE
);

-- Apenas um lockfile ativo por vez
CREATE UNIQUE INDEX IF NOT EXISTS idx_lockfile_ativo
    ON prompt_lockfiles (ativo)
    WHERE ativo = TRUE;

-- Referência em ai_interactions
ALTER TABLE ai_interactions
    ADD COLUMN IF NOT EXISTS lockfile_id UUID REFERENCES prompt_lockfiles(id);
