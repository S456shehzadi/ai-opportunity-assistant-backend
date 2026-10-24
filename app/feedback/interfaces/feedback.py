"""Feedback service interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.feedback.models.feedback import FeedbackRecord, FeedbackTargetType
from app.feedback.schemas.feedback import FeedbackCreate


class IFeedbackService(ABC):
    """Abstract interface for ingesting feedback and dispatching review candidates."""

    @abstractmethod
    async def submit_feedback(
        self,
        db: AsyncSession,
        user_id: UUID,
        payload: FeedbackCreate,
    ) -> FeedbackRecord:
        """Processes and stores user feedback, dispatching review tasks when negative."""
        pass

    @abstractmethod
    async def get_feedback_for_target(
        self,
        db: AsyncSession,
        target_type: FeedbackTargetType,
        target_id: str,
    ) -> list[FeedbackRecord]:
        """Retrieves feedback records associated with a specific entity."""
        pass
