import asyncio
import tempfile

import pytest
from httpx import AsyncClient

from app.core.metrics.collector import metrics_collector
from app.core.resilience.circuit_breaker import CircuitBreaker, CircuitBreakerOpenException
from app.core.storage.storage_service import LocalStorageBackend


@pytest.mark.asyncio
async def test_circuit_breaker_state_transitions() -> None:
    breaker = CircuitBreaker("test_breaker", failure_threshold=2, recovery_timeout=0.2)
    assert breaker.state == "CLOSED"

    async def fail_call() -> None:
        raise ValueError("Simulated fault")

    async def success_call() -> str:
        return "success"

    # 1. First failure
    with pytest.raises(ValueError):
        await breaker.call(fail_call)
    assert breaker.state == "CLOSED"

    # 2. Second failure trips the breaker
    with pytest.raises(ValueError):
        await breaker.call(fail_call)
    assert breaker.state == "OPEN"

    # 3. Subsequent call while OPEN fails fast
    with pytest.raises(CircuitBreakerOpenException):
        await breaker.call(success_call)

    # 4. Wait for recovery timeout
    await asyncio.sleep(0.25)

    # 5. Call in HALF_OPEN succeeds and resets to CLOSED
    result = await breaker.call(success_call)
    assert result == "success"
    assert breaker.state == "CLOSED"


@pytest.mark.asyncio
async def test_object_storage_local_backend() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = LocalStorageBackend(base_path=tmpdir, max_size_bytes=1024 * 1024)

        # 1. Put and get valid object
        key = "models/specialized_v1.tar.gz"
        content = b"fake binary weights content"
        saved_key = await storage.put_object(key, content, content_type="application/gzip")
        assert saved_key == key

        read_content = await storage.get_object(key)
        assert read_content == content

        # 2. Exists and delete
        assert await storage.exists(key) is True
        assert await storage.delete_object(key) is True
        assert await storage.exists(key) is False

        # 3. Path traversal attack rejection
        with pytest.raises(ValueError, match="path traversal"):
            await storage.put_object("../../../etc/passwd", b"malicious")

        # 4. Oversized object rejection
        huge_content = b"x" * (1024 * 1024 + 10)
        with pytest.raises(ValueError, match="exceeds maximum allowed"):
            await storage.put_object("huge.bin", huge_content)


@pytest.mark.asyncio
async def test_health_and_metrics_endpoints(client: AsyncClient) -> None:
    # 1. Liveness
    live_resp = await client.get("/live")
    assert live_resp.status_code == 200
    assert live_resp.json()["status"] == "alive"

    # 2. Readiness
    ready_resp = await client.get("/ready")
    assert ready_resp.status_code == 200
    assert ready_resp.json()["status"] == "ready"

    # 3. Comprehensive Health
    health_resp = await client.get("/health")
    assert health_resp.status_code == 200
    health_data = health_resp.json()
    assert health_data["status"] == "healthy"
    assert "services" in health_data

    # 4. Prometheus Metrics
    metrics_collector.record_http_request(
        method="GET", endpoint="/live", status_code=200, latency_ms=12.5
    )
    metrics_resp = await client.get("/metrics")
    assert metrics_resp.status_code == 200
    assert "text/plain" in metrics_resp.headers.get("content-type", "")
    assert "http_requests_total" in metrics_resp.text
