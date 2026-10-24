"""Feedback service orchestrating feedback ingestion and human review candidate creation."""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.models.event import EventType
from app.analytics.schemas.event import UserEventCreate
from app.analytics.services.analytics_service import AnalyticsService
from app.evaluation.models.taxonomy import ErrorTaxonomyType
from app.evaluation.services.error_cluster_service import ErrorClusterService
from app.feedback.interfaces.feedback import IFeedbackService
from app.feedback.models.feedback import (
    FeedbackRecord,
    FeedbackTargetType,
    FeedbackType,
)
from app.feedback.schemas.feedback import FeedbackCreate
from app.review.models.review_item import ReviewCategory
from app.review.schemas.review import ReviewItemCreate
from app.review.services.review_service import ReviewService

logger = logging.getLogger(__name__)


class FeedbackService(IFeedbackService):
    """Handles explicit user feedback and routes failure signals into the review queue."""

    def __init__(
        self,
        review_service: ReviewService | None = None,
        error_cluster_service: ErrorClusterService | None = None,
        analytics_service: AnalyticsService | None = None,
    ) -> None:
        self.review_service = review_service or ReviewService()
        self.error_cluster_service = error_cluster_service or ErrorClusterService()
        self.analytics_service = analytics_service or AnalyticsService()

    async def submit_feedback(
        self,
        db: AsyncSession,
        user_id: UUID,
        payload: FeedbackCreate,
    ) -> FeedbackRecord:
        """Stores feedback, logs analytics event, and queues review if error indicated."""
        record = FeedbackRecord(
            user_id=user_id,
            target_type=payload.target_type,
            target_id=payload.target_id,
            feedback_type=payload.feedback_type,
            reason=payload.reason,
            comment=payload.comment,
            context_snapshot=payload.context_snapshot,
            status="NEW",
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)

        # Log sanitized product event
        await self.analytics_service.track_event(
            db=db,
            user_id=user_id,
            event=UserEventCreate(
                event_type=EventType.FEEDBACK_SUBMITTED,
                entity_type=str(payload.target_type.value),
                entity_id=payload.target_id,
                metadata_json={
                    "feedback_type": str(payload.feedback_type.value),
                    "reason": payload.reason,
                },
            ),
        )

        # Route to Review Queue if error or negative feedback
        negative_types = {
            FeedbackType.NOT_HELPFUL,
            FeedbackType.NOT_RELEVANT,
            FeedbackType.INCORRECT,
            FeedbackType.OUTDATED,
            FeedbackType.DUPLICATE,
            FeedbackType.WRONG_ELIGIBILITY,
            FeedbackType.WRONG_DEADLINE,
            FeedbackType.WRONG_FUNDING,
            FeedbackType.WRONG_SOURCE,
            FeedbackType.MISSING_INFORMATION,
        }

        if payload.feedback_type in negative_types:
            category = self._resolve_review_category(payload.target_type, payload.feedback_type)
            is_high_priority = (
                "WRONG" in payload.feedback_type.value
                or payload.feedback_type == FeedbackType.INCORRECT
            )
            priority = "HIGH" if is_high_priority else "NORMAL"
            reason_text = f"User report: {payload.feedback_type.value} ({payload.reason or 'none'})"

            await self.review_service.create_review_item(
                db=db,
                payload=ReviewItemCreate(
                    category=category,
                    entity_id=payload.target_id,
                    reason=reason_text,
                    evidence_text=payload.comment or "",
                    current_system_output=payload.context_snapshot,
                    priority=priority,
                    user_feedback_id=record.id,
                ),
            )

            # Record into Error Cluster
            error_tax = self._resolve_error_taxonomy(payload.feedback_type)
            await self.error_cluster_service.record_error(
                db=db,
                error_type=error_tax,
                domain=payload.context_snapshot.get("domain"),
                affected_field=payload.reason,
                feedback_id=record.id,
            )

        return record

    async def get_feedback_for_target(
        self,
        db: AsyncSession,
        target_type: FeedbackTargetType,
        target_id: str,
    ) -> list[FeedbackRecord]:
        """Queries feedback records for a specific target entity."""
        query = (
            select(FeedbackRecord)
            .where(
                FeedbackRecord.target_type == target_type,
                FeedbackRecord.target_id == target_id,
            )
            .order_by(FeedbackRecord.created_at.desc())
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    def _resolve_review_category(
        target_type: FeedbackTargetType,
        feedback_type: FeedbackType,
    ) -> ReviewCategory:
        """Maps user feedback context to human review workflow categories."""
        if (
            target_type == FeedbackTargetType.ELIGIBILITY
            or feedback_type == FeedbackType.WRONG_ELIGIBILITY
        ):
            return ReviewCategory.ELIGIBILITY
        if target_type == FeedbackTargetType.ASSISTANT_RESPONSE:
            return ReviewCategory.AI_RESPONSE
        if target_type == FeedbackTargetType.RANKING:
            return ReviewCategory.RANKING
        if feedback_type == FeedbackType.WRONG_DEADLINE:
            return ReviewCategory.DEADLINE
        if feedback_type == FeedbackType.WRONG_FUNDING:
            return ReviewCategory.FUNDING
        if feedback_type == FeedbackType.WRONG_SOURCE:
            return ReviewCategory.SOURCE_CONFLICT

        return ReviewCategory.OPPORTUNITY_EXTRACTION

    @staticmethod
    def _resolve_error_taxonomy(feedback_type: FeedbackType) -> ErrorTaxonomyType:
        """Categorizes feedback type into centralized error taxonomy."""
        mapping = {
            FeedbackType.WRONG_DEADLINE: ErrorTaxonomyType.DEADLINE_ERROR,
            FeedbackType.WRONG_FUNDING: ErrorTaxonomyType.FUNDING_ERROR,
            FeedbackType.WRONG_ELIGIBILITY: ErrorTaxonomyType.ELIGIBILITY_ERROR,
            FeedbackType.WRONG_SOURCE: ErrorTaxonomyType.SOURCE_ERROR,
            FeedbackType.NOT_RELEVANT: ErrorTaxonomyType.RANKING_ERROR,
            FeedbackType.DUPLICATE: ErrorTaxonomyType.DUPLICATION_ERROR,
            FeedbackType.OUTDATED: ErrorTaxonomyType.STALE_DATA_ERROR,
            FeedbackType.MISSING_INFORMATION: ErrorTaxonomyType.MISSING_FIELD_ERROR,
            FeedbackType.INCORRECT: ErrorTaxonomyType.EXTRACTION_ERROR,
        }
        return mapping.get(feedback_type, ErrorTaxonomyType.EXTRACTION_ERROR)
