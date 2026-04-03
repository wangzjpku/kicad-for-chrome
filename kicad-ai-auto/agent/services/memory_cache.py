# -*- coding: utf-8 -*-
"""
简单的内存缓存模块

提供TTL（生存时间）缓存功能，用于优化API响应性能。
"""

import time
import hashlib
import json
import logging
from typing import Any, Optional, Dict, Callable
from functools import wraps
from threading import Lock

logger = logging.getLogger(__name__)


class MemoryCache:
    """
    线程安全的内存缓存实现。

    特性:
    - TTL (Time To Live) 支持
    - LRU 淘汰策略
    - 线程安全
    - 自动清理过期条目
    """

    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        """
        初始化缓存。

        Args:
            max_size: 最大缓存条目数
            default_ttl: 默认TTL（秒）
        """
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._access_order: list = []  # LRU 跟踪
        self._lock = Lock()
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._hits = 0
        self._misses = 0

    def _generate_key(self, func_name: str, *args, **kwargs) -> str:
        """生成缓存键"""
        key_data = {
            "func": func_name,
            "args": str(args),
            "kwargs": str(sorted(kwargs.items()))
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None

            entry = self._cache[key]

            # 检查是否过期
            if entry["expires_at"] < time.time():
                del self._cache[key]
                self._access_order.remove(key)
                self._misses += 1
                return None

            # 更新访问顺序（LRU）
            self._access_order.remove(key)
            self._access_order.append(key)
            self._hits += 1
            return entry["value"]

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存值"""
        with self._lock:
            # 如果已存在，先删除
            if key in self._cache:
                self._access_order.remove(key)

            # LRU 淘汰
            while len(self._cache) >= self.max_size:
                oldest_key = self._access_order.pop(0)
                del self._cache[oldest_key]

            # 添加新条目
            expires_at = time.time() + (ttl or self.default_ttl)
            self._cache[key] = {
                "value": value,
                "expires_at": expires_at,
                "created_at": time.time()
            }
            self._access_order.append(key)

    def delete(self, key: str) -> bool:
        """删除缓存条目"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._access_order.remove(key)
                return True
            return False

    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()

    def cleanup_expired(self) -> int:
        """清理过期条目，返回清理数量"""
        now = time.time()
        expired_keys = []

        with self._lock:
            for key, entry in self._cache.items():
                if entry["expires_at"] < now:
                    expired_keys.append(key)

            for key in expired_keys:
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)

        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

        return len(expired_keys)

    def stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = self._hits / total_requests * 100 if total_requests > 0 else 0

            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": f"{hit_rate:.1f}%",
                "total_requests": total_requests
            }


# 全局缓存实例
_cache_instances: Dict[str, MemoryCache] = {}


def get_cache(namespace: str = "default", max_size: int = 1000, ttl: int = 300) -> MemoryCache:
    """
    获取命名空间缓存实例。

    Args:
        namespace: 缓存命名空间
        max_size: 最大条目数
        ttl: 默认TTL

    Returns:
        MemoryCache 实例
    """
    if namespace not in _cache_instances:
        _cache_instances[namespace] = MemoryCache(max_size=max_size, default_ttl=ttl)
    return _cache_instances[namespace]


def cached(
    ttl: int = 300,
    namespace: str = "default",
    key_prefix: str = ""
):
    """
    缓存装饰器。

    Args:
        ttl: 缓存时间（秒）
        namespace: 缓存命名空间
        key_prefix: 键前缀

    Usage:
        @cached(ttl=60, namespace="api")
        async def get_data():
            return {"data": "value"}
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            cache = get_cache(namespace)
            key = f"{key_prefix}:{func.__name__}:{cache._generate_key(func.__name__, *args, **kwargs)}"

            # 尝试从缓存获取
            cached_value = cache.get(key)
            if cached_value is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_value

            # 执行函数
            result = await func(*args, **kwargs)

            # 存入缓存
            cache.set(key, result, ttl=ttl)
            logger.debug(f"Cache set for {func.__name__}")

            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            cache = get_cache(namespace)
            key = f"{key_prefix}:{func.__name__}:{cache._generate_key(func.__name__, *args, **kwargs)}"

            # 尝试从缓存获取
            cached_value = cache.get(key)
            if cached_value is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_value

            # 执行函数
            result = func(*args, **kwargs)

            # 存入缓存
            cache.set(key, result, ttl=ttl)
            logger.debug(f"Cache set for {func.__name__}")

            return result

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def clear_all_caches():
    """清空所有缓存"""
    for cache in _cache_instances.values():
        cache.clear()
    logger.info("All caches cleared")


def get_all_cache_stats() -> Dict[str, Dict[str, Any]]:
    """获取所有缓存的统计信息"""
    return {
        namespace: cache.stats()
        for namespace, cache in _cache_instances.items()
    }
