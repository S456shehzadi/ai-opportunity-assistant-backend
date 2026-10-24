"""REST API endpoints for human-in-the-loop review queue and corrections."""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_reviewer_user, get_db
from app.models.user import User
from app.review.models.review_item import ReviewCategory, ReviewStatus
from app.review.schemas.review import ReviewItemResponse, ReviewResolutionCreate
from app.review.services.review_service import ReviewService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["Human Review Queue"])
review_service = ReviewService()


@router.get(
    "/review/queue",
    response_model=list[ReviewItemResponse],
    summary="List items in human review queue (Reviewer/Admin only)",
)
async def list_review_queue(
    category: ReviewCategory | None = Query(default=None),
    status: ReviewStatus | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_reviewer: User = Depends(get_current_reviewer_user),
    db: AsyncSession = Depends(get_db),
) -> list[ReviewItemResponse]:
    """Lists verification candidates. Requires reviewer role."""
    items = await review_service.list_review_items(
        db=db,
        category=category,
        status=status,
        limit=limit,
        offset=offset,
    )
    return [ReviewItemResponse.model_validate(i) for i in items]


@router.get(
    "/review/queue/{id}",
    response_model=ReviewItemResponse,
    summary="Get single review item details with audit history",
)
async def get_review_queue_item(
    id: UUID,
    current_reviewer: User = Depends(get_current_reviewer_user),
    db: AsyncSession = Depends(get_db),
) -> ReviewItemResponse:
    """Inspects review item. Requires reviewer role."""
    item = await review_service.get_review_item(db=db, item_id=id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review item {id} not found",
        )
    return ReviewItemResponse.model_validate(item)


@router.post(
    "/review/queue/{id}/assign",
    response_model=ReviewItemResponse,
    summary="Assign review item to current reviewer",
)
async def assign_review_queue_item(
    id: UUID,
    current_reviewer: User = Depends(get_current_reviewer_user),
    db: AsyncSession = Depends(get_db),
) -> ReviewItemResponse:
    """Assigns item to current reviewer."""
    item = await review_service.assign_item(
        db=db,
        item_id=id,
        reviewer_id=current_reviewer.id,
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review item {id} not found",
        )
    return ReviewItemResponse.model_validate(item)


@router.post(
    "/review/queue/{id}/resolve",
    response_model=ReviewItemResponse,
    summary="Resolve a review item with verification or correction",
)
async def resolve_review_queue_item(
    id: UUID,
    payload: ReviewResolutionCreate,
    current_reviewer: User = Depends(get_current_reviewer_user),
    db: AsyncSession = Depends(get_db),
) -> ReviewItemResponse:
    """Submits review decision, creating HumanCorrection if modified."""
    try:
        item = await review_service.resolve_item(
            db=db,
            item_id=id,
            reviewer_id=current_reviewer.id,
            payload=payload,
        )
        return ReviewItemResponse.model_validate(item)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
