"""
Redis Cache Service with in-memory fallback.

Provides caching for:
- API responses (BOM lookups, component searches)
- DRC results
- PCB layout snapshots
- Component library data

Falls back to in-memory dict when Redis is unavailable.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class CacheEntry:
    """A single cache entry with TTL support."""

    __slots__ = ("value", "expires_at")

    def __init__(self, value: Any, ttl: Optional[float] = None):
        self.value = value
        self.expires_at = time.time() + ttl if ttl else None

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at


class InMemoryCache:
    """Thread-safe in-memory cache with TTL support."""

    def __init__(self, max_size: int = 1000):
        self._store: Dict[str, CacheEntry] = {}
        self._max_size = max_size
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if entry is None:
            self._misses += 1
            return None
        if entry.is_expired():
            del self._store[key]
            self._misses += 1
            return None
        self._hits += 1
        return entry.value

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        if len(self._store) >= self._max_size and key not in self._store:
            self._evict()
        self._store[key] = CacheEntry(value, ttl)

    def delete(self, key: str) -> bool:
        return self._store.pop(key, None) is not None

    def clear(self) -> None:
        self._store.clear()

    def exists(self, key: str) -> bool:
        entry = self._store.get(key)
        if entry is None:
            return False
        if entry.is_expired():
            del self._store[key]
            return False
        return True

    def stats(self) -> Dict[str, Any]:
        total = self._hits + self._misses
        return {
            "size": len(self._store),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / total if total > 0 else 0.0,
        }

    def _evict(self) -> None:
        """Evict expired entries, then oldest entries."""
        now = time.time()
        expired_keys = [
            k for k, v in self._store.items()
            if v.expires_at and v.expires_at < now
        ]
        for k in expired_keys:
            del self._store[k]
        if len(self._store) >= self._max_size:
            # Remove oldest 10%
            keys = list(self._store.keys())
            for k in keys[: max(1, len(keys) // 10)]:
                del self._store[k]


class RedisCache:
    """Redis-based cache with connection pooling."""

    def __init__(self, url: str = "redis://localhost:6379"):
        self._url = url
        self._redis = None
        self._hits = 0
        self._misses = 0
        try:
            import redis
            self._redis = redis.from_url(url, decode_responses=True)
            self._redis.ping()
            logger.info(f"Redis cache connected: {url}")
        except ImportError:
            logger.info("redis package not installed, falling back to in-memory cache")
            self._fallback = InMemoryCache()
        except Exception as e:
            logger.warning(f"Redis connection failed ({e}), falling back to in-memory cache")
            self._fallback = InMemoryCache()

    @property
    def _use_redis(self) -> bool:
        return self._redis is not None

    def get(self, key: str) -> Optional[Any]:
        if self._use_redis:
            try:
                raw = self._redis.get(key)
                if raw is None:
                    self._misses += 1
                    return None
                self._hits += 1
                return json.loads(raw)
            except Exception:
                self._misses += 1
                return None
        return self._fallback.get(key)

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        if self._use_redis:
            try:
                serialized = json.dumps(value, default=str)
                if ttl:
                    self._redis.setex(key, int(ttl), serialized)
                else:
                    self._redis.set(key, serialized)
            except Exception as e:
                logger.warning(f"Redis set failed: {e}")
        else:
            self._fallback.set(key, value, ttl)

    def delete(self, key: str) -> bool:
        if self._use_redis:
            try:
                return bool(self._redis.delete(key))
            except Exception:
                return False
        return self._fallback.delete(key)

    def clear(self) -> None:
        if self._use_redis:
            try:
                self._redis.flushdb()
            except Exception:
                pass
        else:
            self._fallback.clear()

    def exists(self, key: str) -> bool:
        if self._use_redis:
            try:
                return bool(self._redis.exists(key))
            except Exception:
                return False
        return self._fallback.exists(key)

    def stats(self) -> Dict[str, Any]:
        if self._use_redis:
            total = self._hits + self._misses
            try:
                info = self._redis.info("stats")
                return {
                    "backend": "redis",
                    "url": self._url,
                    "keys": self._redis.dbsize(),
                    "hits": self._hits,
                    "misses": self._misses,
                    "hit_rate": self._hits / total if total > 0 else 0.0,
                    "redis_used_memory": info.get("used_memory_human", "?"),
                }
            except Exception:
                return {"backend": "redis", "status": "error"}
        else:
            stats = self._fallback.stats()
            stats["backend"] = "in_memory"
            return stats


class CacheService:
    """
    Unified cache service with namespace support.

    Namespaces prevent key collisions between different data types:
    - bom: BOM lookup results
    - component: Component search results
    - drc: DRC analysis results
    - layout: Layout snapshots
    - api: General API responses
    """

    DEFAULT_TTLS = {
        "bom": 3600,          # 1 hour
        "component": 1800,    # 30 minutes
        "drc": 600,           # 10 minutes
        "layout": 300,        # 5 minutes
        "api": 600,           # 10 minutes
        "spatial": 180,       # 3 minutes
        "template": 3600,     # 1 hour
    }

    def __init__(self, redis_url: Optional[str] = None):
        url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self._cache = RedisCache(url)

    @staticmethod
    def _make_key(namespace: str, key: str) -> str:
        return f"kicad:{namespace}:{key}"

    @staticmethod
    def _hash_key(data: Any) -> str:
        raw = json.dumps(data, sort_keys=True, default=str)
        return hashlib.md5(raw.encode()).hexdigest()

    def get(self, namespace: str, key: str) -> Optional[Any]:
        return self._cache.get(self._make_key(namespace, key))

    def set(
        self,
        namespace: str,
        key: str,
        value: Any,
        ttl: Optional[float] = None,
    ) -> None:
        effective_ttl = ttl or self.DEFAULT_TTLS.get(namespace, 600)
        self._cache.set(self._make_key(namespace, key), value, effective_ttl)

    def delete(self, namespace: str, key: str) -> bool:
        return self._cache.delete(self._make_key(namespace, key))

    def get_or_compute(
        self,
        namespace: str,
        key: str,
        compute_fn,
        ttl: Optional[float] = None,
    ) -> Any:
        """
        Get from cache or compute and cache the result.
        """
        cached = self.get(namespace, key)
        if cached is not None:
            return cached
        result = compute_fn()
        self.set(namespace, key, result, ttl)
        return result

    def invalidate_namespace(self, namespace: str) -> None:
        """Clear all entries in a namespace (only works for in-memory)."""
        self._cache.clear()

    def cache_hashed(
        self,
        namespace: str,
        params: Any,
        value: Any,
        ttl: Optional[float] = None,
    ) -> str:
        """Cache a value with auto-generated hash key from params."""
        key = self._hash_key(params)
        self.set(namespace, key, value, ttl)
        return key

    def get_hashed(self, namespace: str, params: Any) -> Optional[Any]:
        """Retrieve a cached value by hashing the params."""
        key = self._hash_key(params)
        return self.get(namespace, key)

    def stats(self) -> Dict[str, Any]:
        return self._cache.stats()


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_cache_service: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service
