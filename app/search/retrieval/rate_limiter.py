import asyncio
import logging
import random
import time
from collections.abc import Callable, Coroutine
from typing import Any, TypeVar

from app.core.exceptions import SearchProviderException

logger = logging.getLogger(__name__)
T = TypeVar("T")


class SearchRateLimiter:
    """Token bucket rate limiter and exponential backoff retry handler for search queries."""

    def __init__(self, requests_per_second: float = 5.0) -> None:
        self.rate = max(requests_per_second, 0.1)
        self.capacity = max(requests_per_second, 1.0)
        self.tokens = self.capacity
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait until a rate-limit token becomes available."""
        while True:
            async with self._lock:
                now = time.monotonic()
                elapsed = now - self.last_update
                self.last_update = now
                self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)

                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    return

                # Calculate required sleep time
                sleep_needed = (1.0 - self.tokens) / self.rate

            await asyncio.sleep(sleep_needed)

    async def execute_with_retry(
        self,
        func: Callable[..., Coroutine[Any, Any, T]],
        *args: Any,
        max_retries: int = 3,
        base_delay: float = 0.5,
        **kwargs: Any,
    ) -> T:
        """Executes an async search function with rate limiting, timeouts, and backoff."""
        attempt = 0
        while True:
            attempt += 1
            await self.acquire()
            try:
                return await func(*args, **kwargs)
            except TimeoutError as exc:
                if attempt >= max_retries:
                    logger.warning("Search timed out after %d attempts: %s", attempt, exc)
                    raise
                delay = (base_delay * (2 ** (attempt - 1))) + random.uniform(0.05, 0.2)
                logger.info("Search timed out on attempt %d. Retrying in %.2fs...", attempt, delay)
                await asyncio.sleep(delay)
            except SearchProviderException as exc:
                # Retry on HTTP 429 Rate Limit
                is_rate_limited = "429" in exc.message or "rate limit" in exc.message.lower()
                if is_rate_limited and attempt < max_retries:
                    delay = (base_delay * 2 * (2 ** (attempt - 1))) + random.uniform(0.1, 0.3)
                    logger.info(
                        "Rate limit hit on attempt %d. Backing off for %.2fs...", attempt, delay
                    )
                    await asyncio.sleep(delay)
                else:
                    raise
            except Exception as exc:
                # Do not retry fatal non-network exceptions
                logger.error("Non-retryable search error on attempt %d: %s", attempt, exc)
                raise
