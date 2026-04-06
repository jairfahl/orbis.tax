-- Migration: 0010_create_mau_records
-- Objetivo: tabela de metering MAU para billing por usuário ativo mensal

CREATE TABLE IF NOT EXISTS mau_records (
    user_id      UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tenant_id    UUID        NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    active_month DATE        NOT NULL,  -- sempre o primeiro dia do mês: 2026-04-01
    recorded_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, tenant_id, active_month)
);

CREATE INDEX IF NOT EXISTS idx_mau_tenant_month
    ON mau_records (tenant_id, active_month);

COMMENT ON TABLE mau_records IS
    'Registro de usuários ativos por mês por tenant. Um registro por (user, tenant, mês).
     Inserção via ON CONFLICT DO NOTHING garante idempotência.
     active_month sempre armazena o primeiro dia do mês (date_trunc month).';
