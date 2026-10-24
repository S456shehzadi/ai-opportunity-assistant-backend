from app.core.config import Settings, get_settings
from app.core.exceptions import SearchProviderException
from app.search.interfaces.search_provider import SearchProvider
from app.search.models.search_models import SearchQuery, SearchResults
from app.search.models.search_result import NormalizedSearchResult
from app.search.providers.mock_provider import MockSearchProvider
from app.search.providers.searxng_provider import SearXNGSearchProvider
from app.search.providers.tavily_provider import TavilySearchProvider


class ResilientSearchProvider(SearchProvider):
    """Wrapper executing primary search provider with automatic graceful fallback on failure."""

    def __init__(
        self,
        primary: SearchProvider,
        fallback: SearchProvider | None = None,
    ) -> None:
        super().__init__(f"resilient({primary.provider_name})")
        self.primary = primary
        self.fallback = fallback

    async def search_items(
        self,
        query: str,
        max_results: int = 10,
        query_purpose: str = "general_search",
        **kwargs,
    ) -> list[NormalizedSearchResult]:
        try:
            return await self.primary.search_items(
                query=query,
                max_results=max_results,
                query_purpose=query_purpose,
                **kwargs,
            )
        except Exception:
            if self.fallback:
                return await self.fallback.search_items(
                    query=query,
                    max_results=max_results,
                    query_purpose=query_purpose,
                    **kwargs,
                )
            raise

    async def search(self, query: SearchQuery) -> SearchResults:
        try:
            return await self.primary.search(query)
        except Exception:
            if self.fallback:
                return await self.fallback.search(query)
            raise


class SearchProviderFactory:
    """Factory creating search providers from settings with fallback resilience."""

    @classmethod
    def create_provider(
        cls,
        provider_name: str | None = None,
        settings: Settings | None = None,
    ) -> SearchProvider:
        cfg = settings or get_settings()
        name = (provider_name or cfg.SEARCH_PROVIDER).lower().strip()

        if name == "mock":
            return MockSearchProvider("mock")
        if name == "tavily":
            return TavilySearchProvider(
                api_key=cfg.SEARCH_API_KEY,
                endpoint=cfg.SEARCH_ENDPOINT or "https://api.tavily.com",
                timeout=cfg.SEARCH_TIMEOUT,
            )
        if name == "searxng":
            return SearXNGSearchProvider(
                endpoint=cfg.SEARCH_ENDPOINT or "http://localhost:8080",
                timeout=cfg.SEARCH_TIMEOUT,
            )

        raise SearchProviderException(
            message=f"Unsupported search provider: '{name}'",
            provider=name,
        )

    @classmethod
    def create_resilient_provider(
        cls,
        settings: Settings | None = None,
    ) -> SearchProvider:
        cfg = settings or get_settings()
        try:
            primary = cls.create_provider(cfg.SEARCH_PROVIDER, cfg)
        except Exception:
            primary = MockSearchProvider("mock")

        fallback_name = cfg.SEARCH_FALLBACK_PROVIDER
        fallback = None
        if fallback_name and fallback_name.lower() != cfg.SEARCH_PROVIDER.lower():
            try:
                fallback = cls.create_provider(fallback_name, cfg)
            except Exception:
                fallback = MockSearchProvider("mock")
        elif cfg.SEARCH_PROVIDER.lower() != "mock":
            fallback = MockSearchProvider("mock")

        return ResilientSearchProvider(primary=primary, fallback=fallback)
