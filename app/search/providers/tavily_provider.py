import uuid
from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.exceptions import SearchProviderException
from app.search.interfaces.search_provider import SearchProvider
from app.search.models.search_models import SearchQuery, SearchResultItem, SearchResults
from app.search.models.search_result import NormalizedSearchResult
from app.search.normalization.url_normalizer import UrlNormalizer


class TavilySearchProvider(SearchProvider):
    """Legitimate programmatic web search adapter using the official Tavily REST API."""

    def __init__(
        self,
        api_key: str | None = None,
        endpoint: str = "https://api.tavily.com",
        timeout: float = 10.0,
    ) -> None:
        super().__init__("tavily")
        self.api_key = api_key
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout

    async def search_items(
        self,
        query: str,
        max_results: int = 10,
        query_purpose: str = "general_search",
        **kwargs: Any,
    ) -> list[NormalizedSearchResult]:
        if not self.api_key:
            raise SearchProviderException(
                message="Tavily API key is not configured. Set SEARCH_API_KEY in environment.",
                provider="tavily",
            )

        payload = {
            "api_key": self.api_key,
            "query": query,
            "max_results": min(max_results, 20),
            "search_depth": kwargs.get("search_depth", "basic"),
            "include_answer": False,
        }

        url = f"{self.endpoint}/search"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(url, json=payload)
            except httpx.TimeoutException as exc:
                raise TimeoutError(f"Tavily search timed out after {self.timeout}s") from exc
            except httpx.RequestError as exc:
                raise SearchProviderException(
                    message=f"Tavily connection error: {exc}",
                    provider="tavily",
                ) from exc

        if response.status_code == 429:
            raise SearchProviderException(
                message="Tavily rate limit exceeded: HTTP 429",
                provider="tavily",
            )
        if response.status_code == 401:
            raise SearchProviderException(
                message="Tavily authentication failed: invalid API key",
                provider="tavily",
            )
        if response.status_code >= 400:
            raise SearchProviderException(
                message=f"Tavily API returned error HTTP {response.status_code}",
                provider="tavily",
            )

        try:
            data = response.json()
        except Exception as exc:
            raise SearchProviderException(
                message=f"Malformed response from Tavily API: {exc}",
                provider="tavily",
            ) from exc

        raw_results = data.get("results", [])
        normalized_results: list[NormalizedSearchResult] = []

        for idx, item in enumerate(raw_results, start=1):
            raw_url = item.get("url", "")
            if not raw_url:
                continue

            canonical_url = UrlNormalizer.normalize_url(raw_url)
            domain = UrlNormalizer.extract_domain(canonical_url)
            is_official = any(domain.endswith(tld) for tld in (".edu", ".gov", ".org", ".eu"))

            normalized_results.append(
                NormalizedSearchResult(
                    id=uuid.uuid4(),
                    title=item.get("title", ""),
                    url=canonical_url,
                    original_url=raw_url,
                    snippet=item.get("content", ""),
                    domain=domain,
                    rank=idx,
                    provider="tavily",
                    query=query,
                    query_purpose=query_purpose,
                    published_at=item.get("published_date"),
                    retrieved_at=datetime.now(UTC),
                    relevance_score=float(item.get("score", 0.75)),
                    is_official_source_candidate=is_official,
                    raw_metadata={"raw_score": item.get("score")},
                )
            )

        return normalized_results

    async def search(self, query: SearchQuery) -> SearchResults:
        items = await self.search_items(query.query_text, max_results=query.limit)
        return SearchResults(
            query=query,
            provider="tavily",
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
