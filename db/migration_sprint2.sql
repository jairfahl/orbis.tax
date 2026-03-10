-- Sprint 2: tabela de log de interações cognitivas
CREATE TABLE IF NOT EXISTS ai_interactions (
    id              SERIAL PRIMARY KEY,
    query_texto     TEXT         NOT NULL,
    chunks_ids      INTEGER[],
    qualidade_status VARCHAR(10),
    scoring_confianca VARCHAR(10),
    grau_consolidacao VARCHAR(20),
    m1_existencia   BOOLEAN,
    m2_validade     BOOLEAN,
    m3_pertinencia  BOOLEAN,
    m4_consistencia BOOLEAN,
    bloqueado       BOOLEAN,
    prompt_version  VARCHAR(50),
    model_id        VARCHAR(100),
    latencia_ms     INTEGER,
    created_at      TIMESTAMPTZ  DEFAULT NOW()
);
