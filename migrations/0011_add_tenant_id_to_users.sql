-- Migration: 0011_add_tenant_id_to_users
-- Objetivo: associar cada usuário a um tenant para billing MAU
-- Depende de: 0009_create_tenants.sql

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS tenant_id UUID REFERENCES tenants(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_users_tenant_id ON users (tenant_id);

COMMENT ON COLUMN users.tenant_id IS
    'Tenant ao qual o usuário pertence. NULL = usuário sem tenant (ex: admin global).';
