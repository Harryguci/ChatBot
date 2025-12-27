-- Migration script to convert embeddings from JSON to Vector type
-- Run this after pgvector extension is enabled

BEGIN;

-- Step 1: Add new vector columns
ALTER TABLE document_chunks 
ADD COLUMN IF NOT EXISTS embedding_vector vector(384);

ALTER TABLE document_chunks 
ADD COLUMN IF NOT EXISTS vintern_embedding_vector vector(768);

-- Step 2: Migrate data
UPDATE document_chunks
SET embedding_vector = 
    CASE 
        WHEN embedding IS NOT NULL THEN
            -- Convert JSON array to vector format
            ('[' || array_to_string(
                ARRAY(SELECT json_array_elements_text(embedding::json)), 
                ','
            ) || ']')::vector
        ELSE NULL
    END
WHERE embedding IS NOT NULL;

UPDATE document_chunks
SET vintern_embedding_vector = 
    CASE 
        WHEN vintern_embedding IS NOT NULL THEN
            ('[' || array_to_string(
                ARRAY(SELECT json_array_elements_text(vintern_embedding::json)), 
                ','
            ) || ']')::vector
        ELSE NULL
    END
WHERE vintern_embedding IS NOT NULL;

-- Step 3: Drop old columns and rename
ALTER TABLE document_chunks DROP COLUMN IF EXISTS embedding CASCADE;
ALTER TABLE document_chunks DROP COLUMN IF EXISTS vintern_embedding CASCADE;

ALTER TABLE document_chunks RENAME COLUMN embedding_vector TO embedding;
ALTER TABLE document_chunks RENAME COLUMN vintern_embedding_vector TO vintern_embedding;

-- Step 4: Create indexes
CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_cosine 
ON document_chunks USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

CREATE INDEX IF NOT EXISTS ix_document_chunks_vintern_embedding_cosine 
ON document_chunks USING ivfflat (vintern_embedding vector_cosine_ops)
WITH (lists = 100);

COMMIT;
