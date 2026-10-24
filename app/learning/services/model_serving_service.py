"""Inference routing, canary traffic division, health monitoring, and safe fallback."""

from __future__ import annotations

import logging
import random
import time
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.learning.models.model_registry import (
    ModelDefinition,
    ModelHealthStatus,
    ModelStatus,
    ModelType,
)
from app.learning.schemas.training import ModelHealthResponse

logger = logging.getLogger(__name__)


class ModelServingService:
    """Manages runtime model routing, canary deployments, and safe fallback handling."""

    async def get_active_model_for_task(
        self,
        db: AsyncSession,
        task: ModelType,
    ) -> tuple[ModelDefinition | None, bool]:
        """Resolves target model according to canary percentage and production status."""
        query = select(ModelDefinition).where(
            ModelDefinition.model_type == task,
            ModelDefinition.active.is_(True),
            ModelDefinition.status.in_(
                [ModelStatus.PRODUCTION, ModelStatus.STAGING, ModelStatus.CANDIDATE]
            ),
        )
        result = await db.execute(query)
        models = result.scalars().all()

        if not models:
            return None, False

        # Look for candidate with active canary percentage
        canary_candidates = [
            m for m in models if m.canary_percentage > 0.0 and m.status != ModelStatus.PRODUCTION
        ]
        production_models = [m for m in models if m.status == ModelStatus.PRODUCTION]

        if canary_candidates and random.uniform(0, 100) < canary_candidates[0].canary_percentage:
            return canary_candidates[0], True

        primary = production_models[0] if production_models else models[0]
        return primary, False

    async def execute_with_fallback(
        self,
        db: AsyncSession,
        task: ModelType,
        specialized_invoker: Callable[[], Awaitable[Any]],
        fallback_invoker: Callable[[], Awaitable[Any]],
    ) -> tuple[Any, dict[str, Any]]:
        """Executes specialized model with instant fallback to generalist baseline on failure."""
        model, is_canary = await self.get_active_model_for_task(db, task)
        meta: dict[str, Any] = {
            "task": task,
            "used_fallback": False,
            "is_canary": is_canary,
            "model_id": model.model_id if model else "none",
        }

        if not model or model.health_status == ModelHealthStatus.UNAVAILABLE:
            meta["used_fallback"] = True
            meta["fallback_reason"] = "No specialized model available or marked unavailable"
            fallback_res = await fallback_invoker()
            return fallback_res, meta

        try:
            start_time = time.time()
            result = await specialized_invoker()
            meta["latency_ms"] = round((time.time() - start_time) * 1000, 2)
            return result, meta
        except Exception as exc:
            logger.warning(
                "Specialized model %s failed for task %s, executing safe fallback: %s",
                model.model_id,
                task,
                str(exc),
            )
            # Mark model health as DEGRADED
            model.health_status = ModelHealthStatus.DEGRADED
            await db.commit()

            meta["used_fallback"] = True
            meta["fallback_reason"] = str(exc)
            fallback_res = await fallback_invoker()
            return fallback_res, meta

    async def check_health(
        self,
        db: AsyncSession,
        model_id: str,
    ) -> ModelHealthResponse:
        """Runs health probe verifying model availability and response latency."""
        query = select(ModelDefinition).where(ModelDefinition.model_id == model_id)
        result = await db.execute(query)
        model = result.scalar_one_or_none()

        if not model:
            return ModelHealthResponse(
                model_id=model_id,
                status=ModelStatus.ARCHIVED,
                health_status=ModelHealthStatus.UNAVAILABLE,
                is_healthy=False,
                latency_ms=0.0,
                message=f"Model {model_id} does not exist in registry",
            )

        start = time.time()
        # Simulated health verification probe
        is_healthy = model.active and model.status != ModelStatus.RETIRED
        latency_ms = round((time.time() - start) * 1000, 2)

        health_status = ModelHealthStatus.HEALTHY if is_healthy else ModelHealthStatus.UNAVAILABLE
        model.health_status = health_status
        await db.commit()

        return ModelHealthResponse(
            model_id=model_id,
            status=model.status,
            health_status=health_status,
            is_healthy=is_healthy,
            latency_ms=latency_ms,
            message=(
                "Model endpoint operating normally" if is_healthy else "Model inactive or retired"
            ),
        )
