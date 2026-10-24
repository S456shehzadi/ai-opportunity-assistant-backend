"""Asynchronous web retriever handling HTTP/HTTPS, redirects, timeouts, retries, and SSRF."""

import asyncio
import ipaddress
import logging
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.config import get_settings
from app.web.models.errors import (
    ConnectionFailureError,
    ContentTooLargeError,
    HTTPStatusError,
    RobotsDisallowedError,
    SSRFBlockedError,
    UnsupportedContentTypeError,
    WebTimeoutError,
)
from app.web.policies.rate_limiter import DomainRateLimiter
from app.web.policies.robots_service import RobotsPolicyService
from app.web.retrieval.http_client import get_shared_http_client
from app.web.security.ssrf_protector import SSRFProtector
from app.web.security.url_validator import URLValidator

logger = logging.getLogger(__name__)

SUPPORTED_CONTENT_TYPES = {"text/html", "application/xhtml+xml", "text/plain"}
RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}


@dataclass
class FetchedRawDocument:
    """Raw web document payload fetched by WebRetriever before extraction."""

    original_url: str
    final_url: str
    domain: str
    status_code: int
    content_type: str
    raw_html: str
    encoding: str
    redirect_chain: list[str] = field(default_factory=list)
    retrieved_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    headers: dict[str, str] = field(default_factory=dict)


class WebRetriever(ABC):
    """Abstract interface for ethical, secure web document retrieval."""

    @abstractmethod
    async def fetch(self, url: str) -> FetchedRawDocument:
        """Retrieves target webpage markup safely."""


class HttpWebRetriever(WebRetriever):
    """Production asynchronous HTTP retriever with SSRF protection and polite crawling."""

    def __init__(
        self,
        robots_service: RobotsPolicyService | None = None,
        rate_limiter: DomainRateLimiter | None = None,
    ) -> None:
        self.settings = get_settings()
        self.robots_service = robots_service or RobotsPolicyService()
        self.rate_limiter = rate_limiter or DomainRateLimiter()

    async def fetch(self, url: str) -> FetchedRawDocument:
        """Safely fetches a web page with validation, SSRF checks, robots.txt, and retries."""
        # 1. URL Validation
        normalized_url, hostname = URLValidator.validate_and_normalize(url)

        # 2. SSRF Protection (DNS & IP validation)
        SSRFProtector.validate_host(hostname, url=normalized_url)

        # 3. Robots.txt Compliance Check
        is_allowed = await self.robots_service.is_allowed(normalized_url)
        if not is_allowed:
            raise RobotsDisallowedError(
                f"Crawling disallowed by robots.txt for URL: {normalized_url}",
                url=normalized_url,
            )

        # 4. Domain Rate Limiting
        await self.rate_limiter.acquire(hostname)

        # 5. Retrieval with Redirect and Retry Handling
        return await self._fetch_with_retries(normalized_url)

    async def _fetch_with_retries(self, initial_url: str) -> FetchedRawDocument:
        client = await get_shared_http_client()
        current_url = initial_url
        redirect_chain: list[str] = []

        max_retries = self.settings.WEB_MAX_RETRIES
        max_redirects = self.settings.WEB_MAX_REDIRECTS
        max_response_bytes = self.settings.WEB_MAX_RESPONSE_SIZE

        attempt = 0
        while True:
            try:
                # Manual redirect resolution loop
                while True:
                    req = client.build_request("GET", current_url)
                    resp = await client.send(req, stream=True)

                    status = resp.status_code

                    # Handle Redirects (3xx)
                    if status in (301, 302, 303, 307, 308):
                        location = resp.headers.get("Location")
                        await resp.aclose()

                        if not location:
                            raise HTTPStatusError(
                                f"Redirect status {status} received without Location header.",
                                status_code=status,
                                url=current_url,
                            )

                        redirect_chain.append(current_url)
                        target_url, target_host = SSRFProtector.validate_redirect(
                            current_url=current_url,
                            location_header=location,
                            redirect_chain=redirect_chain,
                            max_redirects=max_redirects,
                        )
                        # Throttle next domain hop
                        await self.rate_limiter.acquire(target_host)
                        current_url = target_url
                        continue

                    # Handle Non-Redirect Responses
                    content_type_raw = resp.headers.get("Content-Type", "").lower()
                    mime_type = content_type_raw.split(";")[0].strip() or "text/html"

                    if mime_type not in SUPPORTED_CONTENT_TYPES:
                        await resp.aclose()
                        raise UnsupportedContentTypeError(
                            f"Unsupported Content-Type '{mime_type}'. "
                            f"Supported: {SUPPORTED_CONTENT_TYPES}",
                            url=current_url,
                        )

                    # Stream response and enforce size bounds
                    chunks: list[bytes] = []
                    total_bytes = 0
                    try:
                        async for chunk in resp.aiter_bytes():
                            total_bytes += len(chunk)
                            if total_bytes > max_response_bytes:
                                await resp.aclose()
                                raise ContentTooLargeError(
                                    f"Response exceeded size limit of {max_response_bytes} bytes.",
                                    url=current_url,
                                )
                            chunks.append(chunk)
                    finally:
                        await resp.aclose()

                    # Handle HTTP Errors
                    if status >= 400:
                        retry_after = self._parse_retry_after(resp.headers.get("Retry-After"))
                        if status in RETRYABLE_STATUS_CODES and attempt < max_retries:
                            attempt += 1
                            delay = retry_after or (0.5 * (2**attempt) + random.uniform(0.1, 0.5))
                            logger.warning(
                                "HTTP %d on %s, retrying attempt %d in %.2fs",
                                status,
                                current_url,
                                attempt,
                                delay,
                            )
                            await asyncio.sleep(delay)
                            break  # Break inner loop to retry GET request
                        raise HTTPStatusError(
                            f"HTTP request failed with status {status}",
                            status_code=status,
                            url=current_url,
                            retry_after=retry_after,
                        )

                    # Decode Content
                    encoding = resp.encoding or "utf-8"
                    raw_bytes = b"".join(chunks)
                    try:
                        raw_html = raw_bytes.decode(encoding, errors="replace")
                    except Exception:
                        raw_html = raw_bytes.decode("utf-8", errors="replace")

                    if len(raw_html) > self.settings.WEB_MAX_HTML_SIZE:
                        max_chars = self.settings.WEB_MAX_HTML_SIZE
                        raise ContentTooLargeError(
                            f"HTML markup exceeded max HTML size ({max_chars} chars).",
                            url=current_url,
                        )

                    parsed_final = URLValidator.validate_and_normalize(current_url)
                    return FetchedRawDocument(
                        original_url=initial_url,
                        final_url=parsed_final[0],
                        domain=parsed_final[1],
                        status_code=status,
                        content_type=mime_type,
                        raw_html=raw_html,
                        encoding=encoding,
                        redirect_chain=redirect_chain,
                        headers=dict(resp.headers),
                    )

            except (httpx.TimeoutException, TimeoutError) as exc:
                if attempt < max_retries:
                    attempt += 1
                    delay = 0.5 * (2**attempt) + random.uniform(0.1, 0.4)
                    logger.warning(
                        "Timeout retrieving %s, retry %d in %.2fs", current_url, attempt, delay
                    )
                    await asyncio.sleep(delay)
                    continue
                raise WebTimeoutError(
                    f"Request timeout while retrieving: {exc}", url=current_url
                ) from exc

            except (httpx.NetworkError, httpx.RemoteProtocolError) as exc:
                if attempt < max_retries:
                    attempt += 1
                    delay = 0.5 * (2**attempt) + random.uniform(0.1, 0.4)
                    logger.warning(
                        "Network failure for %s, retry %d in %.2fs", current_url, attempt, delay
                    )
                    await asyncio.sleep(delay)
                    continue
                raise ConnectionFailureError(
                    f"Connection failed while retrieving: {exc}", url=current_url
                ) from exc

    def _parse_retry_after(self, retry_header: str | None) -> float | None:
        if not retry_header:
            return None
        try:
            return float(retry_header)
        except ValueError:
            return None


class MockWebRetriever(WebRetriever):
    """Deterministic mock retriever for offline development, fixtures, and unit tests."""

    def __init__(self, routes: dict[str, Any] | None = None) -> None:
        self.routes: dict[str, Any] = routes or {}
        self.retrieval_history: list[str] = []

    def set_route(
        self, url: str, html: str, status_code: int = 200, headers: dict | None = None
    ) -> None:
        norm_url, domain = URLValidator.validate_and_normalize(url)
        self.routes[norm_url] = {
            "html": html,
            "status_code": status_code,
            "domain": domain,
            "headers": headers or {"Content-Type": "text/html; charset=utf-8"},
        }

    async def fetch(self, url: str) -> FetchedRawDocument:
        norm_url, domain = URLValidator.validate_and_normalize(url)
        # Check SSRF on explicit IPs or internal names without requiring live external DNS
        try:
            ip_obj = ipaddress.ip_address(domain)
            SSRFProtector._verify_ip_is_public(ip_obj, url=norm_url)
        except ValueError:
            if domain in ("localhost", "localhost.localdomain") or domain.endswith(".internal"):
                raise SSRFBlockedError(
                    f"Access to internal hostname '{domain}' is prohibited.", url=norm_url
                ) from None

        self.retrieval_history.append(norm_url)

        if norm_url in self.routes:
            entry = self.routes[norm_url]
            status = entry.get("status_code", 200)
            if status >= 400:
                raise HTTPStatusError(f"HTTP mock error {status}", status_code=status, url=norm_url)
            return FetchedRawDocument(
                original_url=url,
                final_url=norm_url,
                domain=domain,
                status_code=status,
                content_type="text/html",
                raw_html=entry["html"],
                encoding="utf-8",
                redirect_chain=[],
                headers=entry.get("headers", {}),
            )

        # Fallback synthetic page
        return FetchedRawDocument(
            original_url=url,
            final_url=norm_url,
            domain=domain,
            status_code=200,
            content_type="text/html",
            raw_html=(
                f"<html><head><title>Opportunity Page</title></head>"
                f"<body><h1>Opportunity for {domain}</h1>"
                f"<p>Full funding available for master's students.</p></body></html>"
            ),
            encoding="utf-8",
        )
