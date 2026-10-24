"""Analytics service interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.models.event import UserEvent
from app.analytics.models.search_evaluation import SearchEvaluationRecord
from app.analytics.schemas.event import AnalyticsOverviewResponse, UserEventCreate


class IAnalyticsService(ABC):
    """Interface for logging sanitized events and generating system health metrics."""

    @abstractmethod
    async def track_event(
        self,
        db: AsyncSession,
        event: UserEventCreate,
        user_id: UUID | None = None,
    ) -> UserEvent:
        """Sanitizes and saves an analytics event."""
        pass

    @abstractmethod
    async def track_search_evaluation(
        self,
        db: AsyncSession,
        record: SearchEvaluationRecord,
    ) -> SearchEvaluationRecord:
        """Stores a search evaluation performance snapshot."""
        pass

    @abstractmethod
    async def get_overview_metrics(
        self,
        db: AsyncSession,
    ) -> AnalyticsOverviewResponse:
        """Aggregates high-level system metrics without leaking PII."""
        pass
