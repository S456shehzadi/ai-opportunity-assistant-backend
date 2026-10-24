"""Tests for WebRetriever, content limits, content types, and error handling."""

from unittest.mock import AsyncMock

import pytest

from app.web.models.errors import (
    HTTPStatusError,
    RobotsDisallowedError,
    SSRFBlockedError,
)
from app.web.policies.robots_service import RobotsPolicyService
from app.web.retrieval.web_retriever import HttpWebRetriever, MockWebRetriever


@pytest.mark.asyncio
async def test_mock_web_retriever_fetch() -> None:
    mock = MockWebRetriever()
    html_content = "<html><head><title>Test</title></head><body><h1>Hello World</h1></body></html>"
    mock.set_route("https://example.org/test", html=html_content, status_code=200)

    doc = await mock.fetch("https://example.org/test")
    assert doc.status_code == 200
    assert doc.domain == "example.org"
    assert "Hello World" in doc.raw_html


@pytest.mark.asyncio
async def test_mock_web_retriever_http_error() -> None:
    mock = MockWebRetriever()
    mock.set_route("https://example.org/notfound", html="404 Not Found", status_code=404)

    with pytest.raises(HTTPStatusError) as exc_info:
        await mock.fetch("https://example.org/notfound")
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_http_retriever_blocks_ssrf_and_robots() -> None:
    robots_mock = RobotsPolicyService()
    robots_mock.is_allowed = AsyncMock(return_value=False)  # type: ignore

    retriever = HttpWebRetriever(robots_service=robots_mock)

    # SSRF blocked before network request
    with pytest.raises(SSRFBlockedError):
        await retriever.fetch("http://127.0.0.1:8000/secret")

    # Robots disallowed
    with pytest.raises(RobotsDisallowedError):
        await retriever.fetch("https://example.org/disallowed-path")
