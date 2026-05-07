from typing import Any, Optional
from cacheout import Cache
from app.interfaces.memory_cache_interface import IMemoryCache


class CacheOutMemoryCache(IMemoryCache):
    """Memory cache implementation using cacheout library."""
    
    def __init__(self, maxsize: int = 1000):
        """
        Initialize cache with specified configuration.
        
        Args:
            maxsize: Maximum number of items to store in cache
        """
        self._cache = Cache(maxsize=maxsize, ttl=None)
    
    def get(self, key: str) -> Optional[Any]:
        """Retrieves cached value by key."""
        return self._cache.get(key)
    
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Stores value in cache with optional TTL."""
        self._cache.set(key, value, ttl=ttl_seconds)
    
    def remove(self, key: str) -> None:
        """Removes item from cache."""
        self._cache.delete(key)
    
    def clear(self) -> None:
        """Clears all cached items."""
        self._cache.clear()
    
    def has_key(self, key: str) -> bool:
        """Checks if key exists in cache."""
        return self._cache.has(key)
    
    def get_stats(self) -> dict:
        """
        Get cache statistics for monitoring.
        
        Returns:
            Dictionary with cache statistics
        """
        return {
            'size': len(self._cache),
            'maxsize': self._cache.maxsize,
            'hits': getattr(self._cache, 'hits', 0),
            'misses': getattr(self._cache, 'misses', 0)
        }