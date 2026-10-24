"""Tiered rate limiting middleware backed by Redis."""

from __future__ import annotations

import logging
import time

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import get_settings
from app.core.redis import get_redis_service

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Enforces configurable endpoint-specific request rate limits."""

    def __init__(self, app: object) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self.settings = get_settings()
        self.redis_service = get_redis_service()
        self._memory_buckets: dict[str, list[float]] = {}

    def _get_limit_for_path(self, path: str) -> int:
        """Determines tiered rate limit threshold according to endpoint cost."""
        if "/auth" in path:
            return self.settings.RATE_LIMIT_AUTH_PER_MIN
        if "/search" in path:
            return self.settings.RATE_LIMIT_SEARCH_PER_MIN
        if "/assistant" in path:
            return self.settings.RATE_LIMIT_ASSISTANT_PER_MIN
        if "/training" in path or "/models" in path:
            return self.settings.RATE_LIMIT_ADMIN_PER_MIN
        return self.settings.RATE_LIMIT_DEFAULT_PER_MIN

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not self.settings.RATE_LIMIT_ENABLED or request.url.path in (
            "/health",
            "/live",
            "/ready",
            "/metrics",
        ):
            return await call_next(request)

        # Identify client by IP or user authorization
        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path
        limit = self._get_limit_for_path(path)
        now = time.time()
        window_start = now - 60.0

        key = f"ratelimit:{client_ip}:{path.split('/')[3] if len(path.split('/')) > 3 else 'root'}"

        # Sliding window check
        try:
            client = await self.redis_service.get_client()
            if hasattr(client, "zremrangebyscore"):
                # Redis sorted set sliding window
                pipe = client.pipeline()
                pipe.zremrangebyscore(key, 0, window_start)
                pipe.zcard(key)
                pipe.zadd(key, {str(now): now})
                pipe.expire(key, 60)
                _, count, _, _ = await pipe.execute()
            else:
                timestamps = self._memory_buckets.setdefault(key, [])
                self._memory_buckets[key] = [t for t in timestamps if t > window_start]
                count = len(self._memory_buckets[key])
                self._memory_buckets[key].append(now)

            if count >= limit:
                logger.warning(
                    "Rate limit exceeded for %s on %s (limit: %d/min)", client_ip, path, limit
                )
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Too Many Requests",
                        "message": f"Rate limit of {limit} requests per minute exceeded.",
                        "retry_after_seconds": 60,
                    },
                    headers={"Retry-After": "60"},
                )
        except Exception as exc:
            logger.debug("Rate limit verification error: %s", exc)

        return await call_next(request)
