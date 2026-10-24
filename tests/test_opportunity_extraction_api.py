"""Tests for Opportunity Extraction REST API endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from tests.fixtures.opportunities.dataset import (
    COMPLETE_SCHOLARSHIP_HTML,
    build_synthetic_document,
)


@pytest.mark.asyncio
async def test_extract_opportunity_from_document_payload(client: AsyncClient) -> None:
    """Tests POST /api/v1/opportunities/extract with pre-constructed WebDocument."""
    doc = build_synthetic_document(
        title="DAAD Master Scholarships 2026",
        html=COMPLETE_SCHOLARSHIP_HTML,
        url="https://daad.de/masters",
        domain="daad.de",
    )

    res = await client.post(
        "/api/v1/opportunities/extract",
        json={"document": doc.model_dump(mode="json")},
    )
    assert res.status_code == 200
    data = res.json()

    assert data["canonical_key"].startswith("opp_")
    assert data["title"] == "DAAD Helmut-Schmidt-Programme Master Scholarships 2026"
    assert data["funding_type"] == "Fully Funded"
    assert data["deadline"]["value"] == "2026-07-31"
    assert data["source_type"] == "OFFICIAL"
    assert data["confidence"] > 0.6


@pytest.mark.asyncio
async def test_extract_opportunity_from_url_mocked(client: AsyncClient) -> None:
    """Tests POST /api/v1/opportunities/extract with URL retrieval mocked."""
    doc = build_synthetic_document(
        title="DAAD Master Scholarships 2026",
        html=COMPLETE_SCHOLARSHIP_HTML,
        url="https://daad.de/masters",
        domain="daad.de",
    )

    with patch(
        "app.api.v1.endpoints.opportunities.web_service.retrieve_and_process",
        new=AsyncMock(return_value=doc),
    ):
        res = await client.post(
            "/api/v1/opportunities/extract",
            json={"url": "https://daad.de/masters"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["title"] == "DAAD Helmut-Schmidt-Programme Master Scholarships 2026"


@pytest.mark.asyncio
async def test_extract_opportunity_missing_params(client: AsyncClient) -> None:
    """Tests 400 Bad Request when neither url nor document is provided."""
    res = await client.post(
        "/api/v1/opportunities/extract",
        json={},
    )
    assert res.status_code == 400
    assert "Either 'url' or 'document' must be provided" in res.json()["detail"]


@pytest.mark.asyncio
async def test_deduplicate_endpoint(client: AsyncClient) -> None:
    """Tests POST /api/v1/opportunities/deduplicate endpoint."""
    res = await client.post(
        "/api/v1/opportunities/deduplicate",
        json={
            "title_a": "DAAD Master Scholarships 2026",
            "organization_a": "DAAD Germany",
            "url_a": "https://daad.de/masters?utm_source=ad",
            "title_b": "DAAD Master Scholarships 2026",
            "organization_b": "DAAD Germany",
            "url_b": "https://daad.de/masters",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["is_duplicate"] is True
    assert data["canonical_key_a"] == data["canonical_key_b"]
