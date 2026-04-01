-- Migration: 024_multi_query_fields.sql
-- Multi-Query Retrieval (RDM-024)
ALTER TABLE ai_interactions
  ADD COLUMN IF NOT EXISTS multi_query_activated    BOOLEAN  DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS query_variations_count   SMALLINT DEFAULT 0;
