"""Tests for Web Retrieval REST API endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.web.models.document import ContentQualityScore, PageType, WebDocument


@pytest.mark.asyncio
async def test_api_web_retrieve_success(client: AsyncClient) -> None:
    mock_doc = WebDocument(
        original_url="https://scholarships.example.org/test",
        final_url="https://scholarships.example.org/test",
        domain="scholarships.example.org",
        status_code=200,
        content_type="text/html",
        title="Sample Scholarship",
        clean_text="Clean text about scholarship funding.",
        language="en",
        word_count=5,
        content_quality=ContentQualityScore(
            text_length=35,
            word_count=5,
            text_to_code_ratio=0.5,
            has_main_content=False,
            quality_score=0.5,
        ),
        page_type=PageType.OPPORTUNITY_PAGE,
        content_hash="abc123",
        simhash="ffff",
    )

    with patch(
        "app.api.v1.endpoints.web.web_service.retrieve_document",
        new=AsyncMock(return_value=mock_doc),
    ):
        res = await client.post(
            "/api/v1/web/retrieve",
            json={"url": "https://scholarships.example.org/test"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["title"] == "Sample Scholarship"
        assert data["domain"] == "scholarships.example.org"
        assert data["page_type"] == "OPPORTUNITY_PAGE"


@pytest.mark.asyncio
async def test_api_web_retrieve_ssrf_blocked(client: AsyncClient) -> None:
    res = await client.post(
        "/api/v1/web/retrieve",
        json={"url": "http://127.0.0.1:8000/admin"},
    )
    # SSRF protection raises SSRFBlockedError -> HTTP 403 Forbidden
    assert res.status_code == 403
    assert "SSRF" in res.json()["detail"]


@pytest.mark.asyncio
async def test_api_web_retrieve_invalid_scheme(client: AsyncClient) -> None:
    res = await client.post(
        "/api/v1/web/retrieve",
        json={"url": "file:///etc/passwd"},
    )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_api_web_batch_retrieve(client: AsyncClient) -> None:
    mock_doc = WebDocument(
        original_url="https://scholarships.example.org/1",
        final_url="https://scholarships.example.org/1",
        domain="scholarships.example.org",
        status_code=200,
        content_type="text/html",
        title="Doc 1",
        clean_text="Text 1",
        language="en",
        word_count=2,
    )

    with patch(
        "app.api.v1.endpoints.web.web_service.retrieve_batch",
        new=AsyncMock(return_value=[mock_doc]),
    ):
        res = await client.post(
            "/api/v1/web/batch-retrieve",
            json={"urls": ["https://scholarships.example.org/1"]},
        )
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 1
        assert data[0]["title"] == "Doc 1"
