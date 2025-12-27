# PostgreSQL pgvector Integration Guide

## Overview

This document describes the migration from storing embeddings as JSON to using PostgreSQL's pgvector extension for efficient vector similarity search.

## Changes Made

### 1. Database Models (`src/config/db/models.py`)

- **Removed** `content_hash` column from `Document` model
- **Updated** `DocumentChunk` model to use `Vector` type for embeddings:
  - `embedding` column: `Vector(384)` for sentence-transformers embeddings
  - `vintern_embedding` column: `Vector(768)` for Vintern multimodal embeddings
- **Added** vector indexes for cosine similarity search:
  - `ix_document_chunks_embedding_cosine`
  - `ix_document_chunks_vintern_embedding_cosine`

### 2. Database Services (`src/config/db/services.py`)

- **Updated** `DocumentService.create_document()` to remove `content_hash` parameter
- **Added** `DocumentService.check_document_exists_by_filename()` to replace hash-based lookup
- **Added** `DocumentChunkService.find_similar_chunks_by_embedding()` for vector similarity search
- **Added** `DocumentChunkService.find_similar_chunks_by_vintern_embedding()` for Vintern vector search

### 3. Chatbot Memory (`src/chatbot_memory.py`)

- **Removed** content hash calculation using `hashlib.sha256()`
- **Replaced** hash-based duplicate detection with filename-based checking
- **Added** `vector_to_numpy()` helper function to convert Vector types to numpy arrays
- **Updated** all embedding access to use `vector_to_numpy()` conversion
- **Updated** Vintern embedding loading to handle Vector types

### 4. Database Initialization (`src/migrations/20251026_2340_initalization.py`)

- **Added** pgvector extension installation to initialization process
- **Updated** critical indexes list to include vector indexes

### 5. Requirements (`requirements.txt`)

- **Added** `pgvector>=0.3.1` dependency

## Installation Steps

### 1. Install pgvector Extension in PostgreSQL

```bash
# Connect to PostgreSQL
psql -U postgres -d chatbot_db

# Enable the extension
CREATE EXTENSION IF NOT EXISTS vector;
```

### 2. Run Database Migration

```bash
# Activate virtual environment
.venv/Scripts/activate

# Run the pgvector migration
python src/migrations/20251026_2327_update_to_pgvector.py
```

### 3. Verify Installation

```bash
# Check if extension is installed
python src/migrations/20251026_2340_initalization.py verify
```

## Vector Similarity Search

### Basic Query

```python
from src.config.db.services import document_chunk_service

# Find similar chunks
chunks_with_scores = document_chunk_service.find_similar_chunks_by_embedding(
    query_embedding=query_vector,
    limit=5,
    threshold=0.7
)

for chunk, similarity in chunks_with_scores:
    print(f"Similarity: {similarity:.3f}")
    print(f"Content: {chunk.content[:100]}...")
```

### Using in Search

The new vector search uses PostgreSQL's cosine distance operator (`<=>`):

```sql
SELECT * FROM document_chunks
ORDER BY embedding <=> CAST('[0.1, 0.2, ...]' AS vector)
LIMIT 5;
```

## Benefits

1. **Performance**: Vector indexes (IVFFlat/HNSW) provide faster similarity search
2. **Scalability**: Efficient for large databases with millions of vectors
3. **Native Integration**: Leverages PostgreSQL's built-in capabilities
4. **Flexibility**: Easy to switch between distance metrics (cosine, L2, inner product)

## Dimension Specifications

- **Text Embeddings**: 384 dimensions (sentence-transformers/all-MiniLM-L12-v2)
- **Vintern Embeddings**: 768 dimensions (Vintern multimodal model)

## Migration Notes

- Existing embeddings stored as JSON will need to be migrated
- The migration script handles this automatically
- No data loss - all embeddings are preserved during migration

## Index Types

The current implementation uses **IVFFlat** indexes:

```sql
CREATE INDEX ix_document_chunks_embedding_cosine
ON document_chunks USING ivfflat (embedding vector_cosine_ops);
```

For better performance with very large datasets (>100K vectors), consider using HNSW:

```sql
CREATE INDEX ix_document_chunks_embedding_cosine
ON document_chunks USING hnsw (embedding vector_cosine_ops);
```

## Testing Vector Search

```python
import numpy as np
from src.config.db.services import document_chunk_service

# Create a test query embedding
query_embedding = np.random.rand(384).tolist()

# Find similar chunks
results = document_chunk_service.find_similar_chunks_by_embedding(
    query_embedding=query_embedding,
    limit=5,
    threshold=0.5
)

print(f"Found {len(results)} similar chunks")
```

## Troubleshooting

### Issue: "Extension 'vector' does not exist"

**Solution**: Install pgvector on your PostgreSQL server:

```bash
# On Ubuntu/Debian
sudo apt-get install postgresql-15-pgvector

# On macOS
brew install pgvector

# Then enable in database
CREATE EXTENSION vector;
```

### Issue: "Cannot import pgvector"

**Solution**: Install the Python package:

```bash
pip install pgvector
```

### Issue: Dimension mismatch errors

**Solution**: Ensure your embedding dimensions match the Vector column definition:

- Text embeddings: 384 dimensions
- Vintern embeddings: 768 dimensions

## References

- [pgvector GitHub](https://github.com/pgvector/pgvector)
- [pgvector Documentation](https://github.com/pgvector/pgvector#documentation)
- [SQLAlchemy pgvector](https://github.com/pgvector/pgvector-python)
