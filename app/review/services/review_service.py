"""Human review service orchestrating verification tasks and auditable corrections."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.review.interfaces.review import IReviewService
from app.review.models.correction import HumanCorrection
from app.review.models.review_item import ReviewCategory, ReviewQueueItem, ReviewStatus
from app.review.schemas.review import ReviewItemCreate, ReviewResolutionCreate

logger = logging.getLogger(__name__)


class ReviewService(IReviewService):
    """Manages the human review queue, assignments, and verified ground-truth corrections."""

    async def create_review_item(
        self,
        db: AsyncSession,
        payload: ReviewItemCreate,
    ) -> ReviewQueueItem:
        """Enqueues an item for human review."""
        item = ReviewQueueItem(
            category=payload.category,
            entity_id=payload.entity_id,
            reason=payload.reason,
            evidence_text=payload.evidence_text,
            evidence_url=payload.evidence_url,
            current_system_output=payload.current_system_output,
            user_feedback_id=payload.user_feedback_id,
            priority=payload.priority,
            status=ReviewStatus.PENDING,
        )
        db.add(item)
        await db.commit()
        await db.refresh(item)
        return item

    async def list_review_items(
        self,
        db: AsyncSession,
        category: ReviewCategory | None = None,
        status: ReviewStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ReviewQueueItem]:
        """Queries review items with filtering and pagination."""
        query = select(ReviewQueueItem).options(selectinload(ReviewQueueItem.corrections))

        if category is not None:
            query = query.where(ReviewQueueItem.category == category)
        if status is not None:
            query = query.where(ReviewQueueItem.status == status)

        query = query.order_by(ReviewQueueItem.created_at.desc()).offset(offset).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_review_item(
        self,
        db: AsyncSession,
        item_id: UUID,
    ) -> ReviewQueueItem | None:
        """Retrieves a single review item with correction history."""
        query = (
            select(ReviewQueueItem)
            .options(selectinload(ReviewQueueItem.corrections))
            .where(ReviewQueueItem.id == item_id)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def assign_item(
        self,
        db: AsyncSession,
        item_id: UUID,
        reviewer_id: UUID,
    ) -> ReviewQueueItem | None:
        """Assigns an item to a reviewer and sets status to IN_REVIEW."""
        item = await self.get_review_item(db, item_id)
        if not item:
            return None

        item.assigned_to = reviewer_id
        item.status = ReviewStatus.IN_REVIEW
        await db.commit()
        return await self.get_review_item(db, item_id)

    async def resolve_review_item(
        self,
        db: AsyncSession,
        item_id: UUID,
        reviewer_id: UUID,
        payload: ReviewResolutionCreate,
    ) -> ReviewQueueItem:
        """Resolves a review item, creating a HumanCorrection record if modified."""
        item = await self.get_review_item(db, item_id)
        if not item:
            raise ValueError(f"Review item {item_id} not found")

        now = datetime.now(UTC)
        item.status = payload.status
        item.resolved_at = now
        item.resolution_notes = payload.resolution_notes
        item.assigned_to = reviewer_id

        # If corrected, record immutable HumanCorrection
        if payload.status == ReviewStatus.CORRECTED and payload.corrected_value:
            correction = HumanCorrection(
                review_id=item.id,
                original_value=item.current_system_output,
                corrected_value=payload.corrected_value,
                evidence=payload.evidence or item.evidence_text,
                reviewer_id=reviewer_id,
                reason=payload.resolution_notes or item.reason,
            )
            item.corrections.append(correction)
            db.add(correction)

        await db.commit()
        reloaded = await self.get_review_item(db, item_id)
        return reloaded or item

    # Alias for endpoint compatibility
    resolve_item = resolve_review_item
