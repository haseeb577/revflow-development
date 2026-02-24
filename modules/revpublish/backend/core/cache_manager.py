"""
RevPublish Cache Manager - Production-Ready Caching Helper
Supports both Redis and in-memory fallback with TTL, namespacing, and serialization

Usage:
    from core.cache_manager import get_cache
    
    cache = get_cache()
    
    # Basic operations
    cache.set("site_config", {"domain": "example.com"}, ttl=3600)
    config = cache.get("site_config")
    cache.delete("site_config")
    
    # With namespacing
    cache.set("dallasplumber.com", content, namespace="generated_content", ttl=86400)
    content = cache.get("dallasplumber.com", namespace="generated_content")
    
    # Bulk operations
    cache.set_many({"site1": data1, "site2": data2}, ttl=3600)
    results = cache.get_many(["site1", "site2"])
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Unified cache manager with Redis primary and in-memory fallback
    """
    
    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0,
        default_ttl: int = 3600,
        namespace_separator: str = ":"
    ):
        """
        Initialize cache manager
        
        Args:
            redis_host: Redis server host
            redis_port: Redis server port
            redis_db: Redis database number (0-4 available)
            default_ttl: Default time-to-live in seconds (1 hour)
            namespace_separator: Character to separate namespace from key
        """
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_db = redis_db
        self.default_ttl = default_ttl
        self.namespace_separator = namespace_separator
        
        # Try to connect to Redis
        self.redis_client = None
        self.use_redis = False
        self._connect_redis()
        
        # In-memory fallback
        self._memory_cache: Dict[str, tuple] = {}  # {key: (value, expiry_timestamp)}
        
    def _connect_redis(self):
        """Attempt to connect to Redis"""
        try:
            import redis
            self.redis_client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                db=self.redis_db,
                decode_responses=True,
                socket_connect_timeout=2
            )
            # Test connection
            self.redis_client.ping()
            self.use_redis = True
            logger.info(f"✅ Redis connected: {self.redis_host}:{self.redis_port} DB{self.redis_db}")
        except Exception as e:
            logger.warning(f"⚠️  Redis unavailable, using in-memory cache: {e}")
            self.use_redis = False
    
    def _make_key(self, key: str, namespace: Optional[str] = None) -> str:
        """Create namespaced key"""
        if namespace:
            return f"{namespace}{self.namespace_separator}{key}"
        return key
    
    def _serialize(self, value: Any) -> str:
        """Serialize value to JSON string"""
        try:
            return json.dumps(value)
        except (TypeError, ValueError) as e:
            logger.error(f"Serialization failed for {type(value)}: {e}")
            return json.dumps(str(value))
    
    def _deserialize(self, value: str) -> Any:
        """Deserialize JSON string to value"""
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return value
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        namespace: Optional[str] = None
    ) -> bool:
        """
        Set a cache value
        
        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time-to-live in seconds (None = default_ttl)
            namespace: Optional namespace for key
            
        Returns:
            True if successful, False otherwise
        """
        full_key = self._make_key(key, namespace)
        ttl = ttl if ttl is not None else self.default_ttl
        serialized_value = self._serialize(value)
        
        try:
            if self.use_redis:
                self.redis_client.setex(full_key, ttl, serialized_value)
            else:
                expiry = time.time() + ttl
                self._memory_cache[full_key] = (serialized_value, expiry)
            
            logger.debug(f"Cache SET: {full_key} (TTL: {ttl}s)")
            return True
            
        except Exception as e:
            logger.error(f"Cache SET failed for {full_key}: {e}")
            return False
    
    def get(self, key: str, namespace: Optional[str] = None, default: Any = None) -> Any:
        """
        Get a cache value
        
        Args:
            key: Cache key
            namespace: Optional namespace for key
            default: Default value if key not found
            
        Returns:
            Cached value or default
        """
        full_key = self._make_key(key, namespace)
        
        try:
            if self.use_redis:
                value = self.redis_client.get(full_key)
                if value is None:
                    logger.debug(f"Cache MISS: {full_key}")
                    return default
                logger.debug(f"Cache HIT: {full_key}")
                return self._deserialize(value)
            else:
                if full_key in self._memory_cache:
                    value, expiry = self._memory_cache[full_key]
                    # Check expiry
                    if time.time() < expiry:
                        logger.debug(f"Cache HIT (memory): {full_key}")
                        return self._deserialize(value)
                    else:
                        # Expired
                        del self._memory_cache[full_key]
                        logger.debug(f"Cache EXPIRED: {full_key}")
                        return default
                logger.debug(f"Cache MISS (memory): {full_key}")
                return default
                
        except Exception as e:
            logger.error(f"Cache GET failed for {full_key}: {e}")
            return default
    
    def delete(self, key: str, namespace: Optional[str] = None) -> bool:
        """
        Delete a cache value
        
        Args:
            key: Cache key
            namespace: Optional namespace for key
            
        Returns:
            True if deleted, False otherwise
        """
        full_key = self._make_key(key, namespace)
        
        try:
            if self.use_redis:
                deleted = self.redis_client.delete(full_key)
                logger.debug(f"Cache DELETE: {full_key} (deleted: {deleted})")
                return deleted > 0
            else:
                if full_key in self._memory_cache:
                    del self._memory_cache[full_key]
                    logger.debug(f"Cache DELETE (memory): {full_key}")
                    return True
                return False
                
        except Exception as e:
            logger.error(f"Cache DELETE failed for {full_key}: {e}")
            return False
    
    def exists(self, key: str, namespace: Optional[str] = None) -> bool:
        """
        Check if key exists in cache
        
        Args:
            key: Cache key
            namespace: Optional namespace for key
            
        Returns:
            True if exists, False otherwise
        """
        full_key = self._make_key(key, namespace)
        
        try:
            if self.use_redis:
                return self.redis_client.exists(full_key) > 0
            else:
                if full_key in self._memory_cache:
                    _, expiry = self._memory_cache[full_key]
                    if time.time() < expiry:
                        return True
                    else:
                        del self._memory_cache[full_key]
                return False
                
        except Exception as e:
            logger.error(f"Cache EXISTS check failed for {full_key}: {e}")
            return False
    
    def clear(self, namespace: Optional[str] = None) -> int:
        """
        Clear cache (all keys or namespace)
        
        Args:
            namespace: If provided, only clear keys in this namespace
            
        Returns:
            Number of keys deleted
        """
        try:
            if self.use_redis:
                if namespace:
                    # Delete all keys with namespace prefix
                    pattern = f"{namespace}{self.namespace_separator}*"
                    keys = self.redis_client.keys(pattern)
                    if keys:
                        deleted = self.redis_client.delete(*keys)
                        logger.info(f"Cache CLEAR: {namespace} ({deleted} keys)")
                        return deleted
                    return 0
                else:
                    # Clear entire database
                    self.redis_client.flushdb()
                    logger.info("Cache CLEAR: ALL")
                    return -1  # Unknown count
            else:
                if namespace:
                    prefix = f"{namespace}{self.namespace_separator}"
                    keys_to_delete = [k for k in self._memory_cache.keys() if k.startswith(prefix)]
                    for key in keys_to_delete:
                        del self._memory_cache[key]
                    logger.info(f"Cache CLEAR (memory): {namespace} ({len(keys_to_delete)} keys)")
                    return len(keys_to_delete)
                else:
                    count = len(self._memory_cache)
                    self._memory_cache.clear()
                    logger.info(f"Cache CLEAR (memory): ALL ({count} keys)")
                    return count
                    
        except Exception as e:
            logger.error(f"Cache CLEAR failed: {e}")
            return 0
    
    def set_many(
        self,
        mapping: Dict[str, Any],
        ttl: Optional[int] = None,
        namespace: Optional[str] = None
    ) -> int:
        """
        Set multiple cache values at once
        
        Args:
            mapping: Dictionary of {key: value}
            ttl: Time-to-live in seconds
            namespace: Optional namespace for all keys
            
        Returns:
            Number of keys successfully set
        """
        success_count = 0
        for key, value in mapping.items():
            if self.set(key, value, ttl=ttl, namespace=namespace):
                success_count += 1
        
        logger.debug(f"Cache SET_MANY: {success_count}/{len(mapping)} keys")
        return success_count
    
    def get_many(
        self,
        keys: List[str],
        namespace: Optional[str] = None,
        default: Any = None
    ) -> Dict[str, Any]:
        """
        Get multiple cache values at once
        
        Args:
            keys: List of cache keys
            namespace: Optional namespace for all keys
            default: Default value for missing keys
            
        Returns:
            Dictionary of {key: value}
        """
        results = {}
        for key in keys:
            results[key] = self.get(key, namespace=namespace, default=default)
        
        hit_count = sum(1 for v in results.values() if v != default)
        logger.debug(f"Cache GET_MANY: {hit_count}/{len(keys)} hits")
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics
        
        Returns:
            Dictionary with cache stats
        """
        stats = {
            "backend": "redis" if self.use_redis else "memory",
            "redis_available": self.use_redis
        }
        
        try:
            if self.use_redis:
                info = self.redis_client.info("stats")
                stats.update({
                    "total_keys": self.redis_client.dbsize(),
                    "hits": info.get("keyspace_hits", 0),
                    "misses": info.get("keyspace_misses", 0),
                    "hit_rate": self._calculate_hit_rate(
                        info.get("keyspace_hits", 0),
                        info.get("keyspace_misses", 0)
                    )
                })
            else:
                # Clean up expired entries first
                self._cleanup_expired()
                stats.update({
                    "total_keys": len(self._memory_cache),
                    "backend_note": "In-memory fallback (Redis unavailable)"
                })
                
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            stats["error"] = str(e)
        
        return stats
    
    def _calculate_hit_rate(self, hits: int, misses: int) -> float:
        """Calculate cache hit rate percentage"""
        total = hits + misses
        if total == 0:
            return 0.0
        return round((hits / total) * 100, 2)
    
    def _cleanup_expired(self):
        """Clean up expired entries from in-memory cache"""
        if not self.use_redis:
            current_time = time.time()
            expired_keys = [
                k for k, (_, expiry) in self._memory_cache.items()
                if current_time >= expiry
            ]
            for key in expired_keys:
                del self._memory_cache[key]
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired entries")


# Singleton instance
_cache_instance = None


def get_cache(
    redis_host: str = "localhost",
    redis_port: int = 6379,
    redis_db: int = 0,
    default_ttl: int = 3600
) -> CacheManager:
    """
    Get or create cache manager singleton
    
    Args:
        redis_host: Redis server host
        redis_port: Redis server port
        redis_db: Redis database number (0-4)
        default_ttl: Default TTL in seconds
        
    Returns:
        CacheManager instance
    """
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = CacheManager(
            redis_host=redis_host,
            redis_port=redis_port,
            redis_db=redis_db,
            default_ttl=default_ttl
        )
    return _cache_instance


# Convenience functions for direct use
def set_cache(key: str, value: Any, ttl: int = 3600, namespace: str = None) -> bool:
    """Quick cache set"""
    return get_cache().set(key, value, ttl=ttl, namespace=namespace)


def get_cache_value(key: str, namespace: str = None, default: Any = None) -> Any:
    """Quick cache get"""
    return get_cache().get(key, namespace=namespace, default=default)


def clear_cache(namespace: str = None) -> int:
    """Quick cache clear"""
    return get_cache().clear(namespace=namespace)
