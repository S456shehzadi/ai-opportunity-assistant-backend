"""Robots.txt parsing, ethical policy enforcement, and domain-level caching."""

import asyncio
import logging
import time
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

from app.core.config import get_settings
from app.web.security.ssrf_protector import SSRFProtector

logger = logging.getLogger(__name__)


class CachedRobotsPolicy:
    """Holds a parsed RobotFileParser and timestamp for TTL cache invalidation."""

    def __init__(self, parser: RobotFileParser, expires_at: float) -> None:
        self.parser = parser
        self.expires_at = expires_at

    def is_expired(self) -> bool:
        return time.monotonic() > self.expires_at


class RobotsPolicyService:
    """Manages ethical robots.txt policy compliance with domain caching and polite fallbacks."""

    def __init__(self, cache_ttl_seconds: int | None = None) -> None:
        settings = get_settings()
        self.cache_ttl = cache_ttl_seconds or settings.WEB_ROBOTS_CACHE_TTL
        self.user_agent = settings.WEB_USER_AGENT
        self._cache: dict[str, CachedRobotsPolicy] = {}
        self._lock = asyncio.Lock()

    async def is_allowed(self, target_url: str, user_agent: str | None = None) -> bool:
        """Determines if the application crawler is allowed to retrieve the target URL.

        Args:
            target_url: Absolute URL to check.
            user_agent: Crawler user-agent string (defaults to configured application bot).

        Returns:
            bool: True if allowed to crawl, False if disallowed by robots.txt.
        """
        ua = user_agent or self.user_agent
        parsed = urlparse(target_url)
        domain = (parsed.hostname or "").lower()
        if not domain:
            return True

        scheme = parsed.scheme.lower() or "https"
        cache_key = f"{scheme}://{domain}"

        # 1. Fast Cache Read
        cached = self._cache.get(cache_key)
        if cached and not cached.is_expired():
            return cached.parser.can_fetch(ua, target_url)

        # 2. Cache Miss / Refresh under lock
        async with self._lock:
            cached = self._cache.get(cache_key)
            if cached and not cached.is_expired():
                return cached.parser.can_fetch(ua, target_url)

            parser = await self._fetch_and_parse_robots(scheme, domain)
            expires_at = time.monotonic() + self.cache_ttl
            self._cache[cache_key] = CachedRobotsPolicy(parser, expires_at)
            return parser.can_fetch(ua, target_url)

    async def _fetch_and_parse_robots(self, scheme: str, domain: str) -> RobotFileParser:
        """Politely fetches /robots.txt from the target domain."""
        parser = RobotFileParser()
        robots_url = f"{scheme}://{domain}/robots.txt"

        # Verify target domain is safe from SSRF before requesting robots.txt
        try:
            SSRFProtector.validate_host(domain, url=robots_url)
        except Exception as exc:
            logger.warning("Skipping robots.txt fetch for unsafe host '%s': %s", domain, exc)
            parser.allow_all = True
            return parser

        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(3.0, connect=3.0),
                headers={"User-Agent": self.user_agent},
                follow_redirects=True,
            ) as client:
                resp = await client.get(robots_url)

                if resp.status_code == 200:
                    lines = resp.text.splitlines()
                    parser.parse(lines)
                elif resp.status_code in (404, 410):
                    # No robots.txt means everything is allowed
                    parser.allow_all = True
                else:
                    # Non-200 / 404 (e.g. 500 error): per web standards, assume allowed
                    parser.allow_all = True
        except Exception as exc:
            logger.debug(
                "Could not fetch robots.txt for '%s' (%s), defaulting to allow.", domain, exc
            )
            parser.allow_all = True

        return parser
