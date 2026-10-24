"""Source monitoring service verifying availability and fetching content safely."""

from __future__ import annotations

import logging
from typing import Any

from app.monitoring.interfaces.monitor import ISourceMonitor
from app.web.models.document import WebDocument
from app.web.service import WebRetrievalService

logger = logging.getLogger(__name__)


class SourceMonitor(ISourceMonitor):
    """Monitors remote opportunity web pages with strict error handling and security."""

    def __init__(self, retrieval_service: WebRetrievalService | None = None) -> None:
        self.retrieval_service = retrieval_service or WebRetrievalService()

    async def check_source_availability(
        self,
        url: str,
    ) -> tuple[bool, int, str | None]:
        """Checks if remote source is reachable.

        Differentiates server/network failure from content closure:
        - 200-299: Available
        - 404, 5xx, timeout: Returns (False, code, error). Never infers opportunity closed.
        """
        try:
            doc = await self.retrieval_service.retrieve_document(url, force_refresh=True)
            status_code = doc.status_code or 200

            if 200 <= status_code < 400 and (doc.clean_text or doc.raw_html):
                return True, status_code, None
            else:
                error_msg = f"Remote server returned HTTP {status_code}"
                return False, status_code, error_msg

        except Exception as exc:
            logger.warning("Source check failed for %s: %s", url, exc)
            return False, 0, f"Connection failure: {exc}"

    async def fetch_latest_content(
        self,
        url: str,
    ) -> tuple[str | None, str | None, dict[str, Any]]:
        """Safely fetches clean text and metadata, treating content as untrusted."""
        try:
            doc: WebDocument = await self.retrieval_service.retrieve_document(
                url, force_refresh=True
            )
            raw_html = doc.raw_html
            clean_text = doc.clean_text
            metadata = {
                "title": doc.title,
                "domain": doc.domain,
                "status_code": doc.status_code,
                "headings": [h.model_dump() for h in (doc.headings or [])],
                "final_url": doc.final_url,
            }
            return raw_html, clean_text, metadata
        except Exception as exc:
            logger.warning("Failed to fetch latest content for %s: %s", url, exc)
            return None, None, {"error": str(exc)}
