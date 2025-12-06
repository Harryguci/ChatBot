# RAG Service Enhancement Plan

## Executive Summary

This document outlines the plan to enhance the existing RAG chatbot system by integrating LangChain orchestration, improving PDF processing with OCR support, implementing advanced chunking strategies, and adding FAISS vector store capabilities.

## Current Architecture Analysis

### Strengths
- ✅ Database-first architecture with PostgreSQL + pgvector
- ✅ Dual embedding strategy (SentenceTransformer + Vintern)
- ✅ Recency-weighted similarity search
- ✅ Async initialization for fast startup
- ✅ Multimodal support (text + images)
- ✅ Hybrid search with keyword fallback

### Gaps (Based on ENHANCE_RAG_SERVICE.md)
1. **PDF Processing:** Using PyPDF2 instead of PyMuPDF (fitz)
2. **OCR Support:** No Tesseract integration for scanned PDFs
3. **Chunking Strategy:** Single chunk per document vs semantic chunking
4. **Query Enhancement:** No MultiQueryRetriever for query variations
5. **Vector Store:** Only pgvector, no FAISS local option
6. **Pipeline Orchestration:** Custom pipeline vs LangChain integration

## Enhancement Strategy

### Phase 1: Core Dependencies & Infrastructure

#### 1.1 Add Required Packages
```python
# requirements.txt additions:
PyMuPDF>=1.23.0          # High-speed PDF text extraction
pytesseract>=0.3.10      # OCR for scanned PDFs (already present)
langchain>=0.1.0         # RAG orchestration framework
langchain-community>=0.1.0
faiss-cpu>=1.7.4         # Local vector store (or faiss-gpu for GPU support)
tiktoken>=0.5.0          # Token counting for LangChain
```

#### 1.2 Update Docker Configuration
```yaml
# docker-compose.yml additions:
services:
  tesseract:
    image: tesseractshadow/tesseract4re
    container_name: chatbot-tesseract
    volumes:
      - /tmp/uploads:/tmp/uploads
    networks:
      - chatbot-network
    profiles:
      - ocr

  # Or install Tesseract in the backend container
  backend:
    build:
      context: ..
      dockerfile: DockerFile
    environment:
      - TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata
    # Add to Dockerfile: RUN apt-get install -y tesseract-ocr tesseract-ocr-vie tesseract-ocr-eng
```

### Phase 2: Enhanced PDF Processing

#### 2.1 PyMuPDF Integration
**File:** [src/services/base/implements/EnhancedPdfProcessor.py](src/services/base/implements/EnhancedPdfProcessor.py)

**Features:**
- Fast text extraction using fitz (PyMuPDF)
- Page-level analysis for text density
- Automatic OCR trigger when page has <150 characters
- Image rendering at 300 DPI for OCR
- Support for Vietnamese + English OCR

**Implementation Strategy:**
```python
class EnhancedPdfProcessor(IDocumentProcessor):
    def __init__(self):
        self.text_threshold = 150  # Characters per page
        self.dpi = 300  # For OCR image rendering

    def extract_content(self, file_path: str) -> str:
        doc = fitz.open(file_path)
        text = ""

        for page_num, page in enumerate(doc):
            # Try direct text extraction first
            page_text = page.get_text()

            # If page is scanned (low text density), use OCR
            if len(page_text.strip()) < self.text_threshold:
                page_text = self._ocr_page(page, page_num)

            text += page_text + "\n"

        return text

    def _ocr_page(self, page, page_num):
        # Render page to image at high DPI
        pix = page.get_pixmap(dpi=self.dpi)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        # OCR with Tesseract (Vietnamese + English)
        ocr_text = pytesseract.image_to_string(
            img,
            lang='vie+eng',
            config='--psm 3'
        )
        return ocr_text
```

#### 2.2 Strategy Selection
- PDF with text: Direct extraction via PyMuPDF
- Scanned PDF: Hybrid (extract text where available, OCR for images)
- Pure image PDF: Full OCR processing

### Phase 3: LangChain Integration

#### 3.1 Text Splitting with RecursiveCharacterTextSplitter
**File:** [src/services/base/implements/LangChainPdfIngestionPipeline.py](src/services/base/implements/LangChainPdfIngestionPipeline.py)

**Features:**
- Chunk size: 1500 characters
- Chunk overlap: 200 characters
- Recursive splitting by: \n\n → \n → . → space
- Metadata preservation (page number, source)

**Implementation:**
```python
from langchain.text_splitter import RecursiveCharacterTextSplitter

class LangChainPdfIngestionPipeline(BaseIngestionPipeline):
    def __init__(self, ingestion_service, embedding_model_name='paraphrase-multilingual-MiniLM-L12-v2'):
        super().__init__(ingestion_service)
        self._embedding_model_name = embedding_model_name
        self._embedder = SentenceTransformer(self._embedding_model_name)

        # LangChain text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1500,
            chunk_overlap=200,
            separators=["\n\n", "\n", ". ", " ", ""]
        )

    def process(self, file_path: str) -> Any:
        # Extract using EnhancedPdfProcessor
        content = self.extract(file_path)

        # Split into chunks
        chunks = self.text_splitter.split_text(content)

        # Embed each chunk
        embeddings = self._embedder.encode(chunks)

        # Store all chunks
        return self.store_chunks(chunks, embeddings, file_path)

    def store_chunks(self, chunks, embeddings, file_path):
        filename = Path(file_path).name

        # Create document
        doc = document_service.create_document(
            filename=filename,
            original_filename=filename,
            file_type='PDF',
            file_path=file_path,
            file_size=os.path.getsize(file_path)
        )

        # Create multiple chunks (instead of single chunk)
        for idx, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
            document_chunk_service.create_chunk(
                document_id=doc.id,
                chunk_index=idx,
                heading=f'Chunk {idx+1}',
                content=chunk_text,
                embedding=embedding.tolist(),
                embedding_model=self._embedding_model_name,
                metadata={
                    'source_file': filename,
                    'chunk_index': idx,
                    'total_chunks': len(chunks)
                }
            )

        return {
            'document_id': doc.id,
            'chunks_created': len(chunks),
            'filename': filename
        }
```

#### 3.2 MultiQueryRetriever Integration
**File:** [src/chatbot_memory.py](src/chatbot_memory.py) - Update search methods

**Features:**
- Generate 3-5 query variations
- Use Gemini LLM to create variations
- Search with each variation
- Combine and deduplicate results

**Implementation:**
```python
def generate_query_variations(self, query: str, num_variations: int = 3) -> List[str]:
    """Use Gemini to generate query variations for better retrieval coverage."""
    prompt = f"""Generate {num_variations} variations of the following question.
    The variations should ask the same thing but use different words and phrasings.

    Original question: {query}

    Provide only the variations, one per line, without numbering."""

    response = self.llm.generate_content(prompt)
    variations = [line.strip() for line in response.text.strip().split('\n') if line.strip()]

    # Include original query
    return [query] + variations[:num_variations]

def search_with_multi_query(self, query: str, top_k: int = 5) -> List[Tuple[str, float, dict]]:
    """Multi-query retrieval strategy."""
    query_variations = self.generate_query_variations(query)

    all_results = []
    seen_chunk_ids = set()

    for q in query_variations:
        results = self.search_relevant_documents(q, top_k=top_k)

        for content, score, metadata in results:
            chunk_id = metadata.get('chunk_id')
            if chunk_id not in seen_chunk_ids:
                all_results.append((content, score, metadata))
                seen_chunk_ids.add(chunk_id)

    # Sort by score and return top k
    all_results.sort(key=lambda x: x[1], reverse=True)
    return all_results[:top_k]
```

### Phase 4: FAISS Integration (Hybrid Approach)

#### 4.1 Dual Vector Store Strategy
**Option A: PostgreSQL pgvector as primary, FAISS as cache**
- pgvector: Persistent storage, ACID compliance
- FAISS: In-memory cache for fast lookups during session

**Option B: FAISS as primary, PostgreSQL for metadata**
- FAISS: Vector similarity search
- PostgreSQL: Document metadata, content, tracking

**Recommendation: Option A (Hybrid)**
- Maintain database-first architecture
- Add FAISS as optional performance layer
- Configurable via environment variable

#### 4.2 Implementation
**File:** [src/services/base/implements/FAISSVectorStore.py](src/services/base/implements/FAISSVectorStore.py)

```python
import faiss
import numpy as np
from typing import List, Tuple, Optional

class FAISSVectorStore:
    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self.index = faiss.IndexFlatIP(dimension)  # Inner product (cosine similarity)
        self.chunk_id_map = []  # Maps FAISS index to chunk_id

    def add_embeddings(self, embeddings: np.ndarray, chunk_ids: List[int]):
        """Add embeddings to FAISS index."""
        # Normalize for cosine similarity
        faiss.normalize_L2(embeddings)
        self.index.add(embeddings)
        self.chunk_id_map.extend(chunk_ids)

    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> List[Tuple[int, float]]:
        """Search FAISS index and return (chunk_id, similarity_score)."""
        # Normalize query
        faiss.normalize_L2(query_embedding)

        # Search
        distances, indices = self.index.search(query_embedding, top_k)

        # Map to chunk IDs
        results = [
            (self.chunk_id_map[idx], float(dist))
            for idx, dist in zip(indices[0], distances[0])
            if idx < len(self.chunk_id_map)
        ]

        return results

    def save(self, filepath: str):
        """Persist FAISS index to disk."""
        faiss.write_index(self.index, filepath)

    def load(self, filepath: str):
        """Load FAISS index from disk."""
        self.index = faiss.read_index(filepath)
```

**Integration in Chatbot:**
```python
class Chatbot:
    def __init__(self, google_api_key: str, use_faiss: bool = False):
        self.use_faiss = use_faiss

        if self.use_faiss:
            self.faiss_store = FAISSVectorStore(dimension=384)
            self.faiss_vintern_store = FAISSVectorStore(dimension=768)

    def load_documents_from_database(self):
        """Load metadata and optionally build FAISS index."""
        documents = document_service.get_all_processed_documents()

        if self.use_faiss:
            # Build FAISS indexes from database
            all_chunks = document_chunk_service.get_all_chunks_with_embeddings()

            embeddings = np.array([chunk.embedding for chunk in all_chunks])
            chunk_ids = [chunk.id for chunk in all_chunks]

            self.faiss_store.add_embeddings(embeddings, chunk_ids)
            logger.info(f"Built FAISS index with {len(chunk_ids)} chunks")

    def search_relevant_documents(self, query: str, top_k: int = 5):
        """Search using FAISS if enabled, otherwise use database."""
        query_embedding = self.embedding_model.encode([query])[0]

        if self.use_faiss:
            # FAISS search
            results = self.faiss_store.search(query_embedding.reshape(1, -1), top_k)

            # Fetch chunk data from database
            chunks_with_scores = []
            for chunk_id, score in results:
                chunk = document_chunk_service.get_chunk_by_id(chunk_id)
                if chunk:
                    chunks_with_scores.append((chunk, score))

            return self._format_search_results(chunks_with_scores)
        else:
            # Database search (existing implementation)
            return super().search_relevant_documents(query, top_k)
```

### Phase 5: Date-Based Filtering Enhancement

**Current Implementation:**
- ✅ Recency weighting (15% boost for new docs)
- ✅ Exponential decay based on age

**Enhancement:**
- Add explicit date range filtering
- Support user queries like "documents from last month"
- Extract temporal expressions from queries

**Implementation:**
```python
def search_with_date_filter(
    self,
    query: str,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    top_k: int = 5
) -> List[Tuple[str, float, dict]]:
    """Search with explicit date range filter."""
    query_embedding = self.embedding_model.encode([query])[0]

    # Use database service with date filtering
    chunks_with_scores = document_chunk_service.find_similar_chunks_with_date_filter(
        query_embedding=query_embedding.tolist(),
        limit=top_k,
        date_from=date_from,
        date_to=date_to,
        recency_weight=0.15
    )

    return self._format_search_results(chunks_with_scores)
```

## Implementation Roadmap

### Sprint 1: Foundation (Week 1)
- [ ] Add dependencies to requirements.txt
- [ ] Update docker-compose.yml for Tesseract
- [ ] Create EnhancedPdfProcessor with PyMuPDF + OCR
- [ ] Unit tests for enhanced PDF processing

### Sprint 2: Chunking & LangChain (Week 2)
- [ ] Implement LangChainPdfIngestionPipeline
- [ ] Integrate RecursiveCharacterTextSplitter
- [ ] Update database schema if needed (chunk metadata)
- [ ] Migration script for existing documents

### Sprint 3: Query Enhancement (Week 3)
- [ ] Implement MultiQueryRetriever
- [ ] Add query variation generation
- [ ] Performance benchmarking

### Sprint 4: FAISS Integration (Week 4)
- [ ] Implement FAISSVectorStore
- [ ] Add hybrid search strategy
- [ ] Configuration options (enable/disable FAISS)
- [ ] Performance comparison tests

### Sprint 5: Testing & Documentation (Week 5)
- [ ] End-to-end testing
- [ ] Performance benchmarks
- [ ] Update API documentation
- [ ] User guide for new features

## Configuration Management

### Environment Variables
```bash
# .env additions
USE_FAISS=false                    # Enable FAISS hybrid mode
CHUNK_SIZE=1500                    # Text chunk size
CHUNK_OVERLAP=200                  # Chunk overlap
MULTI_QUERY_ENABLED=true           # Enable MultiQueryRetriever
OCR_ENABLED=true                   # Enable Tesseract OCR
OCR_LANGUAGES=vie+eng              # Tesseract languages
TEXT_THRESHOLD=150                 # Min chars for OCR trigger
```

## Performance Considerations

### Expected Improvements
1. **PDF Processing:**
   - PyMuPDF: 3-5x faster than PyPDF2
   - OCR: Slower but handles scanned docs

2. **Chunking:**
   - Better granularity for long documents
   - Improved context relevance
   - Slight increase in storage (more chunks)

3. **MultiQuery:**
   - Better recall (finds more relevant docs)
   - Higher API costs (more LLM calls)
   - Configurable (can be disabled)

4. **FAISS:**
   - Faster similarity search (ms vs tens of ms)
   - Memory overhead (if enabled)
   - Trade-off: Speed vs memory

### Benchmarks to Track
- PDF processing time (with/without OCR)
- Query latency (database vs FAISS)
- Chunk retrieval accuracy
- Memory usage (FAISS enabled vs disabled)

## Migration Strategy

### Backward Compatibility
- Keep existing pipelines functional
- Add new pipelines as alternatives
- Gradual migration path for existing documents

### Migration Script
```python
# scripts/migrate_to_langchain_chunks.py
def migrate_document(document_id: int):
    """Re-process document with new chunking strategy."""
    doc = document_service.get_document_by_id(document_id)

    # Delete old chunks
    old_chunks = document_chunk_service.get_chunks_by_document(document_id)
    for chunk in old_chunks:
        document_chunk_service.delete_chunk(chunk.id)

    # Re-process with new pipeline
    pipeline = LangChainPdfIngestionPipeline(...)
    pipeline.process(doc.file_path)
```

## Risk Mitigation

### Risks & Mitigations
1. **OCR Accuracy**
   - Risk: Poor quality scans yield bad text
   - Mitigation: Confidence scores, manual review option

2. **Memory Usage (FAISS)**
   - Risk: Large document sets exceed memory
   - Mitigation: Make FAISS optional, configurable limits

3. **Breaking Changes**
   - Risk: Existing integrations break
   - Mitigation: Versioned APIs, backward compatibility

4. **Performance Regression**
   - Risk: New features slow down queries
   - Mitigation: Benchmarks, A/B testing, feature flags

## Success Metrics

### Key Performance Indicators
- ✅ PDF processing speed: >3x improvement with PyMuPDF
- ✅ OCR success rate: >90% for scanned PDFs
- ✅ Chunk quality: Improved context relevance (measured by user feedback)
- ✅ Query accuracy: >10% improvement with MultiQuery
- ✅ Search latency: <100ms with FAISS (vs <200ms database)

## Conclusion

This enhancement plan transforms the chatbot from a database-first RAG system to a **hybrid, LangChain-powered RAG system** with:
- Advanced PDF processing (PyMuPDF + OCR)
- Semantic chunking (RecursiveCharacterTextSplitter)
- Query enhancement (MultiQueryRetriever)
- Optional FAISS acceleration
- Maintained database-first architecture

The phased approach ensures minimal disruption while delivering significant improvements in accuracy, performance, and capability.

---

**Document Version:** 1.0
**Last Updated:** 2025-12-06
**Status:** Planning Phase
