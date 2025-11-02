# Architecture Documentation

## System Overview

This document outlines the architecture of the Chatbot system with async initialization and service-oriented design.

---

## Component Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         FastAPI Application                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  Routers (src/routers/chatbot.py)                       │    │
│  │  - /api/chatbot/upload-document                         │    │
│  │  - /api/chatbot/chat                                    │    │
│  │  - /api/chatbot/memory/status                           │    │
│  └────────────────┬───────────────────────────────────────┘    │
│                   │                                             │
│                   │ Depends(get_chatbot)                        │
│                   │                                             │
│  ┌────────────────▼───────────────────────────────────────┐    │
│  │  Chatbot Instance (Singleton)                          │    │
│  │  - create_async() [async initialization]               │    │
│  │  - __init__() [sync initialization]                    │    │
│  └────────────────┬───────────────────────────────────────┘    │
│                   │                                             │
└───────────────────┼─────────────────────────────────────────────┘
                    │
    ┌───────────────┴───────────────┐
    │                               │
    ▼                               ▼
┌─────────────────────┐   ┌──────────────────────┐
│  setup_models()     │   │ load_documents_      │
│                     │   │ from_database()      │
│  - Gemini LLM       │   │                      │
│  - Embedding Model  │   │ - Query DB           │
│  - Vintern Service  │   │ - Load chunks        │
│  - Pipelines        │   │ - Build matrices     │
└──────┬──────────────┘   └──────┬───────────────┘
       │                         │
       │                         │
       └────────┬────────────────┘
                │
                │ Runs concurrently in async mode
                │
                ▼
    ┌───────────────────────────┐
    │  Initialized Chatbot      │
    │  Ready to serve requests  │
    └───────────────────────────┘
```

---

## Service Layer Architecture

### Vintern Embedding Service

```
┌──────────────────────────────────────────────────────────────┐
│                    Service Layer                             │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  IVinternEmbeddingService (Interface)              │    │
│  │  ┌──────────────────────────────────────────────┐  │    │
│  │  │  + is_enabled() -> bool                      │  │    │
│  │  │  + embed_texts(texts) -> List[Tensor]        │  │    │
│  │  │  + embed_images(images) -> List[Tensor]      │  │    │
│  │  │  + get_model_name() -> Optional[str]         │  │    │
│  │  │  + get_device() -> Optional[str]             │  │    │
│  │  └──────────────────────────────────────────────┘  │    │
│  └────────────────────┬───────────────────────────────┘    │
│                       │ implements                         │
│                       │                                    │
│  ┌────────────────────▼───────────────────────────────┐    │
│  │  VinternEmbeddingService (Implementation)          │    │
│  │  ┌──────────────────────────────────────────────┐  │    │
│  │  │ Private:                                     │  │    │
│  │  │  - _model: AutoModel                        │  │    │
│  │  │  - _processor: AutoProcessor                │  │    │
│  │  │  - _device: str (cuda/cpu)                  │  │    │
│  │  │  - _dtype: torch.dtype                      │  │    │
│  │  │  - _enabled: bool                           │  │    │
│  │  │                                              │  │    │
│  │  │ Public:                                      │  │    │
│  │  │  + embed_texts(texts)                       │  │    │
│  │  │  + embed_images(images)                     │  │    │
│  │  │  + process_query(query)                     │  │    │
│  │  │  + score_multi_vector(q_emb, doc_embs)      │  │    │
│  │  └──────────────────────────────────────────────┘  │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Ingestion Pipeline Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Ingestion Pipeline System                  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌───────────────────────────────────────────────┐    │
│  │  BaseIngestionPipeline (Abstract)             │    │
│  │  - process(file_path)                         │    │
│  │  - extract(file_path)                         │    │
│  │  - embed(content, file_path)    [abstract]    │    │
│  │  - store(content, vectors, ...)  [abstract]   │    │
│  └───────────────┬───────────────────────────────┘    │
│                  │ extends                            │
│         ┌────────┴────────┐                           │
│         │                 │                           │
│  ┌──────▼──────────┐  ┌──▼────────────────────┐      │
│  │ PdfIngestion    │  │ ImageIngestion        │      │
│  │ Pipeline        │  │ Pipeline              │      │
│  │                 │  │                       │      │
│  │ + embed()       │  │ + embed()             │      │
│  │ + store()       │  │ + store()             │      │
│  │                 │  │   - Uses Vintern      │      │
│  │ Dependencies:   │  │     Service           │      │
│  │ - Ingestion     │  │                       │      │
│  │   Service       │  │ Dependencies:         │      │
│  │                 │  │ - Ingestion Service   │      │
│  │                 │  │ - Vintern Service     │      │
│  └─────────────────┘  └───────────────────────┘      │
│                                                       │
└───────────────────────────────────────────────────────┘
```

---

## Data Flow

### Document Upload and Processing

```
1. Client Request
   │
   ├─> POST /api/chatbot/upload-document
   │   └─> Receive file upload
   │
2. Save to Temporary File
   │
3. Determine Pipeline
   │
   ├─> PDF?  → PdfIngestionPipeline
   └─> Image? → ImageIngestionPipeline
   │
4. Execute Pipeline
   │
   ├─> Extract Content
   │   └─> PDF: Extract text
   │   └─> Image: OCR with Gemini
   │
   ├─> Generate Embeddings
   │   ├─> Text: SentenceTransformer
   │   └─> Multimodal: Vintern (if enabled)
   │
   └─> Store in Database
       ├─> Create Document record
       ├─> Create DocumentChunk record(s)
       └─> Store embeddings (pgvector)
   │
5. Load into Memory
   │
   └─> Update in-memory caches
       ├─> documents list
       ├─> embeddings matrix
       └─> metadata list
   │
6. Return Success Response
```

### Query and Answer Generation

```
1. Client Query
   │
   ├─> POST /api/chatbot/chat
   │   └─> { query: "What is...?" }
   │
2. Search Relevant Documents
   │
   ├─> Text Search (SentenceTransformer)
   │   └─> Cosine similarity on embeddings
   │
   ├─> Multimodal Search (Vintern, if enabled)
   │   └─> Multi-vector scoring
   │
   └─> Combine and rank results
   │
3. Generate Answer
   │
   ├─> Prepare context from top results
   │
   ├─> Call Gemini LLM
   │   └─> With context and query
   │
   └─> Extract confidence score
   │
4. Return Response
   │
   └─> {
         answer: "...",
         confidence: 0.85,
         source_files: ["doc1.pdf", "image2.png"]
       }
```

---

## Initialization Sequence

### Synchronous Initialization (Legacy)

```
Time →
0s     2s     4s     6s     8s
│──────┼──────┼──────┼──────│
│                           │
├─> setup_models()          │
│   ├─> Gemini              │
│   ├─> SentenceTransformer │
│   ├─> Vintern             │
│   └─> Pipelines           │
│                           │
├─> load_documents_from_db()│
│   ├─> Query DB            │
│   ├─> Load chunks         │
│   └─> Build matrices      │
│                           │
└─> Ready ✓                 │
                            │
Total: ~8 seconds
```

### Asynchronous Initialization (New)

```
Time →
0s     2s     4s     6s
│──────┼──────┼──────│
│                    │
├─> setup_models()   │ (Thread 1)
│   ├─> Gemini       │
│   ├─> Sentence..   │
│   ├─> Vintern      │
│   └─> Pipelines    │
│                    │
├─> load_documents() │ (Thread 2)
│   ├─> Query DB     │
│   ├─> Load chunks  │
│   └─> Build        │
│       matrices     │
│                    │
└─────────────> Ready ✓
                    │
Total: ~5 seconds (max of both)
```

---

## Database Schema

```
┌─────────────────────────────────────────┐
│  documents                              │
├─────────────────────────────────────────┤
│  id                SERIAL PK             │
│  filename          VARCHAR              │
│  original_filename VARCHAR              │
│  file_type         VARCHAR              │
│  file_path         VARCHAR              │
│  file_size         INTEGER              │
│  processing_status VARCHAR              │
│  created_at        TIMESTAMP            │
│  updated_at        TIMESTAMP            │
└──────────┬──────────────────────────────┘
           │
           │ 1:N
           │
┌──────────▼──────────────────────────────┐
│  document_chunks                        │
├─────────────────────────────────────────┤
│  id                 SERIAL PK            │
│  document_id        INTEGER FK           │
│  chunk_index        INTEGER              │
│  heading            VARCHAR              │
│  content            TEXT                 │
│  embedding          VECTOR(384)          │
│  vintern_embedding  VECTOR(768)          │
│  embedding_model    VARCHAR              │
│  vintern_model      VARCHAR              │
│  metadata           JSONB                │
│  created_at         TIMESTAMP            │
└─────────────────────────────────────────┘
```

---

## Dependency Graph

```
┌──────────────────────────────────────────────────┐
│                  Chatbot                         │
├──────────────────────────────────────────────────┤
│  Depends on:                                     │
│  ├─> Gemini (google.generativeai)               │
│  ├─> SentenceTransformer                         │
│  ├─> VinternEmbeddingService                     │
│  ├─> IngestionService                            │
│  └─> Database Services                           │
│      ├─> document_service                        │
│      └─> document_chunk_service                  │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│         VinternEmbeddingService                  │
├──────────────────────────────────────────────────┤
│  Depends on:                                     │
│  ├─> transformers.AutoModel                      │
│  ├─> transformers.AutoProcessor                  │
│  └─> torch                                       │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│         ImageIngestionPipeline                   │
├──────────────────────────────────────────────────┤
│  Depends on:                                     │
│  ├─> IIngestionService                           │
│  ├─> IVinternEmbeddingService                    │
│  ├─> SentenceTransformer                         │
│  └─> Database Services                           │
└──────────────────────────────────────────────────┘
```

---

## Thread Safety

### Singleton Pattern with Async Lock

```python
# Global state
chatbot_instance: Optional[Chatbot] = None
chatbot_lock = asyncio.Lock()

# Thread-safe initialization
async def get_chatbot() -> Chatbot:
    async with chatbot_lock:
        if chatbot_instance is None:
            chatbot_instance = await Chatbot.create_async(api_key)
    return chatbot_instance
```

**Benefits:**
- Only one chatbot instance created
- No race conditions
- Safe for concurrent requests
- Efficient resource usage

---

## Error Handling

### Graceful Degradation

```
┌────────────────────────────────────┐
│  Initialize Components             │
├────────────────────────────────────┤
│                                    │
│  Gemini LLM                        │
│  ├─> Success ✓                     │
│  └─> Failure → Exception           │
│                                    │
│  SentenceTransformer               │
│  ├─> Success ✓                     │
│  └─> Failure → Exception           │
│                                    │
│  VinternEmbeddingService           │
│  ├─> Success ✓                     │
│  └─> Failure → Disabled (warning)  │  ← Graceful
│                                    │
│  Database Connection               │
│  ├─> Success ✓                     │
│  └─> Failure → Empty memory        │  ← Graceful
│                                    │
└────────────────────────────────────┘
```

**Philosophy:**
- Core components (LLM, embeddings) must succeed
- Optional components (Vintern) can fail gracefully
- Database errors don't prevent chatbot creation
- Clear logging of all failures

---

## Performance Optimizations

### 1. Concurrent Initialization
- Setup models and load documents in parallel
- Reduces total initialization time by ~30-40%

### 2. Vector Database
- pgvector extension for fast similarity search
- Indexed embeddings for O(log n) lookups

### 3. In-Memory Caching
- Documents and embeddings cached in RAM
- No disk I/O during query processing

### 4. Batch Processing
- Multiple texts/images embedded in single batch
- Reduces model inference overhead

---

## Security Considerations

### API Key Management
```
Environment Variable → .env file → os.getenv()
                                     │
                                     ├─> Never logged
                                     ├─> Never returned in responses
                                     └─> Used only for model initialization
```

### File Upload Validation
```
Client Upload → Validate extension → Save to temp file
                                        │
                                        ├─> Allowed: pdf, jpg, png, etc.
                                        ├─> Rejected: exe, sh, etc.
                                        └─> Auto-cleanup after processing
```

### Database Security
- Parameterized queries prevent SQL injection
- Connection pooling with limits
- Credentials from environment variables

---

## Monitoring and Logging

### Log Levels

```
DEBUG   - Detailed diagnostic information
INFO    - General informational messages
WARNING - Non-critical issues (Vintern disabled, etc.)
ERROR   - Serious issues requiring attention
```

### Key Metrics to Monitor

1. **Initialization Time**
   - Track async vs sync performance
   - Identify bottlenecks

2. **Query Latency**
   - Time to find relevant documents
   - Time to generate answer

3. **Database Performance**
   - Query execution time
   - Connection pool usage

4. **Model Performance**
   - Embedding generation time
   - LLM response time

---

## Future Architecture Improvements

### 1. Microservices Architecture
```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Ingestion  │  │   Embedding  │  │   Query      │
│   Service    │  │   Service    │  │   Service    │
└──────────────┘  └──────────────┘  └──────────────┘
```

### 2. Message Queue for Processing
```
Upload → Queue → Worker Pool → Database
                    │
                    └─> Process documents asynchronously
```

### 3. Distributed Caching
```
Redis/Memcached for shared embeddings cache
```

### 4. Horizontal Scaling
```
Load Balancer → Multiple Chatbot Instances → Shared Database
```

---

**Last Updated:** 2025-11-02
**Version:** 2.0.0
