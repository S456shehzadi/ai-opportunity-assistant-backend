"""Schemas for notifications."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.notifications.models.notification import (
    DeliveryChannel,
    DeliveryStatus,
    NotificationPriority,
    NotificationType,
)


class NotificationBase(BaseModel):
    """Base notification attributes."""

    notification_type: NotificationType
    priority: NotificationPriority = NotificationPriority.NORMAL
    title: str = Field(min_length=1, max_length=255)
    message: str
    opportunity_id: UUID | None = None
    change_event_id: UUID | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class NotificationCreate(NotificationBase):
    """Internal creation payload."""

    user_id: UUID
    deduplication_key: str | None = None


class NotificationDeliveryResponse(BaseModel):
    """Channel delivery status."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    channel: DeliveryChannel
    status: DeliveryStatus
    sent_at: datetime | None = None
    delivered_at: datetime | None = None
    error_message: str | None = None


class NotificationResponse(NotificationBase):
    """User-facing notification object."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    read_at: datetime | None = None
    deduplication_key: str | None = None
    created_at: datetime
    updated_at: datetime
    deliveries: list[NotificationDeliveryResponse] = Field(default_factory=list)


class UnreadCountResponse(BaseModel):
    """Count of unread notifications."""

    unread_count: int
