-- Enable pgvector extension on database creation
-- This script runs automatically when the database is first initialized

CREATE EXTENSION IF NOT EXISTS vector;
