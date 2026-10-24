"""REST API endpoints for product analytics and system overview metrics."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.schemas.event import (
    AnalyticsOverviewResponse,
    UserEventCreate,
    UserEventResponse,
)
from app.analytics.services.analytics_service import AnalyticsService
from app.api.dependencies import get_current_reviewer_user, get_current_user, get_db
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["Product Analytics"])
analytics_service = AnalyticsService()


@router.post(
    "/analytics/events",
    response_model=UserEventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a client product behavioral event",
)
async def track_user_event(
    payload: UserEventCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserEventResponse:
    """Ingests client events with automated privacy and secret scrubbing."""
    event = await analytics_service.track_event(
        db=db,
        event=payload,
        user_id=current_user.id,
    )
    return UserEventResponse.model_validate(event)


@router.get(
    "/analytics/overview",
    response_model=AnalyticsOverviewResponse,
    summary="Retrieve high-level system quality overview (Reviewer/Admin only)",
)
async def get_analytics_overview(
    current_reviewer: User = Depends(get_current_reviewer_user),
    db: AsyncSession = Depends(get_db),
) -> AnalyticsOverviewResponse:
    """Provides high-level system health metrics. Requires reviewer privileges."""
    return await analytics_service.get_overview_metrics(db)
