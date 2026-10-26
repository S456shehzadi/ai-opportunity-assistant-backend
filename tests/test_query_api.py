import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_api_query_understand(client: AsyncClient) -> None:
    res = await client.post(
        "/api/v1/query/understand",
        json={"query": "Find fully funded master's scholarships in Europe for computer science."},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["intent_type"] == "find_scholarships"
    assert "Europe" in data["regions"]
    assert any("Master" in d for d in data["degree_levels"])
    assert data["funding_constraints"][0]["is_fully_funded"] is True


@pytest.mark.asyncio
async def test_api_query_context_and_conflicts(client: AsyncClient) -> None:
    # 1. Setup profile with preferred country Germany
    await client.post(
        "/api/v1/profile",
        json={
            "nationality": "Pakistan",
            "education_level": "Undergraduate",
            "degree_title": "BS Computer Science",
        },
    )
    await client.put(
        "/api/v1/profile/preferences",
        json={
            "preferred_countries": ["Germany"],
            "preferred_opportunity_categories": ["Scholarship"],
        },
    )

    # 2. Query for Japan (should trigger conflict override)
    res = await client.post(
        "/api/v1/query/context",
        json={"query": "Find scholarships in Japan"},
    )
    assert res.status_code == 200
    ctx = res.json()
    assert "Japan" in ctx["explicit_constraints"]["countries"]
    assert ctx["profile_constraints"]["nationality"] == "Pakistan"

    # Verify conflict detected
    assert len(ctx["conflicts"]) >= 1
    assert ctx["conflicts"][0]["field"] == "country"
    assert ctx["conflicts"][0]["resolution"] == "query_override"


@pytest.mark.asyncio
async def test_api_query_optimize(client: AsyncClient) -> None:
    res = await client.post(
        "/api/v1/query/optimize",
        json={"query": "Find AI master's scholarships without IELTS"},
    )
    assert res.status_code == 200
    queries = res.json()
    assert len(queries) >= 2
    assert any("ielts" in q["query"].lower() for q in queries)
