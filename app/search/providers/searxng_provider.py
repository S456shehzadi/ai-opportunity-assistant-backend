import uuid
from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.exceptions import SearchProviderException
from app.search.interfaces.search_provider import SearchProvider
from app.search.models.search_models import SearchQuery, SearchResultItem, SearchResults
from app.search.models.search_result import NormalizedSearchResult
from app.search.normalization.url_normalizer import UrlNormalizer


class SearXNGSearchProvider(SearchProvider):
    """Programmatic meta-search adapter using official SearXNG JSON API."""

    def __init__(
        self,
        endpoint: str = "http://localhost:8080",
        timeout: float = 10.0,
    ) -> None:
        super().__init__("searxng")
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout

    async def search_items(
        self,
        query: str,
        max_results: int = 10,
        query_purpose: str = "general_search",
        **kwargs: Any,
    ) -> list[NormalizedSearchResult]:
        params = {
            "q": query,
            "format": "json",
            "categories": "general",
            "language": "en",
        }

        url = f"{self.endpoint}/search"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(url, params=params)
            except httpx.TimeoutException as exc:
                raise TimeoutError(f"SearXNG timed out after {self.timeout}s") from exc
            except httpx.RequestError as exc:
                raise SearchProviderException(
                    message=f"SearXNG connection error: {exc}",
                    provider="searxng",
                ) from exc

        if response.status_code == 429:
            raise SearchProviderException(
                message="SearXNG rate limit exceeded: HTTP 429",
                provider="searxng",
            )
        if response.status_code >= 400:
            raise SearchProviderException(
                message=f"SearXNG returned error HTTP {response.status_code}",
                provider="searxng",
            )

        try:
            data = response.json()
        except Exception as exc:
            raise SearchProviderException(
                message=f"Malformed SearXNG response: {exc}",
                provider="searxng",
            ) from exc

        raw_results = data.get("results", [])
        normalized: list[NormalizedSearchResult] = []

        for idx, item in enumerate(raw_results[:max_results], start=1):
            raw_url = item.get("url", "")
            if not raw_url:
                continue

            canonical_url = UrlNormalizer.normalize_url(raw_url)
            domain = UrlNormalizer.extract_domain(canonical_url)
            is_official = any(domain.endswith(tld) for tld in (".edu", ".gov", ".org", ".eu"))

            normalized.append(
                NormalizedSearchResult(
                    id=uuid.uuid4(),
                    title=item.get("title", ""),
                    url=canonical_url,
                    original_url=raw_url,
                    snippet=item.get("content", ""),
                    domain=domain,
                    rank=idx,
                    provider="searxng",
                    query=query,
                    query_purpose=query_purpose,
                    published_at=item.get("publishedDate"),
                    retrieved_at=datetime.now(UTC),
                    relevance_score=float(item.get("score", 0.7)),
                    is_official_source_candidate=is_official,
                    raw_metadata={"engines": item.get("engines", [])},
                )
            )

        return normalized

    async def search(self, query: SearchQuery) -> SearchResults:
        items = await self.search_items(query.query_text, max_results=query.limit)
        return SearchResults(
            query=query,
            provider="searxng",
            items=[
                SearchResultItem(
                    title=item.title,
                    url=item.url,
                    snippet=item.snippet,
                    domain=item.domain,
                    rank=item.rank,
                    published_date=item.published_at,
                    metadata=item.raw_metadata,
                )
                for item in items
            ],
            retrieved_at=datetime.now(UTC),
            total_results=len(items),
        )
