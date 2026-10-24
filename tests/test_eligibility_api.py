"""Tests for Eligibility Matching REST API endpoints."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from tests.fixtures.eligibility.dataset import (
    OPPORTUNITY_A_STANDARD_DICT,
    OPPORTUNITY_B_STRICT_CGPA_DICT,
    USER_PROFILE_A_DICT,
    USER_PROFILE_B_LOW_CGPA_DICT,
)


@pytest.mark.asyncio
async def test_direct_evaluate_eligibility_endpoint_success(client: AsyncClient) -> None:
    """Tests POST /api/v1/eligibility/evaluate with inline profile and opportunity."""
    payload = {
        "profile": USER_PROFILE_A_DICT,
        "opportunity": OPPORTUNITY_A_STANDARD_DICT,
    }

    res = await client.post("/api/v1/eligibility/evaluate", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["overall_status"] == "CLEARLY_ELIGIBLE"
    assert data["match_percentage"] >= 90.0
    assert len(data["requirements"]) > 0
    assert "explanation" in data
    assert "personalized_intelligence" in data
    assert data["personalized_intelligence"]["satisfied_requirements"]


@pytest.mark.asyncio
async def test_direct_evaluate_eligibility_scenario_b(client: AsyncClient) -> None:
    """Tests POST /api/v1/eligibility/evaluate for Scenario B (low CGPA)."""
    payload = {
        "profile": USER_PROFILE_B_LOW_CGPA_DICT,
        "opportunity": OPPORTUNITY_B_STRICT_CGPA_DICT,
    }

    res = await client.post("/api/v1/eligibility/evaluate", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["overall_status"] == "CLEARLY_NOT_ELIGIBLE"
    assert len(data["blocking_requirements"]) > 0


@pytest.mark.asyncio
async def test_direct_evaluate_missing_inputs_returns_400(client: AsyncClient) -> None:
    """Tests POST /api/v1/eligibility/evaluate with missing inputs."""
    # 1. Missing both profile and opportunity
    res1 = await client.post("/api/v1/eligibility/evaluate", json={})
    assert res1.status_code == 400

    # 2. Provided profile but missing opportunity
    res2 = await client.post(
        "/api/v1/eligibility/evaluate",
        json={"profile": USER_PROFILE_A_DICT},
    )
    assert res2.status_code == 400


@pytest.mark.asyncio
async def test_batch_evaluate_eligibility_endpoint_success(client: AsyncClient) -> None:
    """Tests POST /api/v1/eligibility/batch with multiple opportunities."""
    payload = {
        "profile": USER_PROFILE_A_DICT,
        "opportunities": [
            OPPORTUNITY_A_STANDARD_DICT,
            OPPORTUNITY_B_STRICT_CGPA_DICT,
        ],
    }

    res = await client.post("/api/v1/eligibility/batch", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["overall_status"] == "CLEARLY_ELIGIBLE"


@pytest.mark.asyncio
async def test_batch_evaluate_empty_opportunities_returns_400(client: AsyncClient) -> None:
    """Tests POST /api/v1/eligibility/batch with empty opportunities list."""
    payload = {
        "profile": USER_PROFILE_A_DICT,
        "opportunities": [],
    }

    res = await client.post("/api/v1/eligibility/batch", json=payload)
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_evaluate_opportunity_not_found(client: AsyncClient) -> None:
    """Tests POST /api/v1/opportunities/{opportunity_id}/eligibility for non-existent ID."""
    random_id = str(uuid.uuid4())
    res = await client.post(f"/api/v1/opportunities/{random_id}/eligibility")
    assert res.status_code in (404, 503)
