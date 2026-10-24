"""Notification entity models for in-app and external delivery tracking."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class NotificationType(StrEnum):
    """Types of user-facing notifications."""

    DEADLINE_APPROACHING = "DEADLINE_APPROACHING"
    DEADLINE_CHANGED = "DEADLINE_CHANGED"
    REQUIREMENT_CHANGED = "REQUIREMENT_CHANGED"
    ELIGIBILITY_STATUS_CHANGED = "ELIGIBILITY_STATUS_CHANGED"
    FUNDING_CHANGED = "FUNDING_CHANGED"
    STATUS_CHANGED = "STATUS_CHANGED"
    NEW_MATCHING_OPPORTUNITY = "NEW_MATCHING_OPPORTUNITY"
    APPLICATION_OPENED = "APPLICATION_OPENED"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    SYSTEM = "SYSTEM"


class NotificationPriority(StrEnum):
    """Priority level determining delivery urgency and fatigue threshold."""

    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"


class DeliveryChannel(StrEnum):
    """Supported delivery channels."""

    IN_APP = "IN_APP"
    PUSH = "PUSH"
    EMAIL = "EMAIL"


class DeliveryStatus(StrEnum):
    """Delivery status per channel."""

    PENDING = "PENDING"
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    SUPPRESSED = "SUPPRESSED"


class Notification(Base, UUIDMixin, TimestampMixin):
    """In-app and channel-agnostic notification event for a specific user."""

    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    opportunity_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    change_event_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("opportunity_change_events.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    notification_type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, native_enum=False, length=50),
        nullable=False,
        index=True,
    )
    priority: Mapped[NotificationPriority] = mapped_column(
        Enum(NotificationPriority, native_enum=False, length=20),
        default=NotificationPriority.NORMAL,
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    deduplication_key: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    opportunity = relationship("Opportunity", foreign_keys=[opportunity_id])
    change_event = relationship("OpportunityChangeEvent", foreign_keys=[change_event_id])
    deliveries = relationship(
        "NotificationDelivery",
        back_populates="notification",
        cascade="all, delete-orphan",
    )


class NotificationDelivery(Base, UUIDMixin, TimestampMixin):
    """Channel-specific delivery tracking record."""

    __tablename__ = "notification_deliveries"

    notification_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("notifications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel: Mapped[DeliveryChannel] = mapped_column(
        Enum(DeliveryChannel, native_enum=False, length=20),
        nullable=False,
    )
    status: Mapped[DeliveryStatus] = mapped_column(
        Enum(DeliveryStatus, native_enum=False, length=20),
        default=DeliveryStatus.PENDING,
        nullable=False,
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    notification = relationship("Notification", back_populates="deliveries")
