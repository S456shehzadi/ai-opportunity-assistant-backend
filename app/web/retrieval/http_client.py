"""Shared, connection-pooled HTTPX asynchronous client manager."""

import asyncio

import httpx

from app.core.config import get_settings

_client: httpx.AsyncClient | None = None
_client_lock = asyncio.Lock()


async def get_shared_http_client() -> httpx.AsyncClient:
    """Provides a shared connection-pooled AsyncClient configured for web retrieval."""
    global _client
    if _client is not None and not _client.is_closed:
        return _client

    async with _client_lock:
        if _client is not None and not _client.is_closed:
            return _client

        settings = get_settings()
        limits = httpx.Limits(
            max_connections=settings.WEB_MAX_CONNECTIONS,
            max_keepalive_connections=settings.WEB_MAX_KEEPALIVE_CONNECTIONS,
            keepalive_expiry=30.0,
        )
        timeout = httpx.Timeout(
            timeout=settings.WEB_TIMEOUT_READ,
            connect=settings.WEB_TIMEOUT_CONNECT,
            read=settings.WEB_TIMEOUT_READ,
            write=settings.WEB_TIMEOUT_WRITE,
            pool=settings.WEB_TIMEOUT_POOL,
        )
        headers = {
            "User-Agent": settings.WEB_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,*;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
        }

        _client = httpx.AsyncClient(
            limits=limits,
            timeout=timeout,
            headers=headers,
            follow_redirects=False,  # Manual redirect validation for SSRF security
            verify=True,
            http2=False,
        )
        return _client


async def close_shared_http_client() -> None:
    """Closes connection pools gracefully on application shutdown."""
    global _client
    async with _client_lock:
        if _client is not None and not _client.is_closed:
            await _client.aclose()
            _client = None
