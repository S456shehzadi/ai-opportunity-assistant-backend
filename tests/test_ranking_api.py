"""Integration tests for Personalized Opportunity Ranking REST API endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.fixtures.eligibility.dataset import USER_PROFILE_A_DICT


@pytest.mark.asyncio
async def test_rank_opportunities_endpoint_success(client: AsyncClient) -> None:
    """Tests POST /api/v1/opportunities/rank with inline profile, opportunities, and preferences."""
    payload = {
        "profile": USER_PROFILE_A_DICT,
        "opportunities": [
            {
                "id": "opp-1",
                "title": "DAAD Master in Computer Science",
                "organization": "DAAD",
                "description": "Full Master scholarship in Germany for Computer Science",
                "category": "scholarship",
                "host_country": "Germany",
                "countries_allowed": ["Global"],
                "funding_type": "fully_funded",
                "official_source_url": "https://daad.de/cs",
                "source_domain": "daad.de",
                "status": "active",
                "eligibility": {
                    "degree_levels": ["Master's"],
                    "fields_of_study": ["Computer Science"],
                    "min_gpa": 3.0,
                },
                "created_at": "2026-09-01T00:00:00Z",
                "updated_at": "2026-09-01T00:00:00Z",
            },
            {
                "id": "opp-2",
                "title": "Arts Residency in Sydney",
                "organization": "Sydney Art Council",
                "description": "Short residency in Australia for artists",
                "category": "scholarship",
                "host_country": "Australia",
                "countries_allowed": ["Global"],
                "funding_type": "partially_funded",
                "official_source_url": "https://sydneyart.org/residency",
                "source_domain": "sydneyart.org",
                "status": "active",
                "eligibility": {
                    "degree_levels": ["Bachelor's"],
                    "fields_of_study": ["Fine Arts"],
                    "min_gpa": 2.5,
                },
                "created_at": "2026-09-01T00:00:00Z",
                "updated_at": "2026-09-01T00:00:00Z",
            },
        ],
        "preferences": [
            {
                "category": "FUNDING",
                "value": "FULLY_FUNDED",
                "priority": "HIGH",
            },
            {
                "category": "LOCATION",
                "value": ["Germany"],
                "priority": "HIGH",
            },
        ],
        "sort_mode": "RELEVANCE",
    }

    res = await client.post("/api/v1/opportunities/rank", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert "opportunities" in data
    assert len(data["opportunities"]) == 2
    assert data["total_evaluated"] == 2
    assert data["filtered_out_count"] == 0

    top_opp = data["opportunities"][0]
    assert top_opp["opportunity_id"] == "opp-1"
    assert top_opp["rank"] == 1
    assert top_opp["relevance_score"] > data["opportunities"][1]["relevance_score"]
    assert top_opp["fit_summary"]
    assert len(top_opp["positive_factors"]) > 0


@pytest.mark.asyncio
async def test_rank_opportunities_empty_candidates(client: AsyncClient) -> None:
    """Tests POST /api/v1/opportunities/rank with empty candidates list."""
    payload = {
        "profile": USER_PROFILE_A_DICT,
        "opportunities": [],
        "sort_mode": "RELEVANCE",
    }

    res = await client.post("/api/v1/opportunities/rank", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["opportunities"] == []
    assert data["total_evaluated"] == 0


@pytest.mark.asyncio
async def test_rank_opportunities_invalid_sort_mode(client: AsyncClient) -> None:
    """Tests POST /api/v1/opportunities/rank with invalid sort_mode."""
    payload = {
        "profile": USER_PROFILE_A_DICT,
        "opportunities": [],
        "sort_mode": "UNKNOWN_SORT_MODE",
    }

    res = await client.post("/api/v1/opportunities/rank", json=payload)
    assert res.status_code == 422
