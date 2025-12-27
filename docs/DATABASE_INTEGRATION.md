# Database Integration for PDFChatbot

## Overview

The PDFChatbot has been updated to use PostgreSQL database for persistent storage of documents, chunks, and embeddings. This replaces the in-memory storage approach and provides:

- **Scalability**: Handle large datasets without memory limitations
- **Persistence**: Data persists across application restarts
- **Deduplication**: Content hashing prevents duplicate documents
- **Efficiency**: Only loads active chunks into memory for search

## Changes Made

### 1. Database Models (`src/config/db/models.py`)

Added new fields to `DocumentChunk` model:
- `vintern_embedding`: JSON field to store Vintern multimodal embeddings
- `vintern_model`: Model version string for Vintern embeddings

### 2. Database Services (`src/config/db/services.py`)

New methods added to `DocumentChunkService`:
- `get_all_chunks_with_embeddings()`: Load all chunks with embeddings
- `get_all_chunks_with_vintern_embeddings()`: Load chunks with Vintern embeddings
- `update_chunk_embedding()`: Update standard embeddings
- `update_chunk_vintern_embedding()`: Update Vintern embeddings

### 3. PDFChatbot Updates (`src/chatbot_memory.py`)

#### New Imports
- Database services and models
- Hashlib for content hashing

#### New Methods
- `vintern_embed_texts()`: Create Vintern embeddings for text
- `vintern_embed_images()`: Create Vintern embeddings for images

#### Updated `process_document()` Method

The document processing now:
1. **Calculates content hash** to check for duplicates
2. **Checks database** for existing documents with same hash
3. **Loads from database** if document exists
4. **Creates new document record** if not exists
5. **Saves chunks with embeddings** to database
6. **Maintains in-memory cache** for fast search

## Database Schema

### Document Table
- Stores document metadata
- Tracks processing status
- Content hash for deduplication

### DocumentChunk Table
- Stores text chunks with headings
- Standard embeddings (JSON array)
- Vintern multimodal embeddings (JSON array)
- Chunk metadata

## Usage

### Initial Setup

1. **Ensure database is running**:
```bash
docker-compose up -d postgres
```

2. **Run migration** (if needed):
```bash
python src/migrations/20251026_2229_add_vintern_fields.py
```

3. **Start the application**:
```bash
python src/main.py
```

### Processing Documents

When you process a document:

1. **First time**: Document is processed, chunks and embeddings saved to database
2. **Subsequent times**: Document is loaded from database if content hash matches

The system maintains an in-memory cache of active chunks for fast similarity search.

### Benefits

1. **Memory Optimization**: Only active chunks loaded in RAM
2. **Fast Retrieval**: Cached embeddings for instant search
3. **Deduplication**: No duplicate documents processed
4. **Persistence**: Data survives application restarts
5. **Scalability**: Can handle thousands of documents

## Migration Guide

### From In-Memory to Database-Backed

If you have existing in-memory chatbot:

1. Documents in memory will be lost on restart
2. New documents will be automatically saved to database
3. Re-process documents to populate database
4. Future sessions will load from database

### Running Migrations

```bash
# Add Vintern fields
python src/migrations/20251026_2229_add_vintern_fields.py
```

## Performance Considerations

1. **Initial Load**: First document processing may be slower
2. **Subsequent Loads**: Documents load instantly from database
3. **Memory Usage**: Only active session data in RAM
4. **Database Size**: Embeddings stored as JSON (consider PostgreSQL vector extension for better performance)

## Future Enhancements

1. **PostgreSQL pgvector Extension**: Use native vector type for better performance
2. **Vector Indexing**: Add GIN/GiST indexes for faster similarity search
3. **Batch Operations**: Optimize bulk document processing
4. **Embedding Caching**: Global embedding cache for common chunks

## Troubleshooting

### Database Connection Issues

Check `.env` file has correct database credentials:
```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=chatbot_db
DB_USER=postgres
DB_PASSWORD=postgres
```

### Migration Errors

If migration fails:
```bash
# Drop and recreate tables
python src/config/db/db_init.py
```

### Memory Issues

If still seeing memory issues:
1. Reduce batch size in chunking
2. Implement lazy loading of embeddings
3. Use database-only search (remove in-memory cache)
