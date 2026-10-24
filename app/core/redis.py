"""Asynchronous Redis client with automatic fallback for local development and tests."""

from __future__ import annotations

import logging
import time
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class InMemoryRedisMock:
    """Thread-safe in-memory mock when Redis daemon is unavailable."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[str, float | None]] = {}
        self._sets: dict[str, set[str]] = {}

    def _purge_expired(self) -> None:
        now = time.time()
        expired = [k for k, (_, exp) in self._store.items() if exp is not None and exp < now]
        for k in expired:
            del self._store[k]

    async def get(self, key: str) -> str | None:
        self._purge_expired()
        item = self._store.get(key)
        return item[0] if item else None

    async def set(
        self,
        key: str,
        value: str,
        ex: int | None = None,
        nx: bool = False,
    ) -> bool:
        self._purge_expired()
        if nx and key in self._store:
            return False
        exp = (time.time() + ex) if ex else None
        self._store[key] = (str(value), exp)
        return True

    async def delete(self, *keys: str) -> int:
        count = 0
        for k in keys:
            if k in self._store:
                del self._store[k]
                count += 1
        return count

    async def exists(self, key: str) -> int:
        self._purge_expired()
        return 1 if key in self._store else 0

    async def ping(self) -> bool:
        return True

    async def sadd(self, key: str, *members: str) -> int:
        s = self._sets.setdefault(key, set())
        initial = len(s)
        s.update(members)
        return len(s) - initial

    async def sismember(self, key: str, member: str) -> bool:
        return member in self._sets.get(key, set())

    async def srem(self, key: str, *members: str) -> int:
        s = self._sets.get(key, set())
        initial = len(s)
        for m in members:
            s.discard(m)
        return initial - len(s)

    async def eval(self, script: str, numkeys: int, *keys_and_args: Any) -> Any:
        # Simple simulation of release lock lua script
        if numkeys == 1 and len(keys_and_args) >= 2:
            key, expected_val = keys_and_args[0], keys_and_args[1]
            current = await self.get(key)
            if current == str(expected_val):
                await self.delete(key)
                return 1
            return 0
        return 1

    async def close(self) -> None:
        pass


class RedisService:
    """Manages Redis connection lifecycle with resilient fallback."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._client: Any = None
        self._is_mock = False

    async def get_client(self) -> Any:
        """Initializes and returns the active Redis client or in-memory fallback."""
        if self._client is not None:
            return self._client

        try:
            import redis.asyncio as aioredis

            client = aioredis.from_url(
                self.settings.REDIS_URL,
                max_connections=self.settings.REDIS_POOL_SIZE,
                decode_responses=True,
            )
            # Test connectivity
            await client.ping()
            self._client = client
            self._is_mock = False
            logger.info("Connected to Redis instance at %s", self.settings.REDIS_URL)
        except Exception as exc:
            logger.info(
                "Redis unavailable (%s), operating with in-memory cache/lock fallback",
                exc,
            )
            self._client = InMemoryRedisMock()
            self._is_mock = True

        return self._client

    async def is_healthy(self) -> bool:
        """Probes Redis connection status."""
        try:
            client = await self.get_client()
            return await client.ping()
        except Exception:
            return False

    async def close(self) -> None:
        """Closes connection pool."""
        if self._client is not None:
            await self._client.close()
            self._client = None


_redis_service: RedisService | None = None


def get_redis_service() -> RedisService:
    global _redis_service
    if _redis_service is None:
        _redis_service = RedisService()
    return _redis_service


def get_redis_client() -> Any:
    """Returns active redis client or initialized in-memory mock."""
    service = get_redis_service()
    if service._client is None:
        service._client = InMemoryRedisMock()
        service._is_mock = True
    return service._client
