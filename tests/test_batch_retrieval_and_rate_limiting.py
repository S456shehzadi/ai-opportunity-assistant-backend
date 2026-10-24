"""Tests for batch retrieval concurrency and per-domain rate limiting."""

import time

import pytest

from app.web.policies.rate_limiter import DomainRateLimiter
from app.web.retrieval.batch_retriever import BatchWebRetriever
from app.web.retrieval.web_retriever import FetchedRawDocument, MockWebRetriever


@pytest.mark.asyncio
async def test_batch_retriever_concurrency_and_partial_failure() -> None:
    mock = MockWebRetriever()
    mock.set_route("https://example.org/doc1", "<html><body>Doc 1</body></html>", 200)
    mock.set_route("https://example.org/doc2", "<html><body>Doc 2</body></html>", 200)
    mock.set_route("https://example.org/fail", "500 Error", 500)

    batch_retriever = BatchWebRetriever(retriever=mock, max_concurrency=3)
    urls = [
        "https://example.org/doc1",
        "https://example.org/fail",
        "https://example.org/doc2",
    ]

    results = await batch_retriever.fetch_many(urls)
    assert len(results) == 3

    assert isinstance(results[0], FetchedRawDocument)
    assert results[0].original_url == "https://example.org/doc1"

    # Failed item returned as Exception without crashing others
    assert isinstance(results[1], Exception)

    assert isinstance(results[2], FetchedRawDocument)
    assert results[2].original_url == "https://example.org/doc2"


@pytest.mark.asyncio
async def test_domain_rate_limiter_delay() -> None:
    limiter = DomainRateLimiter(min_interval_seconds=0.1)

    start = time.monotonic()
    await limiter.acquire("example.org")
    await limiter.acquire("example.org")
    elapsed = time.monotonic() - start

    # Should take at least min_interval_seconds (0.1s)
    assert elapsed >= 0.08
