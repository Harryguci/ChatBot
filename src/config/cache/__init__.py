"""Cache configuration module."""
from .redis_cache import RedisCache, get_redis_cache

__all__ = ['RedisCache', 'get_redis_cache']
