-- Migration 107: alertas de vigência em ai_interactions.
--
-- G08: Verificação de Vigência Legislativa (DC v7).
-- Registra alertas de vigência detectados na resposta da IA — normas revogadas
-- ou ainda não vigentes na data da análise (crítico no período de transição RT 2026-2033).
--
BEGIN;

ALTER TABLE ai_interactions
    ADD COLUMN IF NOT EXISTS alertas_vigencia  JSONB    DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS vigencia_ok       BOOLEAN  DEFAULT TRUE;

COMMENT ON COLUMN ai_interactions.alertas_vigencia IS
    'Lista de alertas de vigência legislativa detectados na resposta da IA (G08)';
COMMENT ON COLUMN ai_interactions.vigencia_ok IS
    'False se há algum alerta de vigência na análise (norma revogada ou não vigente)';

COMMIT;

-- Verificação pós-migration
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'ai_interactions' AND column_name = 'alertas_vigencia'
    ) THEN
        RAISE EXCEPTION 'Migration 107 falhou: coluna alertas_vigencia não encontrada.';
    END IF;
    RAISE NOTICE 'Migration 107 aplicada com sucesso.';
END;
$$;
