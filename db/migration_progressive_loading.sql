-- Progressive Loading: context budget log para observabilidade de prompts
ALTER TABLE ai_interactions
  ADD COLUMN IF NOT EXISTS context_budget_log TEXT;
