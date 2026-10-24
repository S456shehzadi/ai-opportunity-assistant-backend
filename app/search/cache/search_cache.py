import hashlib
import json
import logging
import time
from abc import ABC, abstractmethod
from typing import Any

from app.core.config import Settings, get_settings
from app.search.models.search_result import NormalizedSearchResult

logger = logging.getLogger(__name__)


class SearchCache(ABC):
    """Abstract interface for caching search results."""

    @abstractmethod
    async def get(
        self, provider: str, query: str, max_results: int
    ) -> list[NormalizedSearchResult] | None:
        pass

    @abstractmethod
    async def set(
        self,
        provider: str,
        query: str,
        max_results: int,
        results: list[NormalizedSearchResult],
        ttl_seconds: int = 3600,
    ) -> None:
        pass

    @abstractmethod
    async def clear(self) -> None:
        pass

    @staticmethod
    def build_cache_key(provider: str, query: str, max_results: int) -> str:
        key_raw = f"{provider.lower()}:{query.strip().lower()}:{max_results}"
        return f"search_cache:{hashlib.sha256(key_raw.encode()).hexdigest()}"


class InMemorySearchCache(SearchCache):
    """Thread-safe in-memory search cache with TTL eviction."""

    def __init__(self) -> None:
        self._cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}

    async def get(
        self, provider: str, query: str, max_results: int
    ) -> list[NormalizedSearchResult] | None:
        key = self.build_cache_key(provider, query, max_results)
        if key not in self._cache:
            return None

        expiry, serialized_items = self._cache[key]
        if time.monotonic() > expiry:
            del self._cache[key]
            return None

        try:
            return [NormalizedSearchResult.model_validate(item) for item in serialized_items]
        except Exception as exc:
            logger.warning("Cache deserialization error: %s", exc)
            return None

    async def set(
        self,
        provider: str,
        query: str,
        max_results: int,
        results: list[NormalizedSearchResult],
        ttl_seconds: int = 3600,
    ) -> None:
        key = self.build_cache_key(provider, query, max_results)
        expiry = time.monotonic() + ttl_seconds
        serialized = [item.model_dump(mode="json") for item in results]
        self._cache[key] = (expiry, serialized)

    async def clear(self) -> None:
        self._cache.clear()


class RedisSearchCache(SearchCache):
    """Redis-backed search cache for production deployments."""

    def __init__(self, redis_url: str) -> None:
        self.redis_url = redis_url
        self._redis_client = None

    async def _get_client(self) -> Any:
        if self._redis_client is None:
            try:
                import redis.asyncio as aioredis

                self._redis_client = aioredis.from_url(
                    self.redis_url, encoding="utf-8", decode_responses=True
                )
            except Exception as exc:
                logger.warning("Failed to connect to Redis: %s", exc)
                return None
        return self._redis_client

    async def get(
        self, provider: str, query: str, max_results: int
    ) -> list[NormalizedSearchResult] | None:
        client = await self._get_client()
        if not client:
            return None

        key = self.build_cache_key(provider, query, max_results)
        try:
            cached_str = await client.get(key)
            if not cached_str:
                return None
            items_raw = json.loads(cached_str)
            return [NormalizedSearchResult.model_validate(i) for i in items_raw]
        except Exception as exc:
            logger.warning("Redis search cache get error: %s", exc)
            return None

    async def set(
        self,
        provider: str,
        query: str,
        max_results: int,
        results: list[NormalizedSearchResult],
        ttl_seconds: int = 3600,
    ) -> None:
        client = await self._get_client()
        if not client:
            return

        key = self.build_cache_key(provider, query, max_results)
        try:
            serialized = json.dumps([item.model_dump(mode="json") for item in results])
            await client.setex(key, ttl_seconds, serialized)
        except Exception as exc:
            logger.warning("Redis search cache set error: %s", exc)

    async def clear(self) -> None:
        client = await self._get_client()
        if client:
            try:
                keys = await client.keys("search_cache:*")
                if keys:
                    await client.delete(*keys)
            except Exception as exc:
                logger.warning("Redis search cache clear error: %s", exc)


def get_search_cache(settings: Settings | None = None) -> SearchCache:
    """Returns the search cache instance (InMemory by default, Redis if configured)."""
    cfg = settings or get_settings()
    # Default to InMemory for reliability without Redis daemon
    if cfg.is_production and cfg.REDIS_URL:
        return RedisSearchCache(cfg.REDIS_URL)
    return InMemorySearchCache()
