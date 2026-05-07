from typing import Protocol, Any, Optional


class IMemoryCache(Protocol):
    """Interface for memory caching operations."""
    
    def get(self, key: str) -> Optional[Any]:
        """
        Retrieves cached value by key.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value if found, None otherwise
        """
        ...
    
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """
        Stores value in cache with optional TTL.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Time to live in seconds, None for no expiration
        """
        ...
    
    def remove(self, key: str) -> None:
        """
        Removes item from cache.
        
        Args:
            key: Cache key to remove
        """
        ...
    
    def clear(self) -> None:
        """Clears all cached items."""
        ...
    
    def has_key(self, key: str) -> bool:
        """
        Checks if key exists in cache.
        
        Args:
            key: Cache key to check
            
        Returns:
            True if key exists, False otherwise
        """
        ...