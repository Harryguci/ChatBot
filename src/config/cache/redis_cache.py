"""
Redis caching module for query results.
Provides fast in-memory caching to reduce database load and improve response times.
Supports semantic caching using embeddings to match similar queries.
"""

import os
import json
import hashlib
import logging
import numpy as np
from typing import Optional, Any, List, Dict, Tuple
from dotenv import load_dotenv
import redis
from redis.exceptions import RedisError

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)


class RedisCache:
    """Redis cache manager for chatbot query results with semantic caching support."""

    def __init__(
        self,
        host: str = None,
        port: int = None,
        db: int = None,
        password: str = None,
        decode_responses: bool = True,
        enabled: bool = True,
        semantic_similarity_threshold: float = None
    ):
        """
        Initialize Redis cache connection.

        Args:
            host: Redis host (default from REDIS_HOST env)
            port: Redis port (default from REDIS_PORT env)
            db: Redis database number (default from REDIS_DB env)
            password: Redis password (default from REDIS_PASSWORD env)
            decode_responses: Decode responses to strings
            enabled: Enable/disable caching (default from REDIS_ENABLED env)
            semantic_similarity_threshold: Cosine similarity threshold for semantic cache hits (0-1)
        """
        self.enabled = enabled and os.getenv('REDIS_ENABLED', 'true').lower() == 'true'
        self.host = host or os.getenv('REDIS_HOST', 'localhost')
        self.port = port or int(os.getenv('REDIS_PORT', '6379'))
        self.db = db or int(os.getenv('REDIS_DB', '0'))
        self.password = password or os.getenv('REDIS_PASSWORD', None)
        self.decode_responses = decode_responses
        self.client: Optional[redis.Redis] = None

        # Semantic caching configuration
        self.semantic_threshold = semantic_similarity_threshold or float(
            os.getenv('REDIS_SEMANTIC_THRESHOLD', '0.95')
        )
        self._embedding_model = None
        self._semantic_enabled = os.getenv('REDIS_SEMANTIC_CACHE', 'true').lower() == 'true'

        if self.enabled:
            self._initialize_client()
            if self._semantic_enabled:
                self._initialize_embedding_model()

    def _initialize_client(self):
        """Initialize Redis client connection."""
        try:
            self.client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=self.decode_responses,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )

            # Test connection
            self.client.ping()
            logger.info(f"Redis cache initialized successfully at {self.host}:{self.port}")

        except RedisError as e:
            logger.warning(f"Failed to connect to Redis: {str(e)}")
            logger.warning("Caching will be disabled. Application will continue without cache.")
            self.enabled = False
            self.client = None
        except Exception as e:
            logger.error(f"Unexpected error initializing Redis: {str(e)}")
            self.enabled = False
            self.client = None

    def _initialize_embedding_model(self):
        """Initialize lightweight embedding model for semantic caching."""
        try:
            from sentence_transformers import SentenceTransformer

            # Use a lightweight model for fast cache lookups
            model_name = os.getenv('CACHE_EMBEDDING_MODEL', 'paraphrase-multilingual-MiniLM-L12-v2')
            self._embedding_model = SentenceTransformer(model_name)
            logger.info(f"Semantic caching enabled with model: {model_name}")

        except Exception as e:
            logger.warning(f"Failed to initialize semantic cache embeddings: {str(e)}")
            logger.warning("Falling back to exact match caching")
            self._semantic_enabled = False
            self._embedding_model = None

    def _compute_query_embedding(self, query: str) -> Optional[np.ndarray]:
        """
        Compute embedding for a query string.

        Args:
            query: Query string to embed

        Returns:
            Numpy array embedding or None if embeddings unavailable
        """
        if not self._semantic_enabled or not self._embedding_model:
            return None

        try:
            embedding = self._embedding_model.encode(query, convert_to_numpy=True)
            return embedding
        except Exception as e:
            logger.warning(f"Error computing query embedding: {str(e)}")
            return None

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Cosine similarity score (0-1)
        """
        dot_product = np.dot(vec1, vec2)
        norm_product = np.linalg.norm(vec1) * np.linalg.norm(vec2)

        if norm_product == 0:
            return 0.0

        return float(dot_product / norm_product)

    def _generate_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """
        Generate cache key from arguments.

        Args:
            prefix: Cache key prefix
            *args: Positional arguments to hash
            **kwargs: Keyword arguments to hash

        Returns:
            Cache key string
        """
        # Create a deterministic string from arguments
        key_parts = [str(arg) for arg in args]
        key_parts.extend([f"{k}:{v}" for k, v in sorted(kwargs.items())])
        key_string = ":".join(key_parts)

        # Hash for consistent length
        key_hash = hashlib.md5(key_string.encode()).hexdigest()

        return f"{prefix}:{key_hash}"

    def get_query_results(
        self,
        query: str,
        top_k: int = 5,
        search_type: str = "hybrid"
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get cached query results with semantic matching support.
        Attempts exact match first, then semantic similarity if enabled.

        Args:
            query: Search query
            top_k: Number of results
            search_type: Type of search (hybrid, text, vintern)

        Returns:
            Cached results or None if not found
        """
        if not self.enabled or not self.client:
            return None

        try:
            # Try exact match first (fastest)
            cache_key = self._generate_cache_key(
                "query",
                query,
                top_k=top_k,
                search_type=search_type
            )

            cached_data = self.client.get(cache_key)

            if cached_data:
                logger.debug(f"Cache HIT (exact) for query: {query[:50]}...")
                return json.loads(cached_data)

            # If semantic caching is enabled, try finding similar queries
            if self._semantic_enabled and self._embedding_model:
                return self._semantic_search(query, top_k, search_type)

            logger.debug(f"Cache MISS for query: {query[:50]}...")
            return None

        except (RedisError, json.JSONDecodeError) as e:
            logger.warning(f"Error retrieving from cache: {str(e)}")
            return None

    def _semantic_search(
        self,
        query: str,
        top_k: int,
        search_type: str
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Search for semantically similar cached queries.

        Args:
            query: Search query
            top_k: Number of results
            search_type: Type of search

        Returns:
            Cached results or None if no similar query found
        """
        try:
            # Compute embedding for the query
            query_embedding = self._compute_query_embedding(query)
            if query_embedding is None:
                return None

            # Get all cached query embeddings with same parameters
            embedding_pattern = f"query_emb:{top_k}:{search_type}:*"
            embedding_keys = self.client.keys(embedding_pattern)

            if not embedding_keys:
                logger.debug(f"No cached embeddings found for semantic search")
                return None

            best_similarity = 0.0
            best_cache_key = None

            # Find the most similar cached query
            for emb_key in embedding_keys:
                cached_embedding_data = self.client.get(emb_key)
                if not cached_embedding_data:
                    continue

                # Deserialize embedding from JSON list
                cached_embedding_list = json.loads(cached_embedding_data)
                cached_embedding = np.array(cached_embedding_list, dtype=np.float32)

                similarity = self._cosine_similarity(query_embedding, cached_embedding)

                if similarity > best_similarity:
                    best_similarity = similarity
                    # Extract original cache key from embedding key
                    best_cache_key = emb_key.decode('utf-8').replace('query_emb:', 'query:')

            # If we found a similar enough query, return its cached results
            if best_similarity >= self.semantic_threshold and best_cache_key:
                cached_data = self.client.get(best_cache_key)
                if cached_data:
                    logger.info(
                        f"Cache HIT (semantic, similarity={best_similarity:.3f}) "
                        f"for query: {query[:50]}..."
                    )
                    return json.loads(cached_data)

            logger.debug(
                f"Cache MISS (semantic, best similarity={best_similarity:.3f} < {self.semantic_threshold}) "
                f"for query: {query[:50]}..."
            )
            return None

        except Exception as e:
            logger.warning(f"Error in semantic search: {str(e)}")
            return None

    def set_query_results(
        self,
        query: str,
        results: List[Dict[str, Any]],
        top_k: int = 5,
        search_type: str = "hybrid",
        ttl: int = 3600
    ) -> bool:
        """
        Cache query results with optional semantic embedding for similarity matching.

        Args:
            query: Search query
            results: Results to cache
            top_k: Number of results
            search_type: Type of search
            ttl: Time to live in seconds (default 1 hour)

        Returns:
            True if cached successfully, False otherwise
        """
        if not self.enabled or not self.client:
            return False

        try:
            cache_key = self._generate_cache_key(
                "query",
                query,
                top_k=top_k,
                search_type=search_type
            )

            # Serialize results to JSON
            cached_data = json.dumps(results)

            # Set with TTL
            self.client.setex(cache_key, ttl, cached_data)

            # If semantic caching is enabled, also store the query embedding
            if self._semantic_enabled and self._embedding_model:
                query_embedding = self._compute_query_embedding(query)
                if query_embedding is not None:
                    # Store embedding with same key structure for easy lookup
                    embedding_key = cache_key.replace('query:', 'query_emb:')
                    # Convert numpy array to list for JSON serialization
                    embedding_list = query_embedding.astype(np.float32).tolist()
                    embedding_data = json.dumps(embedding_list)
                    self.client.setex(embedding_key, ttl, embedding_data)
                    logger.debug(f"Cached query results with semantic embedding for: {query[:50]}...")
                else:
                    logger.debug(f"Cached query results (no embedding) for: {query[:50]}...")
            else:
                logger.debug(f"Cached query results for: {query[:50]}...")

            return True

        except (RedisError, json.JSONEncodeError) as e:
            logger.warning(f"Error caching results: {str(e)}")
            return False

    def invalidate_query_cache(self, pattern: str = "query:*") -> int:
        """
        Invalidate cached queries and their embeddings matching pattern.

        Args:
            pattern: Cache key pattern to match

        Returns:
            Number of keys deleted
        """
        if not self.enabled or not self.client:
            return 0

        try:
            # Delete both query results and embeddings
            query_keys = self.client.keys(pattern)
            embedding_pattern = pattern.replace("query:", "query_emb:")
            embedding_keys = self.client.keys(embedding_pattern)

            all_keys = list(query_keys) + list(embedding_keys)

            if all_keys:
                deleted = self.client.delete(*all_keys)
                logger.info(f"Invalidated {deleted} cached entries (queries + embeddings)")
                return deleted
            return 0

        except RedisError as e:
            logger.warning(f"Error invalidating cache: {str(e)}")
            return 0

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        if not self.enabled or not self.client:
            return {
                "enabled": False,
                "status": "disabled"
            }

        try:
            info = self.client.info()

            # Count query and embedding keys
            query_keys = len(self.client.keys("query:*"))
            embedding_keys = len(self.client.keys("query_emb:*"))

            stats = {
                "enabled": True,
                "status": "connected",
                "host": self.host,
                "port": self.port,
                "db": self.db,
                "used_memory_human": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "total_keys": self.client.dbsize(),
                "query_cache_keys": query_keys,
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0),
                "hit_rate": self._calculate_hit_rate(
                    info.get("keyspace_hits", 0),
                    info.get("keyspace_misses", 0)
                )
            }

            # Add semantic caching stats if enabled
            if self._semantic_enabled:
                stats.update({
                    "semantic_cache_enabled": True,
                    "semantic_threshold": self.semantic_threshold,
                    "embedding_keys": embedding_keys,
                    "embedding_model": os.getenv('CACHE_EMBEDDING_MODEL', 'paraphrase-multilingual-MiniLM-L12-v2')
                })
            else:
                stats["semantic_cache_enabled"] = False

            return stats
        except RedisError as e:
            logger.warning(f"Error getting cache stats: {str(e)}")
            return {
                "enabled": self.enabled,
                "status": "error",
                "error": str(e)
            }

    def _calculate_hit_rate(self, hits: int, misses: int) -> float:
        """Calculate cache hit rate percentage."""
        total = hits + misses
        if total == 0:
            return 0.0
        return round((hits / total) * 100, 2)

    def clear_all(self) -> bool:
        """
        Clear all cache entries in current database.

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.client:
            return False

        try:
            self.client.flushdb()
            logger.info("Cache cleared successfully")
            return True
        except RedisError as e:
            logger.error(f"Error clearing cache: {str(e)}")
            return False

    def close(self):
        """Close Redis connection."""
        if self.client:
            try:
                self.client.close()
                logger.info("Redis connection closed")
            except RedisError as e:
                logger.warning(f"Error closing Redis connection: {str(e)}")


# Global cache instance
_redis_cache: Optional[RedisCache] = None


def get_redis_cache() -> RedisCache:
    """
    Get global Redis cache instance.

    Returns:
        RedisCache instance
    """
    global _redis_cache
    if _redis_cache is None:
        _redis_cache = RedisCache()
    return _redis_cache


def close_redis_cache():
    """Close global Redis cache connection."""
    global _redis_cache
    if _redis_cache:
        _redis_cache.close()
        _redis_cache = None


# Example usage and testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Test cache
    cache = RedisCache()

    # Test caching
    test_query = "What is machine learning?"
    test_results = [
        {"content": "ML is a subset of AI", "score": 0.95},
        {"content": "ML learns from data", "score": 0.87}
    ]

    # Set cache
    cache.set_query_results(test_query, test_results, top_k=5)

    # Get cache
    cached = cache.get_query_results(test_query, top_k=5)
    print(f"Cached results: {cached}")

    # Get stats
    stats = cache.get_cache_stats()
    print(f"Cache stats: {stats}")
