"""REST API endpoints for user notification center and preference controls."""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db
from app.models.user import User
from app.notifications.schemas.notification import (
    NotificationResponse,
    UnreadCountResponse,
)
from app.notifications.schemas.preference import (
    NotificationPreferenceResponse,
    NotificationPreferenceUpdate,
)
from app.notifications.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["User Notifications"])
notification_service = NotificationService()


@router.get(
    "/notifications",
    response_model=list[NotificationResponse],
    summary="List notifications for the current user",
)
async def get_notifications(
    unread_only: bool = Query(default=False, description="Filter only unread notifications"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[NotificationResponse]:
    """Retrieves notifications with user isolation and pagination."""
    notifications = await notification_service.get_user_notifications(
        db=db,
        user_id=current_user.id,
        unread_only=unread_only,
        limit=limit,
        offset=offset,
    )
    return [NotificationResponse.model_validate(n) for n in notifications]


@router.get(
    "/notifications/unread-count",
    response_model=UnreadCountResponse,
    summary="Get count of unread notifications",
)
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UnreadCountResponse:
    """Returns the total number of unread notifications."""
    count = await notification_service.get_unread_count(db=db, user_id=current_user.id)
    return UnreadCountResponse(unread_count=count)


@router.post(
    "/notifications/{id}/read",
    response_model=NotificationResponse,
    summary="Mark a notification as read",
)
async def mark_notification_as_read(
    id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationResponse:
    """Marks a notification as read, enforcing user ownership."""
    notification = await notification_service.mark_as_read(
        db=db,
        user_id=current_user.id,
        notification_id=id,
    )
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )
    return NotificationResponse.model_validate(notification)


@router.post(
    "/notifications/read-all",
    status_code=status.HTTP_200_OK,
    summary="Mark all user notifications as read",
)
async def mark_all_notifications_as_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    """Marks every unread notification for the user as read."""
    marked_count = await notification_service.mark_all_as_read(
        db=db,
        user_id=current_user.id,
    )
    return {"marked_read": marked_count}


@router.delete(
    "/notifications/{id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a notification",
)
async def delete_notification(
    id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Deletes a notification owned by the current user."""
    deleted = await notification_service.delete_notification(
        db=db,
        user_id=current_user.id,
        notification_id=id,
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )
    return {"status": "deleted", "notification_id": str(id)}


@router.get(
    "/notifications/preferences",
    response_model=NotificationPreferenceResponse,
    summary="Get user notification preferences",
)
async def get_notification_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationPreferenceResponse:
    """Retrieves channel, alert type, and quiet hours configuration."""
    prefs = await notification_service.get_or_create_preferences(
        db=db,
        user_id=current_user.id,
    )
    return NotificationPreferenceResponse.model_validate(prefs)


@router.put(
    "/notifications/preferences",
    response_model=NotificationPreferenceResponse,
    summary="Update user notification preferences",
)
async def update_notification_preferences(
    payload: NotificationPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationPreferenceResponse:
    """Updates user notification preferences."""
    prefs = await notification_service.update_preferences(
        db=db,
        user_id=current_user.id,
        update_data=payload,
    )
    return NotificationPreferenceResponse.model_validate(prefs)
