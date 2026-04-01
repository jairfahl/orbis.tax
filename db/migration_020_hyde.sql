-- Migration: 020_hyde_field.sql
-- HyDE: Hypothetical Document Embeddings (RDM-020)
ALTER TABLE ai_interactions
  ADD COLUMN IF NOT EXISTS hyde_activated BOOLEAN DEFAULT FALSE;
