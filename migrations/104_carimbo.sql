-- Migration 104: campos de carimbo em ai_interactions.
--
-- G05: Detector de Carimbo — Anti-Terceirização Cognitiva (DC v7).
-- Registra o resultado da verificação de similaridade entre decisão do gestor
-- e recomendação da IA. Complementa a tabela carimbo_alerts (que armazena
-- alertas por caso/passo) com visão agregada em ai_interactions (por análise).
--
-- Notas:
--   - Os campos ficam NULL por padrão e são populados pelo detector.
--   - carimbo_confirmado é atualizado quando o gestor confirma conscientemente.
--   - Compatível com o sistema Voyage-based existente em src/protocol/carimbo.py.
--
BEGIN;

ALTER TABLE ai_interactions
    ADD COLUMN IF NOT EXISTS carimbo_similaridade  NUMERIC(5,4) DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS carimbo_detectado      BOOLEAN      DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS carimbo_confirmado     BOOLEAN      DEFAULT NULL;

COMMENT ON COLUMN ai_interactions.carimbo_similaridade IS
    'Similaridade léxica ou semântica entre decisão do gestor e recomendação da IA (0.0 a 1.0)';
COMMENT ON COLUMN ai_interactions.carimbo_detectado IS
    'True se similaridade >= 0.70 (threshold do Detector de Carimbo)';
COMMENT ON COLUMN ai_interactions.carimbo_confirmado IS
    'True se gestor confirmou decisão após alerta do detector';

COMMIT;

-- Verificação pós-migration
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'ai_interactions' AND column_name = 'carimbo_similaridade'
    ) THEN
        RAISE EXCEPTION 'Migration 104 falhou: coluna carimbo_similaridade não encontrada.';
    END IF;
    RAISE NOTICE 'Migration 104 aplicada com sucesso.';
END;
$$;
