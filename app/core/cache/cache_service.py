"""Caching layer providing JSON serialization, namespacing, and TTL management."""

from __future__ import annotations

import json
import logging
from typing import Any

from app.core.config import get_settings
from app.core.redis import get_redis_service

logger = logging.getLogger(__name__)


class CacheService:
    """Manages application-level caching backed by Redis or memory fallback."""

    def __init__(self, key_prefix: str = "aiopp:") -> None:
        self.key_prefix = key_prefix
        self.redis_service = get_redis_service()
        self.settings = get_settings()

    def _format_key(self, key: str) -> str:
        return f"{self.key_prefix}{key}"

    async def get(self, key: str) -> Any:
        """Retrieves and deserializes cached item."""
        try:
            client = await self.redis_service.get_client()
            val = await client.get(self._format_key(key))
            if val is not None:
                return json.loads(val)
            return None
        except Exception as exc:
            logger.debug("Cache read error for key %s: %s", key, exc)
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int | None = None,
    ) -> bool:
        """Serializes and persists value with TTL."""
        try:
            client = await self.redis_service.get_client()
            ttl = ttl_seconds if ttl_seconds is not None else self.settings.REDIS_CACHE_TTL
            serialized = json.dumps(value, default=str)
            return bool(await client.set(self._format_key(key), serialized, ex=ttl))
        except Exception as exc:
            logger.debug("Cache write error for key %s: %s", key, exc)
            return False

    async def delete(self, key: str) -> bool:
        """Removes cached item."""
        try:
            client = await self.redis_service.get_client()
            return bool(await client.delete(self._format_key(key)))
        except Exception as exc:
            logger.debug("Cache delete error for key %s: %s", key, exc)
            return False

    async def exists(self, key: str) -> bool:
        """Checks presence of key."""
        try:
            client = await self.redis_service.get_client()
            return bool(await client.exists(self._format_key(key)))
        except Exception:
            return False


_default_cache_service: CacheService | None = None


def get_cache_service() -> CacheService:
    global _default_cache_service
    if _default_cache_service is None:
        _default_cache_service = CacheService()
    return _default_cache_service
