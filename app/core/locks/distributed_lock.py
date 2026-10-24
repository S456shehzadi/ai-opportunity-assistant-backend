"""Redis-backed distributed locking with atomic Lua release and expiration."""

from __future__ import annotations

import asyncio
import logging
import uuid

from app.core.redis import get_redis_service

logger = logging.getLogger(__name__)

# Atomic release script: only deletes the key if its current value matches the caller's owner token
LUA_RELEASE_LOCK = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""


class DistributedLock:
    """Distributed mutex preventing duplicate background job execution across worker replicas."""

    def __init__(
        self,
        name: str,
        ttl_seconds: int = 60,
        acquire_timeout: float = 5.0,
    ) -> None:
        self.key = f"lock:{name}"
        self.ttl = ttl_seconds
        self.acquire_timeout = acquire_timeout
        self.token = str(uuid.uuid4())
        self.redis_service = get_redis_service()
        self.acquired = False

    async def acquire(self) -> bool:
        """Attempts to acquire lock with retry until timeout."""
        client = await self.redis_service.get_client()
        deadline = asyncio.get_event_loop().time() + self.acquire_timeout

        while asyncio.get_event_loop().time() < deadline:
            success = await client.set(self.key, self.token, ex=self.ttl, nx=True)
            if success:
                self.acquired = True
                return True
            await asyncio.sleep(0.1)

        return False

    async def release(self) -> bool:
        """Atomically releases lock if caller is still the current owner."""
        if not self.acquired:
            return False

        try:
            client = await self.redis_service.get_client()
            res = await client.eval(LUA_RELEASE_LOCK, 1, self.key, self.token)
            self.acquired = False
            return bool(res == 1)
        except Exception as exc:
            logger.warning("Error releasing lock %s: %s", self.key, exc)
            self.acquired = False
            return False

    async def __aenter__(self) -> bool:
        return await self.acquire()

    async def __aexit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        await self.release()
