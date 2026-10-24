"""Domain-aware rate limiter to prevent aggressive crawling bursts."""

import asyncio
import time

from app.core.config import get_settings


class DomainRateLimiter:
    """Enforces polite delays between consecutive requests to the same domain."""

    def __init__(self, min_interval_seconds: float | None = None) -> None:
        settings = get_settings()
        self.min_interval = min_interval_seconds or settings.WEB_RATE_LIMIT_PER_DOMAIN
        self._domain_locks: dict[str, asyncio.Lock] = {}
        self._last_access: dict[str, float] = {}
        self._global_lock = asyncio.Lock()

    async def acquire(self, domain: str) -> None:
        """Throttles execution so requests to the same domain maintain polite intervals."""
        clean_domain = domain.lower().strip()

        # Get or create domain lock
        async with self._global_lock:
            if clean_domain not in self._domain_locks:
                self._domain_locks[clean_domain] = asyncio.Lock()
            domain_lock = self._domain_locks[clean_domain]

        async with domain_lock:
            now = time.monotonic()
            last_time = self._last_access.get(clean_domain, 0.0)
            elapsed = now - last_time

            if elapsed < self.min_interval:
                sleep_needed = self.min_interval - elapsed
                await asyncio.sleep(sleep_needed)

            self._last_access[clean_domain] = time.monotonic()
