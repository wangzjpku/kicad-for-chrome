"""
Phase 12A-3: Cache Management API Routes

REST endpoints for cache inspection and management.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Dict, Optional

from services.cache_service import get_cache_service

router = APIRouter(prefix="/api/v1/cache", tags=["cache"])


class CacheSetRequest(BaseModel):
    namespace: str
    key: str
    value: Any
    ttl: Optional[float] = None


class CacheGetRequest(BaseModel):
    namespace: str
    key: str


class CacheDeleteRequest(BaseModel):
    namespace: str
    key: str


@router.get("/stats", summary="Cache statistics")
async def cache_stats():
    cache = get_cache_service()
    return cache.stats()


@router.get("/{namespace}/{key}", summary="Get cached value")
async def cache_get(namespace: str, key: str):
    cache = get_cache_service()
    value = cache.get(namespace, key)
    if value is None:
        return {"found": False}
    return {"found": True, "value": value}


@router.post("/set", summary="Set cached value")
async def cache_set(req: CacheSetRequest):
    cache = get_cache_service()
    cache.set(req.namespace, req.key, req.value, req.ttl)
    return {"status": "ok"}


@router.delete("/{namespace}/{key}", summary="Delete cached value")
async def cache_delete(namespace: str, key: str):
    cache = get_cache_service()
    deleted = cache.delete(namespace, key)
    return {"status": "ok" if deleted else "not_found"}


@router.post("/invalidate/{namespace}", summary="Invalidate all entries in namespace")
async def cache_invalidate(namespace: str):
    cache = get_cache_service()
    cache.invalidate_namespace(namespace)
    return {"status": "ok", "namespace": namespace}


@router.post("/clear", summary="Clear entire cache")
async def cache_clear():
    cache = get_cache_service()
    cache.invalidate_namespace("")
    return {"status": "ok"}
