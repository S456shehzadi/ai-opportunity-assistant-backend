"""REST API endpoints for submitting and inspecting explicit user feedback."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_reviewer_user, get_current_user, get_db
from app.feedback.models.feedback import FeedbackTargetType
from app.feedback.schemas.feedback import FeedbackCreate, FeedbackResponse
from app.feedback.services.feedback_service import FeedbackService
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["User Feedback"])
feedback_service = FeedbackService()


@router.post(
    "/feedback",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit explicit user feedback for a platform component",
)
async def submit_feedback(
    payload: FeedbackCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FeedbackResponse:
    """Stores user feedback and automatically enqueues negative signals for human review."""
    record = await feedback_service.submit_feedback(
        db=db,
        user_id=current_user.id,
        payload=payload,
    )
    return FeedbackResponse.model_validate(record)


@router.get(
    "/feedback",
    response_model=list[FeedbackResponse],
    summary="List feedback for a target entity (Reviewer/Admin only)",
)
async def list_target_feedback(
    target_type: FeedbackTargetType = Query(..., description="Target category"),
    target_id: str = Query(..., description="Target entity ID"),
    current_reviewer: User = Depends(get_current_reviewer_user),
    db: AsyncSession = Depends(get_db),
) -> list[FeedbackResponse]:
    """Retrieves feedback records for a target. Requires reviewer privileges."""
    records = await feedback_service.get_feedback_for_target(
        db=db,
        target_type=target_type,
        target_id=target_id,
    )
    return [FeedbackResponse.model_validate(r) for r in records]
