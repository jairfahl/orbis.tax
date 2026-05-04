-- Migration 135: contador de consultas /analisar para tenants em trial
-- Limite: 5 consultas durante o período de trial
ALTER TABLE tenants
  ADD COLUMN IF NOT EXISTS consultas_trial_usadas INT NOT NULL DEFAULT 0;
