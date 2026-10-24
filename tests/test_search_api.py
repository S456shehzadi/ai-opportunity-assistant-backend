import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_search_api_with_query(client: AsyncClient) -> None:
    res = await client.post(
        "/api/v1/search",
        json={"query": "Find master's scholarships in Germany"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_results"] > 0
    assert len(data["executed_queries"]) >= 1
    assert data["results"][0]["url"].startswith("http")
    assert "search_id" in data


@pytest.mark.asyncio
async def test_search_api_validation_error(client: AsyncClient) -> None:
    # Sending neither query nor context
    res = await client.post(
        "/api/v1/search",
        json={},
    )
    assert res.status_code == 422
