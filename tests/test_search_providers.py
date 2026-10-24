import pytest

from app.core.exceptions import SearchProviderException
from app.search.providers.mock_provider import MockSearchProvider
from app.search.providers.provider_factory import ResilientSearchProvider
from app.search.retrieval.rate_limiter import SearchRateLimiter


@pytest.mark.asyncio
async def test_mock_search_provider_returns_results() -> None:
    provider = MockSearchProvider()
    results = await provider.search_items("master's scholarships in Germany", max_results=5)

    assert len(results) > 0
    assert any("daad" in r.url.lower() or "tum" in r.url.lower() for r in results)
    assert results[0].provider == "mock"
    assert results[0].url.startswith("https://")


@pytest.mark.asyncio
async def test_mock_search_provider_simulated_empty() -> None:
    provider = MockSearchProvider()
    results = await provider.search_items("unmatched query", max_results=5, simulate_empty=True)
    assert len(results) == 0


@pytest.mark.asyncio
async def test_mock_search_provider_simulated_error() -> None:
    provider = MockSearchProvider()
    with pytest.raises(SearchProviderException):
        await provider.search_items("query", simulate_failure=True)


@pytest.mark.asyncio
async def test_resilient_provider_falls_back_on_primary_failure() -> None:
    # Primary fails with exception
    primary = MockSearchProvider("failing_primary")
    primary.simulate_failure = True

    # Fallback succeeds
    fallback = MockSearchProvider("reliable_fallback")

    resilient = ResilientSearchProvider(primary=primary, fallback=fallback)
    results = await resilient.search_items("scholarships in Europe", max_results=3)

    assert len(results) > 0
    assert results[0].provider == "reliable_fallback"


@pytest.mark.asyncio
async def test_rate_limiter_executes_successfully() -> None:
    limiter = SearchRateLimiter(requests_per_second=20.0)

    async def _sample_call(val: int) -> int:
        return val * 2

    res = await limiter.execute_with_retry(_sample_call, 5)
    assert res == 10
