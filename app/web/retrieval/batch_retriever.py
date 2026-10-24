"""Controlled concurrency batch web retriever."""

import asyncio
import logging

from app.core.config import get_settings
from app.web.retrieval.web_retriever import FetchedRawDocument, WebRetriever

logger = logging.getLogger(__name__)


class BatchWebRetriever:
    """Manages parallel retrieval of multiple URLs under controlled concurrency."""

    def __init__(
        self,
        retriever: WebRetriever,
        max_concurrency: int | None = None,
    ) -> None:
        settings = get_settings()
        self.retriever = retriever
        self.concurrency_limit = max_concurrency or settings.WEB_MAX_CONCURRENT_RETRIEVALS
        self._semaphore = asyncio.Semaphore(self.concurrency_limit)

    async def fetch_many(self, urls: list[str]) -> list[FetchedRawDocument | Exception]:
        """Fetches multiple URLs concurrently up to max_concurrency.

        Returns:
            list[FetchedRawDocument | Exception]: Order-preserved list of retrieved documents
            or caught exceptions for failed targets.
        """
        tasks = [self._fetch_single(url) for url in urls]
        return await asyncio.gather(*tasks, return_exceptions=True)

    async def _fetch_single(self, url: str) -> FetchedRawDocument:
        async with self._semaphore:
            return await self.retriever.fetch(url)
