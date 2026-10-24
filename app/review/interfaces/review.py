"""Review service interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.review.models.review_item import ReviewCategory, ReviewQueueItem, ReviewStatus
from app.review.schemas.review import ReviewItemCreate, ReviewResolutionCreate


class IReviewService(ABC):
    """Interface for managing human review workflow and recording corrections."""

    @abstractmethod
    async def create_review_item(
        self,
        db: AsyncSession,
        payload: ReviewItemCreate,
    ) -> ReviewQueueItem:
        pass

    @abstractmethod
    async def list_review_items(
        self,
        db: AsyncSession,
        category: ReviewCategory | None = None,
        status: ReviewStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ReviewQueueItem]:
        pass

    @abstractmethod
    async def resolve_review_item(
        self,
        db: AsyncSession,
        item_id: UUID,
        reviewer_id: UUID,
        payload: ReviewResolutionCreate,
    ) -> ReviewQueueItem:
        pass
