import pytest

from app.search.interfaces.search_provider import MockSearchProvider, get_search_provider
from app.search.models.search_models import SearchQuery, SearchResults
from app.search.retrieval.web_retriever import BaseWebRetriever, RetrievalPolicy


@pytest.mark.asyncio
async def test_search_provider_abstraction() -> None:
    provider = get_search_provider("mock")
    assert isinstance(provider, MockSearchProvider)

    query = SearchQuery(query_text="fellowships 2026", limit=5)
    results = await provider.search(query)

    assert isinstance(results, SearchResults)
    assert results.query.query_text == "fellowships 2026"
    assert results.provider == "mock"


@pytest.mark.asyncio
async def test_web_retriever_policy() -> None:
    policy = RetrievalPolicy(
        timeout_seconds=5.0,
        respect_robots_txt=True,
        rate_limit_per_domain_sec=2.0,
    )
    retriever = BaseWebRetriever(policy=policy)
    assert retriever.policy.respect_robots_txt is True
    assert retriever.policy.timeout_seconds == 5.0

    allowed = await retriever.is_allowed_by_robots_txt("https://example.com/scholarships")
    assert allowed is True
