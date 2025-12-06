"""
FAISS Vector Store for hybrid RAG architecture.

This service provides in-memory vector similarity search as a
complementary layer to the PostgreSQL pgvector database.

Use cases:
- Fast similarity search during active sessions
- Reduced database load for repeated queries
- Optional acceleration layer (can be disabled)
"""

import logging
import os
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any

import numpy as np

logger = logging.getLogger(__name__)

# Import FAISS with fallback handling
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    logger.warning("FAISS not available. Install: pip install faiss-cpu or faiss-gpu")
    FAISS_AVAILABLE = False


class FAISSVectorStore:
    """
    FAISS-based vector store for efficient similarity search.

    This store operates alongside PostgreSQL pgvector as an optional
    performance layer. It maintains chunk_id mappings to link FAISS
    results back to database records.

    Features:
    - Fast cosine similarity search
    - Batch operations for efficiency
    - Persistence to disk
    - Automatic L2 normalization for cosine similarity
    """

    def __init__(
        self,
        dimension: int = 384,
        index_type: str = 'Flat',
        metric: str = 'cosine'
    ):
        """
        Initialize FAISS vector store.

        Args:
            dimension: Embedding vector dimension (default: 384)
            index_type: FAISS index type - 'Flat' or 'IVF' (default: 'Flat')
            metric: Similarity metric - 'cosine' or 'euclidean' (default: 'cosine')
        """
        self.dimension = dimension
        self.index_type = index_type
        self.metric = metric
        self.chunk_id_map: List[int] = []  # Maps FAISS index to chunk_id
        self.index: Optional[Any] = None

        if not FAISS_AVAILABLE:
            logger.error("FAISS not available - vector store will not function")
            return

        # Initialize FAISS index
        self._initialize_index()

    def _initialize_index(self):
        """Initialize the FAISS index based on configuration."""
        if not FAISS_AVAILABLE:
            return

        try:
            if self.metric == 'cosine':
                # Use Inner Product for cosine similarity (after L2 normalization)
                self.index = faiss.IndexFlatIP(self.dimension)
                logger.info(f"Initialized FAISS IndexFlatIP (cosine) with dim={self.dimension}")

            elif self.metric == 'euclidean':
                # Use L2 distance
                self.index = faiss.IndexFlatL2(self.dimension)
                logger.info(f"Initialized FAISS IndexFlatL2 (L2) with dim={self.dimension}")

            else:
                logger.error(f"Unknown metric: {self.metric}, defaulting to cosine")
                self.index = faiss.IndexFlatIP(self.dimension)

        except Exception as e:
            logger.error(f"Failed to initialize FAISS index: {str(e)}")
            self.index = None

    def is_enabled(self) -> bool:
        """Check if FAISS is available and enabled."""
        return FAISS_AVAILABLE and self.index is not None

    def add_embedding(self, embedding: np.ndarray, chunk_id: int):
        """
        Add a single embedding to the index.

        Args:
            embedding: Embedding vector (1D numpy array)
            chunk_id: Database chunk ID
        """
        self.add_embeddings(embedding.reshape(1, -1), [chunk_id])

    def add_embeddings(self, embeddings: np.ndarray, chunk_ids: List[int]):
        """
        Add multiple embeddings to the index.

        Args:
            embeddings: Embedding matrix (N x dimension)
            chunk_ids: List of database chunk IDs
        """
        if not self.is_enabled():
            logger.warning("FAISS not enabled, skipping add operation")
            return

        if len(chunk_ids) != embeddings.shape[0]:
            raise ValueError(
                f"Mismatch: {len(chunk_ids)} chunk_ids but {embeddings.shape[0]} embeddings"
            )

        try:
            # Ensure correct shape and dtype
            embeddings = embeddings.astype(np.float32)

            # Normalize for cosine similarity
            if self.metric == 'cosine':
                faiss.normalize_L2(embeddings)

            # Add to index
            self.index.add(embeddings)

            # Update chunk ID mapping
            self.chunk_id_map.extend(chunk_ids)

            logger.debug(f"Added {len(chunk_ids)} embeddings to FAISS index")

        except Exception as e:
            logger.error(f"Failed to add embeddings to FAISS: {str(e)}")
            raise

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5
    ) -> List[Tuple[int, float]]:
        """
        Search for similar embeddings.

        Args:
            query_embedding: Query vector (1D or 2D numpy array)
            top_k: Number of results to return

        Returns:
            List of (chunk_id, similarity_score) tuples, sorted by score descending
        """
        if not self.is_enabled():
            logger.warning("FAISS not enabled, returning empty results")
            return []

        if self.index.ntotal == 0:
            logger.warning("FAISS index is empty")
            return []

        try:
            # Ensure correct shape
            if query_embedding.ndim == 1:
                query_embedding = query_embedding.reshape(1, -1)

            query_embedding = query_embedding.astype(np.float32)

            # Normalize for cosine similarity
            if self.metric == 'cosine':
                faiss.normalize_L2(query_embedding)

            # Perform search
            top_k = min(top_k, self.index.ntotal)  # Can't return more than we have
            distances, indices = self.index.search(query_embedding, top_k)

            # Convert to results
            results = []
            for idx, dist in zip(indices[0], distances[0]):
                if idx < len(self.chunk_id_map):
                    chunk_id = self.chunk_id_map[idx]

                    # Convert distance to similarity score
                    if self.metric == 'cosine':
                        # For inner product after normalization, distance IS cosine similarity
                        similarity = float(dist)
                    else:
                        # For L2, convert distance to similarity (inverse)
                        similarity = 1.0 / (1.0 + float(dist))

                    results.append((chunk_id, similarity))

            logger.debug(f"FAISS search returned {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"FAISS search failed: {str(e)}")
            return []

    def save(self, filepath: str):
        """
        Save FAISS index and chunk mappings to disk.

        Args:
            filepath: Base path for saving (without extension)
        """
        if not self.is_enabled():
            logger.warning("FAISS not enabled, skipping save")
            return

        try:
            # Save FAISS index
            index_path = f"{filepath}.index"
            faiss.write_index(self.index, index_path)

            # Save chunk ID mapping
            mapping_path = f"{filepath}.mapping.npy"
            np.save(mapping_path, np.array(self.chunk_id_map))

            logger.info(
                f"Saved FAISS index ({self.index.ntotal} vectors) to {index_path}"
            )

        except Exception as e:
            logger.error(f"Failed to save FAISS index: {str(e)}")
            raise

    def load(self, filepath: str):
        """
        Load FAISS index and chunk mappings from disk.

        Args:
            filepath: Base path for loading (without extension)
        """
        if not FAISS_AVAILABLE:
            logger.error("FAISS not available, cannot load index")
            return

        try:
            # Load FAISS index
            index_path = f"{filepath}.index"
            if not os.path.exists(index_path):
                logger.warning(f"FAISS index file not found: {index_path}")
                return

            self.index = faiss.read_index(index_path)

            # Load chunk ID mapping
            mapping_path = f"{filepath}.mapping.npy"
            if os.path.exists(mapping_path):
                chunk_id_array = np.load(mapping_path)
                self.chunk_id_map = chunk_id_array.tolist()
            else:
                logger.warning(f"Chunk mapping file not found: {mapping_path}")
                self.chunk_id_map = list(range(self.index.ntotal))

            logger.info(
                f"Loaded FAISS index with {self.index.ntotal} vectors from {index_path}"
            )

        except Exception as e:
            logger.error(f"Failed to load FAISS index: {str(e)}")
            raise

    def clear(self):
        """Clear the index and chunk mappings."""
        if self.is_enabled():
            self.index.reset()
            self.chunk_id_map = []
            logger.info("Cleared FAISS index")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the vector store.

        Returns:
            Dictionary with index statistics
        """
        if not self.is_enabled():
            return {
                'enabled': False,
                'total_vectors': 0
            }

        return {
            'enabled': True,
            'total_vectors': self.index.ntotal,
            'dimension': self.dimension,
            'metric': self.metric,
            'index_type': self.index_type,
            'chunk_ids_mapped': len(self.chunk_id_map)
        }

    def rebuild_from_database(self, chunks_with_embeddings: List[Tuple[int, np.ndarray]]):
        """
        Rebuild FAISS index from database chunks.

        Args:
            chunks_with_embeddings: List of (chunk_id, embedding) tuples
        """
        if not self.is_enabled():
            logger.warning("FAISS not enabled, skipping rebuild")
            return

        logger.info(f"Rebuilding FAISS index from {len(chunks_with_embeddings)} chunks...")

        # Clear existing index
        self.clear()

        if not chunks_with_embeddings:
            logger.warning("No chunks to rebuild index from")
            return

        # Separate chunk IDs and embeddings
        chunk_ids = [chunk_id for chunk_id, _ in chunks_with_embeddings]
        embeddings = np.vstack([emb for _, emb in chunks_with_embeddings])

        # Add to index
        self.add_embeddings(embeddings, chunk_ids)

        logger.info(f"FAISS index rebuilt with {self.index.ntotal} vectors")


class FAISSManager:
    """
    Manager for multiple FAISS stores (text and Vintern embeddings).
    """

    def __init__(self):
        """Initialize FAISS manager with stores for different embedding types."""
        self.use_faiss = os.getenv('USE_FAISS', 'false').lower() == 'true'

        if self.use_faiss and FAISS_AVAILABLE:
            # Text embeddings store (384-dim)
            self.text_store = FAISSVectorStore(dimension=384, metric='cosine')

            # Vintern embeddings store (768-dim)
            self.vintern_store = FAISSVectorStore(dimension=768, metric='cosine')

            logger.info("FAISS manager initialized with text and vintern stores")
        else:
            self.text_store = None
            self.vintern_store = None

            if self.use_faiss:
                logger.warning("FAISS requested but not available")
            else:
                logger.info("FAISS disabled by configuration")

    def is_enabled(self) -> bool:
        """Check if FAISS is enabled and available."""
        return self.use_faiss and FAISS_AVAILABLE

    def get_text_store(self) -> Optional[FAISSVectorStore]:
        """Get the text embeddings store."""
        return self.text_store

    def get_vintern_store(self) -> Optional[FAISSVectorStore]:
        """Get the Vintern embeddings store."""
        return self.vintern_store

    def save_all(self, base_path: str):
        """Save all FAISS stores to disk."""
        if not self.is_enabled():
            return

        base_dir = Path(base_path)
        base_dir.mkdir(parents=True, exist_ok=True)

        if self.text_store:
            self.text_store.save(str(base_dir / "text"))

        if self.vintern_store:
            self.vintern_store.save(str(base_dir / "vintern"))

        logger.info(f"Saved all FAISS indexes to {base_path}")

    def load_all(self, base_path: str):
        """Load all FAISS stores from disk."""
        if not self.is_enabled():
            return

        base_dir = Path(base_path)

        if self.text_store and (base_dir / "text.index").exists():
            self.text_store.load(str(base_dir / "text"))

        if self.vintern_store and (base_dir / "vintern.index").exists():
            self.vintern_store.load(str(base_dir / "vintern"))

        logger.info(f"Loaded FAISS indexes from {base_path}")
