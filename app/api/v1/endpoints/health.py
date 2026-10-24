"""Health check, readiness, liveness, and Prometheus metrics endpoints."""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_settings, get_optional_db
from app.core.config import Settings
from app.core.metrics.collector import get_metrics_collector
from app.core.redis import get_redis_service
from app.core.resilience.circuit_breaker import get_circuit_breaker
from app.schemas.health import HealthResponse, ServiceStatus

router = APIRouter()


@router.get(
    "/live",
    status_code=status.HTTP_200_OK,
    summary="Liveness Probe",
    description="Kubernetes/container liveness probe verifying process is responsive.",
)
async def check_liveness() -> dict[str, Any]:
    """Returns immediately with 200 OK to confirm application process is running."""
    return {"status": "alive", "timestamp": int(time.time())}


@router.get(
    "/ready",
    status_code=status.HTTP_200_OK,
    summary="Readiness Probe",
    description="Verifies availability of critical dependencies (Database, Redis).",
)
async def check_readiness(
    response: Response,
    db: AsyncSession | None = Depends(get_optional_db),
    settings: Settings = Depends(get_current_settings),
) -> dict[str, Any]:
    """Probes backend subsystems and returns 200 if ready to receive traffic, else 503."""
    db_ok = False
    redis_ok = False

    # 1. Probe database
    if db is not None:
        try:
            res = await db.execute(text("SELECT 1"))
            db_ok = res.scalar() == 1
        except Exception:
            db_ok = False

    # 2. Probe Redis
    try:
        redis_service = get_redis_service()
        redis_ok = await redis_service.is_healthy()
    except Exception:
        redis_ok = False

    is_ready = db_ok or not settings.is_production
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ready" if is_ready else "not_ready",
        "database": "connected" if db_ok else "unreachable",
        "redis": "connected" if redis_ok else "offline_fallback",
        "timestamp": int(time.time()),
    }


@router.get(
    "/metrics",
    summary="Prometheus Application Metrics",
    description="Exposes application counters and latency observations in Prometheus format.",
)
async def get_prometheus_metrics() -> Response:
    """Returns application metrics formatted for scraping by Prometheus."""
    collector = get_metrics_collector()
    content = collector.format_prometheus()
    return Response(
        content=content,
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Application Health Check",
    description="Returns high-level status of the API, environment metadata, and providers.",
)
async def check_health(
    settings: Settings = Depends(get_current_settings),
) -> HealthResponse:
    search_cb = get_circuit_breaker("search_provider")
    ai_cb = get_circuit_breaker("ai_provider")

    return HealthResponse(
        status="healthy",
        environment=settings.APP_ENV,
        version=settings.APP_VERSION,
        app_name=settings.APP_NAME,
        services=ServiceStatus(
            database="configured",
            cache="configured",
            ai_provider=settings.AI_MODEL_PROVIDER,
            search_provider=settings.SEARCH_PROVIDER,
        ),
        metadata={
            "ai_model": settings.AI_MODEL_NAME,
            "embedding_model": settings.EMBEDDING_MODEL,
            "maintenance_mode": settings.MAINTENANCE_MODE,
            "ai_circuit_breaker": ai_cb.state.value,
            "search_circuit_breaker": search_cb.state.value,
        },
    )
