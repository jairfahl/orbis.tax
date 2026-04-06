-- Migration: 0009_create_tenants
-- Objetivo: tabela de tenants para modelo SaaS multi-tenant com billing MAU
-- Criado em: Abril 2026

BEGIN;

CREATE TABLE IF NOT EXISTS tenants (
    id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    nome          VARCHAR(255) NOT NULL,
    slug          VARCHAR(100) UNIQUE NOT NULL,     -- identificador URL-safe (ex: "escritorio-fahl")
    plano         VARCHAR(20)  NOT NULL DEFAULT 'TRIAL'
                      CHECK (plano IN ('TRIAL', 'STARTER', 'PRO', 'ENTERPRISE')),
    ativo         BOOLEAN      NOT NULL DEFAULT TRUE,
    criado_em     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tenants_slug  ON tenants (slug);
CREATE INDEX IF NOT EXISTS idx_tenants_ativo ON tenants (ativo);
CREATE INDEX IF NOT EXISTS idx_tenants_plano ON tenants (plano);

-- Adicionar tenant_id na tabela users (FK nullable — compatível com users já existentes)
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS tenant_id UUID REFERENCES tenants(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_users_tenant_id ON users (tenant_id);

COMMENT ON TABLE tenants IS
    'Tenants do modelo SaaS. Um tenant = uma organização cliente.
     Billing calculado via mau_records (MAU por tenant por mês).';

COMMIT;
