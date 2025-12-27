# Architecture Documentation

## System Overview

This document outlines the architecture of the Chatbot system - a **database-first RAG (Retrieval-Augmented Generation)** implementation with async initialization, service-oriented design, and multimodal capabilities.

### Quick Reference: End-to-End Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     DOCUMENT INGESTION                          │
└─────────────────────────────────────────────────────────────────┘
                              │
    User uploads PDF/Image ───┘
                              │
                              ▼
    ┌─────────────────────────────────────┐
    │  Extract Content                    │
    │  • PDF: pypdf text extraction       │
    │  • Image: Gemini Vision OCR         │
    └─────────────┬───────────────────────┘
                  │
                  ▼
    ┌─────────────────────────────────────┐
    │  Generate Dual Embeddings           │
    │  • Text: 384-dim (SentenceTransf.)  │
    │  • Vintern: 768-dim (Multimodal)    │
    └─────────────┬───────────────────────┘
                  │
                  ▼
    ┌─────────────────────────────────────┐
    │  Store in PostgreSQL (pgvector)     │
    │  • documents table                  │
    │  • document_chunks table            │
    │  • VECTOR columns for embeddings    │
    └─────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                     QUERY & RETRIEVAL                           │
└─────────────────────────────────────────────────────────────────┘
                              │
    User asks question ────────┘
                              │
                              ▼
    ┌─────────────────────────────────────┐
    │  Embed Query                        │
    │  • Generate 384-dim embedding       │
    │  • Generate 768-dim Vintern (opt)   │
    └─────────────┬───────────────────────┘
                  │
                  ▼
    ┌─────────────────────────────────────┐
    │  Database Vector Search             │
    │  • Cosine similarity on embeddings  │
    │  • Recency boost (15% for new docs) │
    │  • Top 5 most relevant chunks       │
    └─────────────┬───────────────────────┘
                  │
                  ▼
    ┌─────────────────────────────────────┐
    │  Fallback: Keyword Search (if weak) │
    │  • PostgreSQL ILIKE on content      │
    └─────────────┬───────────────────────┘
                  │
                  ▼
    ┌─────────────────────────────────────┐
    │  Generate Answer (Gemini 2.0 Flash) │
    │  • Context: Top 5 chunks            │
    │  • Grounded response with sources   │
    │  • Confidence score                 │
    └─────────────┬───────────────────────┘
                  │
                  ▼
    Return: Answer + Source Files + Confidence
```

### Core Architecture Principles

1. **Database-First RAG**: All embeddings stored in PostgreSQL with pgvector - no in-memory embedding matrices
2. **Recency-Weighted Retrieval**: More recent documents receive boosted similarity scores
3. **Multimodal Embeddings**: Dual embedding strategy (SentenceTransformer + Vintern) for text and images
4. **Hybrid Search**: Vector similarity with keyword-based fallback for robustness
5. **Async Initialization**: Concurrent model setup and document loading for faster startup

### Technology Stack

| Layer                       | Technology                | Version                    | Purpose                                |
| --------------------------- | ------------------------- | -------------------------- | -------------------------------------- |
| **Backend**                 | FastAPI                   | ≥0.115.0                   | REST API server with async support     |
| **Database**                | PostgreSQL + pgvector     | pg15 + ≥0.3.1              | Vector storage and similarity search   |
| **Embeddings (Text)**       | SentenceTransformer       | ≥2.2.2                     | Multilingual semantic search (384-dim) |
| **Embeddings (Multimodal)** | Vintern                   | transformers 4.48.0        | Text + Image understanding (768-dim)   |
| **LLM**                     | Gemini 2.0 Flash Lite     | google-generativeai ≥0.7.0 | Fast, cost-effective answer generation |
| **OCR**                     | Gemini Vision API         | -                          | Image text extraction                  |
| **Frontend**                | React + Ant Design + Vite | -                          | User interface with modern build tools |
| **PDF Processing**          | PyMuPDF (fitz)            | ≥1.23.0                    | High-speed PDF text extraction         |
| **Image Processing**        | Pillow                    | ≥10.0.0                    | Image manipulation and processing      |
| **Vector Math**             | PyTorch                   | ≥2.0.0                     | Deep learning framework for embeddings |

---

## RAG (Retrieval-Augmented Generation) Architecture

### Overview

The system implements a **database-first RAG pipeline** where all embeddings are stored and queried directly from PostgreSQL using the pgvector extension. This eliminates memory constraints and enables efficient similarity search at scale.

### RAG Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    RAG Pipeline (Query → Answer)                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. User Query                                                  │
│     │                                                            │
│     ├─> "What is the main topic of document X?"               │
│     │                                                            │
│  2. Dual Embedding Generation                                  │
│     │                                                            │
│     ├─> SentenceTransformer (384-dim)                          │
│     │   └─> Text embedding for semantic search                 │
│     │                                                            │
│     ├─> Vintern (768-dim) [Optional]                           │
│     │   └─> Multimodal embedding (text + image capable)        │
│     │                                                            │
│  3. Database Vector Search (Recency-Weighted)                  │
│     │                                                            │
│     ├─> search_relevant_documents()                            │
│     │   └─> SELECT * FROM document_chunks                      │
│     │       ORDER BY (cosine_similarity * (1 + recency_boost)) │
│     │       LIMIT top_k                                         │
│     │                                                            │
│     ├─> search_relevant_documents_vintern()                    │
│     │   └─> Similar query on vintern_embedding column          │
│     │                                                            │
│  4. Result Fusion & Ranking                                     │
│     │                                                            │
│     ├─> Combine results from both search methods               │
│     ├─> Sort by similarity score (descending)                  │
│     └─> Filter by minimum threshold (0.1)                      │
│     │                                                            │
│  5. Fallback: Keyword Search (if vector search fails)          │
│     │                                                            │
│     └─> search_chunks_by_content(query)                        │
│         └─> PostgreSQL LIKE/ILIKE query on content             │
│     │                                                            │
│  6. Context Preparation                                         │
│     │                                                            │
│     ├─> Select top 5 most relevant chunks                      │
│     ├─> Format with metadata (source file, score)              │
│     └─> Build context string for LLM                           │
│     │                                                            │
│  7. LLM Answer Generation                                       │
│     │                                                            │
│     ├─> Gemini 2.0 Flash Lite (gemini-2.0-flash-lite)         │
│     ├─> Prompt: Context + Query + Instructions                 │
│     └─> Generate grounded answer with citations                │
│     │                                                            │
│  8. Response with Metadata                                      │
│     │                                                            │
│     └─> {                                                       │
│           answer: "...",                                        │
│           confidence: 0.85,                                     │
│           source_files: ["doc1.pdf", "image2.png"]             │
│         }                                                        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Key RAG Features

#### 1. Recency-Weighted Similarity Search

```python
# From chatbot_memory.py:416-438
def search_relevant_documents(query, top_k=5, recency_weight=0.15):
    """
    Similarity score boosted by document recency:

    final_score = cosine_similarity + (recency_weight * recency_factor)

    where recency_factor decreases exponentially with document age
    """
```

**Benefits:**

- More recent documents ranked higher
- Configurable boost weight (default: 15%)
- Prevents stale information dominance

#### 2. Dual Embedding Strategy

| Embedding Type           | Model                                   | Dimensions | Use Case                                          |
| ------------------------ | --------------------------------------- | ---------- | ------------------------------------------------- |
| **Text (Primary)**       | `paraphrase-multilingual-MiniLM-L12-v2` | 384        | General semantic search, multilingual support     |
| **Multimodal (Vintern)** | `5CD-AI/Vintern-Embedding-1B`           | 768        | Text + Image search, visual content understanding |

**Search Priority:**

1. Vintern search (if enabled and model loaded)
2. Text embedding search (always available)
3. Keyword fallback (if vector scores < 0.1)

#### 3. Hybrid Search with Fallback

```
Vector Search Success (score ≥ 0.1)
    │
    ├─> Use vector results
    │
Vector Search Weak (score < 0.1)
    │
    ├─> Fall back to keyword search
    │   └─> document_chunk_service.search_chunks_by_content(query)
    │
No Results
    │
    └─> Return "No relevant information found"
```

**Threshold Logic:**

- `min_threshold = 0.1` (deliberately low to be permissive)
- Keyword search assigns score of `0.15` to matches
- Ensures system can always attempt to answer

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
   │   └─> Receive file upload (PDF or Image)
   │
2. Save to Temporary File
   │
   ├─> Validate file extension
   └─> Save with original filename for tracking
   │
3. Check for Existing Document
   │
   ├─> Query: document_service.check_document_exists_by_filename()
   │
   ├─> If exists with chunks:
   │   └─> Register in processed_files tracker → Done
   │
   └─> If not exists or no chunks:
       └─> Continue to processing
   │
4. Select Ingestion Pipeline
   │
   ├─> PDF (.pdf)?  → PdfIngestionPipeline
   └─> Image (.jpg, .png, etc.)? → ImageIngestionPipeline
   │
5. Execute Pipeline: Extract → Embed → Store
   │
   ├─> EXTRACT Content
   │   ├─> PDF: pypdf.PdfReader (text extraction)
   │   └─> Image: Gemini Vision API (OCR + description)
   │
   ├─> EMBED Content (Dual Strategy)
   │   │
   │   ├─> Primary: SentenceTransformer (384-dim)
   │   │   └─> Generate text embedding
   │   │
   │   └─> Optional: Vintern (768-dim)
   │       ├─> Text: vintern_service.embed_texts()
   │       └─> Image: vintern_service.embed_images()
   │
   └─> STORE in Database
       │
       ├─> Create Document record
       │   └─> documents table (filename, file_type, status)
       │
       ├─> Create DocumentChunk record
       │   ├─> document_chunks table
       │   ├─> Store content (full text)
       │   ├─> Store embedding (VECTOR(384))
       │   └─> Store vintern_embedding (VECTOR(768)) [if available]
       │
       └─> Database handles vector indexing automatically
   │
6. Register in Tracker (No In-Memory Loading)
   │
   ├─> Add filename to processed_files set
   ├─> Note: Embeddings remain in database only
   └─> Similarity searches query database directly
   │
7. Return Success Response
   │
   └─> {
         status: "success",
         chunks_count: N,
         total_chunks_in_db: M
       }
```

**Key Changes from Traditional RAG:**

- ❌ No in-memory embedding matrices
- ✅ All embeddings stored in PostgreSQL with pgvector
- ✅ Database-backed similarity search with SQL queries
- ✅ Recency-weighted scoring at database level

### Query and Answer Generation

```
1. Client Query
   │
   ├─> POST /api/chatbot/chat
   │   └─> { query: "What is...?", chat_history: [...] }
   │
2. Dual Embedding Generation for Query
   │
   ├─> Generate text embedding (384-dim)
   │   └─> query_embedding = embedding_model.encode([query])[0]
   │
   └─> Generate Vintern embedding (768-dim) [if enabled]
       └─> q_emb = vintern_service.process_query(query)
   │
3. Database-Backed Similarity Search (Recency-Weighted)
   │
   ├─> search_relevant_documents(query, top_k=5, recency_weight=0.15)
   │   │
   │   └─> SQL Query to PostgreSQL:
   │       │
   │       ├─> SELECT chunk.*, document.*,
   │       │   (1 - (embedding <=> query_embedding)) * (1 + recency_boost)
   │       │   AS similarity_score
   │       │
   │       ├─> FROM document_chunks chunk
   │       │   JOIN documents doc ON chunk.document_id = doc.id
   │       │
   │       ├─> WHERE embedding IS NOT NULL
   │       │
   │       └─> ORDER BY similarity_score DESC
   │           LIMIT top_k
   │
   ├─> search_relevant_documents_vintern(query, top_k=5) [if enabled]
   │   │
   │   └─> Similar SQL query using vintern_embedding column
   │
   └─> Combine & Rank Results
       │
       ├─> Merge both result lists
       ├─> Sort by similarity score (descending)
       └─> Take top 5 overall
   │
4. Fallback: Keyword Search (if scores < 0.1 threshold)
   │
   └─> document_chunk_service.search_chunks_by_content(query)
       │
       └─> SQL: SELECT * FROM document_chunks
           WHERE content ILIKE '%query%'
           LIMIT 5
   │
5. Context Preparation
   │
   ├─> Select top 5 chunks
   │
   ├─> Format context string:
   │   └─> "--- (From file: 'X.pdf', Relevance: 0.85) ---"
   │       "[chunk content]"
   │
   └─> Extract source_files from top 1-2 results only
   │
6. LLM Answer Generation (Gemini 2.0 Flash)
   │
   ├─> Build prompt:
   │   │
   │   ├─> System instructions (grounding, citation rules)
   │   ├─> Context from retrieved chunks
   │   └─> User query
   │
   ├─> Call: llm.generate_content(prompt)
   │
   └─> Extract answer text
   │
7. Confidence Scoring & Response
   │
   ├─> confidence_score = top_result_similarity
   │
   ├─> Add confidence label:
   │   ├─> < 0.4: "Low - May not be closely related"
   │   ├─> 0.4-0.65: "Medium"
   │   └─> > 0.65: "High"
   │
   └─> Return:
       {
         answer: "... <br/>Confidence: 85% (High)",
         chat_history: [..., (query, answer)],
         source_files: ["doc1.pdf"]
       }
```

**Database Query Optimization:**

- Uses PostgreSQL pgvector extension for vector operations
- `<=>` operator: Cosine distance (1 - cosine similarity)
- Recency boost computed at database level
- Indexed vector columns for fast similarity search

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

### Asynchronous Initialization (Current)

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
│   └─> Register     │
│       filenames    │
│                    │
└─────────────> Ready ✓
                    │
Total: ~5 seconds (max of both)
```

**Key Difference:** Unlike traditional RAG systems, this implementation does not load embeddings into memory during initialization. Similarity searches are performed directly against the database using pgvector.

---

## Database Schema

```
┌─────────────────────────────────────────┐
│  documents                              │
├─────────────────────────────────────────┤
│  id                SERIAL PK            │
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
│  id                 SERIAL PK           │
│  document_id        INTEGER FK          │
│  chunk_index        INTEGER             │
│  heading            VARCHAR             │
│  content            TEXT                │
│  embedding          VECTOR(384)         │
│  vintern_embedding  VECTOR(768)         │
│  embedding_model    VARCHAR             │
│  vintern_model      VARCHAR             │
│  metadata           JSONB               │
│  created_at         TIMESTAMP           │
└─────────────────────────────────────────┘
```

---

## Dependency Graph

```
┌──────────────────────────────────────────────────┐
│                  Chatbot                         │
├──────────────────────────────────────────────────┤
│  Depends on:                                     │
│  ├─> Gemini (google.generativeai)                │
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
│  ├─> Success ✓                    │
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

- Setup models and load documents in parallel using `asyncio.gather()`
- Reduces total initialization time by ~30-40%
- Model loading and database queries run simultaneously

**Implementation:**

```python
# From chatbot_memory.py:66-75
setup_task = asyncio.create_task(asyncio.to_thread(instance.setup_models))
load_task = asyncio.create_task(asyncio.to_thread(instance.load_documents_from_database))
await asyncio.gather(setup_task, load_task)
```

### 2. Database-First Architecture (No In-Memory Embeddings)

**Traditional RAG Issues:**

- ❌ All embeddings loaded into RAM
- ❌ Memory usage scales linearly with document count
- ❌ System crashes when documents exceed available RAM
- ❌ Cold start requires loading all embeddings

**This Implementation:**

- ✅ Zero embeddings in memory
- ✅ Constant memory footprint regardless of document count
- ✅ pgvector extension handles similarity search in PostgreSQL
- ✅ Instant cold start (no embedding loading phase)

**Memory Comparison:**

```
Traditional RAG (In-Memory):
  10,000 chunks × 384 dims × 4 bytes = ~15 MB (text embeddings)
  10,000 chunks × 768 dims × 4 bytes = ~30 MB (vintern embeddings)
  Total: ~45 MB per 10k chunks + Python objects overhead

Database-First RAG (Current Implementation):
  Embeddings: 0 MB (stored in PostgreSQL with pgvector)
  Metadata only: ~1-2 MB per 10k chunks (filenames, document info)
  Model weights: ~1-2 GB (loaded once, shared across requests)
  Total: ~2 MB per 10k chunks + model weights (99%+ reduction for embeddings)
```

### 3. Vector Database with pgvector

**Key Features:**

- PostgreSQL extension for vector operations
- Indexed embeddings for O(log n) similarity search
- Native cosine distance operator (`<=>`)
- Supports vectors up to 16,000 dimensions

**Indexing Strategy:**

```sql
CREATE INDEX idx_embedding ON document_chunks
USING ivfflat (embedding vector_cosine_ops);

CREATE INDEX idx_vintern_embedding ON document_chunks
USING ivfflat (vintern_embedding vector_cosine_ops);
```

### 4. Recency-Weighted Scoring

**Problem:** Older documents dominate search results even when newer, more relevant docs exist

**Solution:** Boost similarity scores for recent documents

```python
# Recency weight: 0.15 (15% boost for most recent docs)
final_score = cosine_similarity + (recency_weight * recency_factor)

# recency_factor decreases exponentially with age
# Most recent doc: recency_factor ≈ 1.0
# 1 month old: recency_factor ≈ 0.5
# 6 months old: recency_factor ≈ 0.1
```

**Benefits:**

- Favors up-to-date information
- Configurable boost weight
- Prevents information staleness

### 5. Hybrid Search with Fallback

**Reliability Hierarchy:**

1. **Primary:** Vintern multimodal search (if enabled)
2. **Secondary:** SentenceTransformer text search
3. **Fallback:** PostgreSQL keyword search (ILIKE)

**When fallback triggers:**

- All vector results have similarity < 0.1
- No embeddings available
- Query contains very specific terms

### 6. Batch Embedding Generation

- Multiple texts/images embedded in single batch
- Reduces model inference overhead
- GPU utilization optimization for Vintern

**Implementation:**

```python
# From chatbot_memory.py:258-269
texts = [chunk.content for chunk in chunks]
vintern_text_embs = self.vintern_service.embed_texts(texts)  # Batch processing
```

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

## Architecture Summary: Database-First RAG

### What Makes This Different

This chatbot implements a **database-first RAG architecture** that fundamentally differs from traditional in-memory RAG systems:

#### Traditional RAG Architecture

```
Document → Embed → Store in DB
                 ↓
              Load into RAM (embeddings matrix)
                 ↓
Query → Embed → Search in RAM → Retrieve chunks → LLM
```

**Problems:**

- Memory usage grows with document count
- Cold start requires loading all embeddings
- Limited by available RAM
- Duplicate storage (DB + RAM)

#### This Implementation (Database-First RAG)

```
Document → Extract → Dual Embed → Store in PostgreSQL
                 ↓
              (No in-memory loading)
                 ↓
Query → Dual Embed → Search DB (pgvector + recency) → Fuse Results → Fallback → LLM
                 ↑
            PostgreSQL handles all
            vector operations natively
```

**Benefits:**

- ✅ Constant memory usage (~2MB per 10k chunks vs ~45MB traditional)
- ✅ Instant cold start (~5s async initialization)
- ✅ Unlimited scalability (limited by disk space, not RAM)
- ✅ Single source of truth (PostgreSQL with ACID guarantees)
- ✅ Recency-weighted retrieval (favors recent documents)
- ✅ Multimodal search (text + image embeddings)
- ✅ Hybrid fallback (vector + keyword search)

### Key Technical Decisions

| Aspect                | Decision                            | Rationale                                                       |
| --------------------- | ----------------------------------- | --------------------------------------------------------------- |
| **Embedding Storage** | PostgreSQL + pgvector               | Eliminates memory constraints, enables persistent vector search |
| **Similarity Search** | Database queries with recency boost | O(log n) with indexes, no need to load embeddings into RAM      |
| **Recency Weighting** | 15% boost with exponential decay    | Favors up-to-date information, prevents stale results           |
| **Dual Embeddings**   | Text (384-dim) + Vintern (768-dim)  | Multimodal support for text and images                          |
| **Search Fallback**   | Vector → Keyword (ILIKE)            | Ensures robustness when vector search fails (< 0.1 threshold)   |
| **Initialization**    | Async with `asyncio.gather()`       | 30-40% faster startup via concurrent model/doc loading          |
| **LLM**               | Gemini 2.0 Flash Lite               | Cost-effective, fast inference, multimodal capable              |
| **Chunk Strategy**    | Single chunk per document           | Simplifies ingestion, suitable for short documents              |
| **Error Handling**    | Graceful degradation                | Optional components (Vintern) can fail without breaking system  |

### System Characteristics

**Strengths:**

- 📊 Scalable to millions of documents (limited by disk space)
- ⚡ Fast cold start (~5s async initialization)
- 💾 Ultra-low memory footprint (constant regardless of doc count)
- 🔄 Recency-weighted search (15% boost for recent documents)
- 🖼️ Multimodal support (text + images via Vintern embeddings)
- 🔍 Hybrid search (vector similarity + keyword fallback)
- 🛡️ ACID compliance (PostgreSQL transactions)
- 🔧 Graceful degradation (Vintern optional, keyword fallback)
- 🚀 Concurrent initialization (30-40% faster startup)

**Trade-offs:**

- 🌐 Requires PostgreSQL + pgvector extension
- 📡 Network latency for each query (DB round-trip)
- 🔧 More complex setup than in-memory approaches
- ⏱️ Slightly slower per-query than pure in-memory (negligible for most use cases)

### Performance Profile

| Operation             | Time Complexity                 | Typical Latency | Notes                                  |
| --------------------- | ------------------------------- | --------------- | -------------------------------------- |
| **Document Upload**   | O(n) where n = doc size         | 5-30s           | Embedding generation + OCR for images  |
| **Similarity Search** | O(log m) where m = total chunks | 50-200ms        | pgvector IVFFlat index + recency boost |
| **Answer Generation** | O(k) where k = top_k chunks     | 1-3s            | Gemini 2.0 Flash Lite latency          |
| **Cold Start**        | O(1)                            | 4-6s            | Concurrent model loading               |
| **Memory Usage**      | O(1)                            | -               | Constant regardless of document count  |
| **Query Response**    | O(log m + k)                    | 1.5-4s          | Search + LLM generation                |

### Deployment Recommendations

**Development:**

```bash
# Using docker-compose for full stack
cd docker/
docker-compose -f docker-compose.development.yml up -d

# Or run PostgreSQL only
docker run -d \
  --name chatbot-postgres \
  -e POSTGRES_DB=chatbot_db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  pgvector/pgvector:pg15
```

**Production:**

- Use managed PostgreSQL with pgvector (AWS RDS, GCP Cloud SQL, Azure)
- Configure connection pooling (recommended: 10-20 connections)
- Enable pgvector indexes on both embedding columns
- Monitor database query performance
- Consider read replicas for high query volume

**Scaling Strategy:**

- Vertical scaling: Increase database instance size
- Horizontal scaling: Read replicas for query distribution
- Caching layer: Redis for frequently accessed chunks (optional)
- Async ingestion: Queue system for document processing (future)

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
Upload → Queue (RabbitMQ/Kafka) → Worker Pool → Database
            │
            └─> Process documents asynchronously
```

### 3. Advanced Chunking Strategy

- Current: 1 chunk per document
- Future: Semantic chunking with overlapping windows
- Benefit: Better granularity for long documents

### 4. Distributed Caching

```
Redis/Memcached for:
  - Frequently accessed chunks
  - Recent query results
  - Embedding cache for common queries
```

### 5. Horizontal Scaling

```
Load Balancer → Multiple Chatbot Instances → Shared Database
                                            → Read Replicas
```

### 6. Advanced Retrieval Techniques

- **Hypothetical Document Embeddings (HyDE)**: Generate hypothetical answers, embed, search
- **Query Expansion**: Expand user query with synonyms/related terms
- **Re-ranking**: Two-stage retrieval (fast recall + slow rerank)
- **Contextual Compression**: Remove irrelevant parts of retrieved chunks

---

**Last Updated:** 2025-12-06
**Version:** 2.2.0 - Database-First RAG Architecture
**Authors:** AI Development Team
