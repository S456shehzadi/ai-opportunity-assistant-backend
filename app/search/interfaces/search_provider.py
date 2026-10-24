from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from app.search.models.search_models import SearchQuery, SearchResults
from app.search.models.search_result import NormalizedSearchResult

if TYPE_CHECKING:
    pass


class SearchProvider(ABC):
    """Abstract base provider for querying search engines."""

    def __init__(self, provider_name: str) -> None:
        self.provider_name = provider_name

    @abstractmethod
    async def search_items(
        self,
        query: str,
        max_results: int = 10,
        query_purpose: str = "general_search",
        **kwargs: Any,
    ) -> list[NormalizedSearchResult]:
        """Executes search and returns normalized search result items."""
        pass

    @abstractmethod
    async def search(self, query: SearchQuery) -> SearchResults:
        """Backward-compatible query interface returning SearchResults."""
        pass


def get_search_provider(provider_name: str) -> SearchProvider:
    """Factory helper resolving search provider by name."""
    from app.search.providers.provider_factory import SearchProviderFactory

    return SearchProviderFactory.create_provider(provider_name)


# Re-export for backward compatibility
from app.search.providers.mock_provider import MockSearchProvider  # noqa: E402

__all__ = ["MockSearchProvider", "SearchProvider", "get_search_provider"]
