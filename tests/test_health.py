import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert data["environment"] == "testing"
    assert data["version"] == "0.1.0"
    assert "timestamp" in data
    assert "services" in data
    assert data["services"]["database"] == "configured"
    assert data["services"]["ai_provider"] == "mock"
    assert data["services"]["search_provider"] == "mock"
