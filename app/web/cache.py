"""In-memory TTL cache for retrieved and processed WebDocument models."""

import asyncio
import time

from app.core.config import get_settings
from app.web.models.document import WebDocument


class CachedDocumentEntry:
    """Wrapper holding cached WebDocument and expiration timestamp."""

    def __init__(self, doc: WebDocument, expires_at: float) -> None:
        self.doc = doc
        self.expires_at = expires_at

    def is_expired(self) -> bool:
        return time.monotonic() > self.expires_at


class WebDocumentCache:
    """Thread-safe in-memory cache for processed WebDocuments."""

    def __init__(self, default_ttl_seconds: int | None = None) -> None:
        settings = get_settings()
        self.default_ttl = default_ttl_seconds or settings.WEB_DOCUMENT_CACHE_TTL
        self._entries: dict[str, CachedDocumentEntry] = {}
        self._lock = asyncio.Lock()

    async def get(self, url: str) -> WebDocument | None:
        """Retrieves unexpired cached WebDocument if present."""
        clean_key = url.strip().lower()
        entry = self._entries.get(clean_key)
        if entry is None:
            return None

        if entry.is_expired():
            async with self._lock:
                self._entries.pop(clean_key, None)
            return None

        return entry.doc

    async def set(self, url: str, doc: WebDocument, ttl: int | None = None) -> None:
        """Saves a WebDocument to cache with specified or default TTL."""
        clean_key = url.strip().lower()
        ttl_seconds = ttl or self.default_ttl
        expires_at = time.monotonic() + ttl_seconds

        async with self._lock:
            self._entries[clean_key] = CachedDocumentEntry(doc, expires_at)

    async def clear(self) -> None:
        """Flushes all cached entries."""
        async with self._lock:
            self._entries.clear()
