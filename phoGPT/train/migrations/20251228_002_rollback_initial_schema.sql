-- Migration Rollback: Initial schema for training management
-- Created: 2025-12-28
-- Description: Rolls back the initial schema migration (drops tables)

-- WARNING: This will delete all training data!

-- Drop tables in reverse order (child tables first)
DROP TABLE IF EXISTS training_metrics CASCADE;
DROP TABLE IF EXISTS training_runs CASCADE;

-- Drop indexes (if tables are dropped, indexes are automatically dropped)
-- This is just for documentation purposes

COMMENT ON DATABASE chatbot_ocr_db IS 'Training schema rollback completed';
