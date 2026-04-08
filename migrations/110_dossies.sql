-- Migration 110: adiciona legal_hold e imutavel à tabela outputs (G13).
--
-- C1 — Taxonomia de Saídas + Dossiê de Decisão Automático.
-- legal_hold: True quando o documento deve ser preservado para auditoria.
-- imutavel:   True quando o documento não pode ser alterado após criação.
--
BEGIN;

ALTER TABLE outputs
    ADD COLUMN IF NOT EXISTS legal_hold BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS imutavel   BOOLEAN NOT NULL DEFAULT FALSE;

-- Marcar documentos existentes de classes imutáveis
UPDATE outputs
SET legal_hold = TRUE, imutavel = TRUE
WHERE classe IN ('dossie_decisao', 'material_compartilhavel');

UPDATE outputs
SET legal_hold = TRUE
WHERE classe = 'recomendacao_formal'
  AND status = 'aprovado';

-- Constraint: dossiê e material compartilhável nunca com imutavel=FALSE
ALTER TABLE outputs
    DROP CONSTRAINT IF EXISTS chk_output_imutavel;

ALTER TABLE outputs
    ADD CONSTRAINT chk_output_imutavel
    CHECK (
        classe NOT IN ('dossie_decisao', 'material_compartilhavel')
        OR imutavel = TRUE
    );

-- Adicionar user_id se não existir (para listar_dossies_usuario)
ALTER TABLE outputs
    ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id) ON DELETE SET NULL;

COMMIT;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'outputs' AND column_name = 'legal_hold'
    ) THEN
        RAISE EXCEPTION 'Migration 110 falhou: coluna legal_hold não encontrada.';
    END IF;
    RAISE NOTICE 'Migration 110 aplicada com sucesso.';
END;
$$;
