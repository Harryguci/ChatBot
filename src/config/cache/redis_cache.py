"""
Redis caching module for query results.
Provides fast in-memory caching to reduce database load and improve response times.
"""

import os
import json
import hashlib
import logging
from typing import Optional, Any, List, Dict
from dotenv import load_dotenv
import redis
from redis.exceptions import RedisError

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)


class RedisCache:
    """Redis cache manager for chatbot query results."""

    def __init__(
        self,
        host: str = None,
        port: int = None,
        db: int = None,
        password: str = None,
        decode_responses: bool = True,
        enabled: bool = True
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
        """
        self.enabled = enabled and os.getenv('REDIS_ENABLED', 'true').lower() == 'true'
        self.host = host or os.getenv('REDIS_HOST', 'localhost')
        self.port = port or int(os.getenv('REDIS_PORT', '6379'))
        self.db = db or int(os.getenv('REDIS_DB', '0'))
        self.password = password or os.getenv('REDIS_PASSWORD', None)
        self.decode_responses = decode_responses
        self.client: Optional[redis.Redis] = None

        if self.enabled:
            self._initialize_client()

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
        Get cached query results.

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
            cache_key = self._generate_cache_key(
                "query",
                query,
                top_k=top_k,
                search_type=search_type
            )

            cached_data = self.client.get(cache_key)

            if cached_data:
                logger.debug(f"Cache HIT for query: {query[:50]}...")
                return json.loads(cached_data)
            else:
                logger.debug(f"Cache MISS for query: {query[:50]}...")
                return None

        except (RedisError, json.JSONDecodeError) as e:
            logger.warning(f"Error retrieving from cache: {str(e)}")
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
        Cache query results.

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
            logger.debug(f"Cached query results for: {query[:50]}...")
            return True

        except (RedisError, json.JSONEncodeError) as e:
            logger.warning(f"Error caching results: {str(e)}")
            return False

    def invalidate_query_cache(self, pattern: str = "query:*") -> int:
        """
        Invalidate cached queries matching pattern.

        Args:
            pattern: Cache key pattern to match

        Returns:
            Number of keys deleted
        """
        if not self.enabled or not self.client:
            return 0

        try:
            keys = self.client.keys(pattern)
            if keys:
                deleted = self.client.delete(*keys)
                logger.info(f"Invalidated {deleted} cached queries")
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
            return {
                "enabled": True,
                "status": "connected",
                "host": self.host,
                "port": self.port,
                "db": self.db,
                "used_memory_human": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "total_keys": self.client.dbsize(),
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0),
                "hit_rate": self._calculate_hit_rate(
                    info.get("keyspace_hits", 0),
                    info.get("keyspace_misses", 0)
                )
            }
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
