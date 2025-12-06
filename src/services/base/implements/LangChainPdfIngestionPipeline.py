"""
LangChain-powered PDF Ingestion Pipeline with semantic chunking.

This pipeline provides:
- RecursiveCharacterTextSplitter for intelligent chunking
- Configurable chunk size and overlap
- Multiple chunks per document for better granularity
- Metadata preservation across chunks
"""

from typing import Any, Dict, List, Tuple
from pathlib import Path
import os
import logging

import numpy as np
from sentence_transformers import SentenceTransformer

from src.services.base.implements.BaseIngestionPipeline import BaseIngestionPipeline
from src.services.base.interfaces.IIngestionService import IIngestionService
from src.config.db.services import (
    document_service,
    document_chunk_service,
)

logger = logging.getLogger(__name__)

# Import LangChain with fallback
try:
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    LANGCHAIN_AVAILABLE = True
except ImportError:
    logger.warning("LangChain not available. Install: pip install langchain")
    LANGCHAIN_AVAILABLE = False


class LangChainPdfIngestionPipeline(BaseIngestionPipeline):
    """
    Enhanced PDF ingestion pipeline using LangChain for semantic chunking.

    This pipeline splits documents into overlapping chunks for better
    context preservation and retrieval accuracy.

    Features:
    - Semantic chunking with RecursiveCharacterTextSplitter
    - Configurable chunk size (default: 1500 chars)
    - Configurable overlap (default: 200 chars)
    - Multiple chunks per document
    - Preserves document metadata
    """

    def __init__(
        self,
        ingestion_service: IIngestionService,
        embedding_model_name: str = 'paraphrase-multilingual-MiniLM-L12-v2',
        chunk_size: int = 1500,
        chunk_overlap: int = 200
    ):
        """
        Initialize the LangChain PDF ingestion pipeline.

        Args:
            ingestion_service: Service for extracting content from PDFs
            embedding_model_name: Name of the SentenceTransformer model
            chunk_size: Maximum characters per chunk
            chunk_overlap: Character overlap between chunks
        """
        super().__init__(ingestion_service)
        self._embedding_model_name = embedding_model_name

        # Load chunk configuration from environment or use defaults
        self.chunk_size = int(os.getenv('CHUNK_SIZE', chunk_size))
        self.chunk_overlap = int(os.getenv('CHUNK_OVERLAP', chunk_overlap))

        logger.info(
            f"LangChain pipeline initialized: chunk_size={self.chunk_size}, "
            f"overlap={self.chunk_overlap}"
        )

        # Initialize embedding model
        try:
            self._embedder = SentenceTransformer(self._embedding_model_name)
            logger.info(f"Loaded embedding model: {self._embedding_model_name}")
        except Exception as e:
            logger.warning(f"Failed to initialize SentenceTransformer: {str(e)}")
            self._embedder = None

        # Initialize LangChain text splitter
        if LANGCHAIN_AVAILABLE:
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                length_function=len,
                separators=["\n\n", "\n", ". ", "。", "! ", "! ", "? ", "? ", ";", ":", ",", " ", ""],
                is_separator_regex=False
            )
            logger.info("RecursiveCharacterTextSplitter initialized")
        else:
            self.text_splitter = None
            logger.warning("LangChain not available, falling back to simple chunking")

    def process(self, file_path: str) -> Any:
        """
        Process PDF: Extract → Chunk → Embed → Store.

        Args:
            file_path: Path to PDF file

        Returns:
            Dictionary with processing results
        """
        try:
            logger.info(f"Starting LangChain pipeline for: {Path(file_path).name}")

            # Step 1: Extract content using ingestion service
            content = self.extract(file_path)

            if not content or not content.strip():
                logger.warning(f"No content extracted from {Path(file_path).name}")
                return {
                    'status': 'error',
                    'message': 'No content extracted from PDF'
                }

            # Step 2: Split into chunks
            chunks = self._split_text(content)
            logger.info(f"Split into {len(chunks)} chunks")

            # Step 3: Embed all chunks
            embeddings = self._embed_chunks(chunks)

            # Step 4: Store document and chunks
            result = self.store(content, embeddings, {'chunks': chunks}, file_path)

            logger.info(
                f"Successfully processed {Path(file_path).name}: "
                f"{len(chunks)} chunks created"
            )

            return result

        except Exception as e:
            logger.error(f"LangChain pipeline error: {str(e)}")
            raise

    def _split_text(self, text: str) -> List[str]:
        """
        Split text into chunks using RecursiveCharacterTextSplitter.

        Args:
            text: Full document text

        Returns:
            List of text chunks
        """
        if LANGCHAIN_AVAILABLE and self.text_splitter:
            # Use LangChain splitter
            chunks = self.text_splitter.split_text(text)
            return chunks
        else:
            # Fallback: Simple chunking by characters
            return self._simple_chunk(text)

    def _simple_chunk(self, text: str) -> List[str]:
        """
        Fallback chunking strategy if LangChain is not available.

        Args:
            text: Full document text

        Returns:
            List of text chunks
        """
        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            end = start + self.chunk_size

            # If not the last chunk, try to break at a sentence boundary
            if end < text_length:
                # Look for sentence ending in the overlap region
                search_start = max(start, end - self.chunk_overlap)
                search_end = min(end + 50, text_length)

                # Find the last period, exclamation, or question mark
                last_period = text.rfind('.', search_start, search_end)
                last_exclaim = text.rfind('!', search_start, search_end)
                last_question = text.rfind('?', search_start, search_end)

                best_break = max(last_period, last_exclaim, last_question)

                if best_break != -1 and best_break > start:
                    end = best_break + 1

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            # Move start position (with overlap)
            start = end - self.chunk_overlap if end < text_length else text_length

        return chunks

    def _embed_chunks(self, chunks: List[str]) -> List[np.ndarray]:
        """
        Generate embeddings for all chunks.

        Args:
            chunks: List of text chunks

        Returns:
            List of embedding vectors
        """
        if not self._embedder:
            logger.warning("Embedding model not available, using zero vectors")
            return [np.zeros(384, dtype=np.float32) for _ in chunks]

        try:
            # Batch encode all chunks for efficiency
            embeddings = self._embedder.encode(
                chunks,
                show_progress_bar=len(chunks) > 10,
                batch_size=32
            )

            logger.info(f"Generated embeddings for {len(chunks)} chunks")
            return embeddings

        except Exception as e:
            logger.error(f"Embedding generation failed: {str(e)}")
            # Return zero vectors as fallback
            return [np.zeros(384, dtype=np.float32) for _ in chunks]

    def embed(self, content: str, file_path: str) -> Tuple[List[np.ndarray], Dict[str, Any]]:
        """
        Embed content (required by BaseIngestionPipeline).

        Note: This method is not used in the LangChain pipeline since we
        override the process() method directly.

        Args:
            content: Document content
            file_path: Path to file

        Returns:
            Tuple of (embeddings list, metadata)
        """
        chunks = self._split_text(content)
        embeddings = self._embed_chunks(chunks)

        metadata = {
            'model': self._embedding_model_name,
            'filename': Path(file_path).name,
            'chunks': chunks,
            'chunk_count': len(chunks)
        }

        return embeddings, metadata

    def store(
        self,
        content: str,
        embeddings: Any,
        metadata: Dict[str, Any],
        file_path: str
    ) -> Any:
        """
        Store document and all chunks in database.

        Args:
            content: Full document content
            embeddings: List of embedding vectors for each chunk
            metadata: Metadata including chunks
            file_path: Path to source file

        Returns:
            Dictionary with storage results
        """
        filename = Path(file_path).name
        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else None

        chunks = metadata.get('chunks', [])

        if len(chunks) != len(embeddings):
            logger.error(
                f"Chunk/embedding mismatch: {len(chunks)} chunks, "
                f"{len(embeddings)} embeddings"
            )
            raise ValueError("Number of chunks must match number of embeddings")

        # Check if document exists
        existing = document_service.check_document_exists_by_filename(filename, filename)

        if existing:
            logger.info(f"Document already exists: {filename} (ID: {existing.id})")
            doc = existing

            # Delete old chunks to replace with new ones
            old_chunks = document_chunk_service.get_chunks_by_document(doc.id)
            for old_chunk in old_chunks:
                try:
                    document_chunk_service.delete_chunk(old_chunk.id)
                except Exception:
                    pass

            logger.info(f"Deleted {len(old_chunks)} old chunks for re-processing")
        else:
            # Create new document
            doc = document_service.create_document(
                filename=filename,
                original_filename=filename,
                file_type='PDF',
                file_path=file_path if os.path.exists(file_path) else None,
                file_size=file_size,
                metadata={
                    'chunk_strategy': 'langchain',
                    'chunk_size': self.chunk_size,
                    'chunk_overlap': self.chunk_overlap
                }
            )
            logger.info(f"Created document: {filename} (ID: {doc.id})")

        # Store each chunk with its embedding
        chunk_ids = []

        for idx, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
            # Convert embedding to list
            if isinstance(embedding, np.ndarray):
                embedding_list = embedding.tolist()
            else:
                embedding_list = list(embedding)

            # Create chunk record
            chunk = document_chunk_service.create_chunk(
                document_id=doc.id,
                chunk_index=idx,
                heading=f'Chunk {idx + 1}/{len(chunks)}',
                content=chunk_text,
                embedding=embedding_list,
                embedding_model=self._embedding_model_name,
                metadata={
                    'source_file': filename,
                    'chunk_index': idx,
                    'total_chunks': len(chunks),
                    'chunk_size': len(chunk_text),
                    'chunk_strategy': 'langchain'
                }
            )

            chunk_ids.append(chunk.id)

        # Mark document as processed
        try:
            document_service.update_document_status(doc.id, 'processed')
        except Exception as e:
            logger.warning(f"Failed to update document status: {str(e)}")

        result = {
            'status': 'success',
            'document_id': doc.id,
            'filename': filename,
            'chunk_ids': chunk_ids,
            'chunks_created': len(chunk_ids),
            'embedding_model': self._embedding_model_name,
            'chunk_size': self.chunk_size,
            'chunk_overlap': self.chunk_overlap
        }

        logger.info(
            f"Stored document {filename}: {len(chunk_ids)} chunks "
            f"(doc_id={doc.id})"
        )

        return result
