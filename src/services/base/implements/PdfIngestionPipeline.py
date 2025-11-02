from typing import Any, Dict, Tuple
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


class PdfIngestionPipeline(BaseIngestionPipeline):
    """
    Pipeline for ingesting PDF documents using a simple Embed->Store strategy.
    - Extract: delegated to ingestion service (reads PDF text)
    - Embed: SentenceTransformer (multilingual MiniLM)
    - Store: create document + single chunk with embedding
    """

    def __init__(self, ingestion_service: IIngestionService, embedding_model_name: str = 'paraphrase-multilingual-MiniLM-L12-v2'):
        super().__init__(ingestion_service)
        self._embedding_model_name = embedding_model_name
        # Lazy and resilient model init
        try:
            self._embedder = SentenceTransformer(self._embedding_model_name)
        except Exception as e:
            logger.warning("Failed to initialize SentenceTransformer '%s': %s", self._embedding_model_name, str(e))
            self._embedder = None

    def embed(self, content: str, file_path: str) -> Tuple[np.ndarray, Dict[str, Any]]:
        # Handle empty content gracefully
        if not content or not content.strip():
            logger.warning("PDF content is empty; creating minimal placeholder embedding")
            vector = np.zeros(384, dtype=np.float32)
        else:
            try:
                if self._embedder is None:
                    # Fallback to zero vector when model unavailable
                    logger.warning("Embedding model unavailable; using zero-vector fallback")
                    vector = np.zeros(384, dtype=np.float32)
                else:
                    vector = self._embedder.encode([content], show_progress_bar=False)[0]
            except Exception as e:
                logger.error("Embedding failed: %s", str(e))
                vector = np.zeros(384, dtype=np.float32)

        metadata: Dict[str, Any] = {
            'model': self._embedding_model_name,
            'filename': Path(file_path).name,
            'length': len(content) if content else 0,
        }
        return vector, metadata

    def store(self, content: str, vectors: Any, metadata: Dict[str, Any], file_path: str) -> Any:
        filename = Path(file_path).name
        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else None

        # Ensure vector is a plain list for JSON/pgvector compatibility
        if isinstance(vectors, np.ndarray):
            embedding_list = vectors.tolist()
        else:
            embedding_list = list(vectors)

        # Create or reuse document
        existing = document_service.check_document_exists_by_filename(filename, filename)
        if existing:
            doc = existing
        else:
            doc = document_service.create_document(
                filename=filename,
                original_filename=filename,
                file_type='PDF',
                file_path=file_path if os.path.exists(file_path) else None,
                file_size=file_size,
            )

        chunk = document_chunk_service.create_chunk(
            document_id=doc.id,
            chunk_index=0,
            heading='N/A',
            content=content,
            embedding=embedding_list,
            embedding_model=metadata.get('model', self._embedding_model_name),
            metadata={
                'source_file': filename,
                'file_type': 'PDF',
                'length': metadata.get('length', len(content)),
                'preview': content[:150] + '...' if len(content) > 150 else content,
            },
        )

        # Mark document as processed after successfully creating a chunk
        try:
            document_service.update_document_status(doc.id, 'processed')
        except Exception:
            # Non-fatal if status update fails
            pass

        result = {
            'document_id': doc.id,
            'chunk_id': chunk.id,
            'filename': filename,
            'embedding_model': metadata.get('model', self._embedding_model_name),
        }
        logger.info("Stored PDF document '%s' (doc=%s, chunk=%s)", filename, str(doc.id), str(chunk.id))
        return result