"""
缓存管理模块
提供 LRU 缓存和内存缓存功能
"""

import time
import logging
from functools import lru_cache, wraps
from typing import Any, Callable, Optional, Dict, TypeVar, ParamSpec
from threading import Lock

logger = logging.getLogger(__name__)

# 全局缓存存储
_memory_cache: Dict[str, tuple[Any, float]] = {}
_cache_lock = Lock()

T = TypeVar('T')
P = ParamSpec('P')


def get_cache_config() -> dict:
    """获取缓存配置"""
    try:
        from config import get_settings
        settings = get_settings()
        return {
            "enabled": settings.cache_enabled,
            "ttl": settings.cache_ttl,
        }
    except ImportError:
        return {"enabled": True, "ttl": 3600}


def cached(
    func: Callable[P, T],
    maxsize: int = 128,
    ttl: Optional[int] = None
) -> Callable[P, T]:
    """
    带 TTL 的缓存装饰器

    Args:
        func: 要缓存的函数
        maxsize: LRU 缓存最大数量
        ttl: 缓存过期时间（秒），None 则使用全局配置
    """
    # 先应用 lru_cache
    lru_cached = lru_cache(maxsize=maxsize)(func)

    # 获取 TTL
    if ttl is None:
        config = get_cache_config()
        ttl = config.get("ttl", 3600)

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        config = get_cache_config()
        if not config.get("enabled", True):
            return lru_cached(*args, **kwargs)

        # 尝试从内存缓存获取
        cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"

        with _cache_lock:
            if cache_key in _memory_cache:
                value, timestamp = _memory_cache[cache_key]
                if time.time() - timestamp < ttl:
                    logger.debug(f"Cache hit: {func.__name__}")
                    return value
                else:
                    # 过期删除
                    del _memory_cache[cache_key]

        # 执行函数
        result = lru_cached(*args, **kwargs)

        # 存入缓存
        with _cache_lock:
            _memory_cache[cache_key] = (result, time.time())

        return result

    # 清除缓存方法
    wrapper.clear_cache = lambda: lru_cached.cache_clear()
    wrapper.cache_info = lru_cached.cache_info

    return wrapper


class CacheManager:
    """缓存管理器"""

    def __init__(self, default_ttl: int = 3600):
        self.default_ttl = default_ttl
        self._cache: Dict[str, tuple[Any, float]] = {}
        self._lock = Lock()

    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        with self._lock:
            if key in self._cache:
                value, timestamp = self._cache[key]
                if time.time() - timestamp < self.default_ttl:
                    return value
                else:
                    del self._cache[key]
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存"""
        if ttl is None:
            ttl = self.default_ttl

        with self._lock:
            self._cache[key] = (value, time.time() + ttl)

    def delete(self, key: str) -> None:
        """删除缓存"""
        with self._lock:
            self._cache.pop(key, None)

    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._cache.clear()

    def cleanup_expired(self) -> int:
        """清理过期缓存，返回清理数量"""
        count = 0
        with self._lock:
            now = time.time()
            expired_keys = [
                key for key, (_, timestamp) in self._cache.items()
                if timestamp < now
            ]
            for key in expired_keys:
                del self._cache[key]
                count += 1
        return count


# 全局缓存管理器实例
_cache_manager = CacheManager()


def get_cache_manager() -> CacheManager:
    """获取全局缓存管理器"""
    return _cache_manager


# 便捷的缓存装饰器（使用默认配置）
def simple_cache(ttl: int = 3600):
    """简单缓存装饰器，使用全局配置"""
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        return cached(func, ttl=ttl)
    return decorator


__all__ = [
    "cached",
    "simple_cache",
    "CacheManager",
    "get_cache_manager",
    "get_cache_config",
]
