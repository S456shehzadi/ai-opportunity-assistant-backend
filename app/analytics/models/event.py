"""Product analytics event model."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


class EventType(StrEnum):
    """Categorized behavioral and product events."""

    SEARCH_STARTED = "SEARCH_STARTED"
    SEARCH_COMPLETED = "SEARCH_COMPLETED"
    SEARCH_FAILED = "SEARCH_FAILED"
    OPPORTUNITY_VIEWED = "OPPORTUNITY_VIEWED"
    OPPORTUNITY_SAVED = "OPPORTUNITY_SAVED"
    OPPORTUNITY_UNSAVED = "OPPORTUNITY_UNSAVED"
    APPLICATION_LINK_OPENED = "APPLICATION_LINK_OPENED"
    SOURCE_OPENED = "SOURCE_OPENED"
    ELIGIBILITY_VIEWED = "ELIGIBILITY_VIEWED"
    AI_RESPONSE_VIEWED = "AI_RESPONSE_VIEWED"
    AI_RESPONSE_EXPANDED = "AI_RESPONSE_EXPANDED"
    FOLLOW_UP_QUERY = "FOLLOW_UP_QUERY"
    NOTIFICATION_OPENED = "NOTIFICATION_OPENED"
    NOTIFICATION_DISMISSED = "NOTIFICATION_DISMISSED"
    NOTIFICATION_MARKED_READ = "NOTIFICATION_MARKED_READ"
    FEEDBACK_SUBMITTED = "FEEDBACK_SUBMITTED"


class UserEvent(Base, UUIDMixin):
    """Structured product analytics event tracking user behavior without private secrets."""

    __tablename__ = "user_events"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    anonymous_session_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    event_type: Mapped[EventType] = mapped_column(
        Enum(EventType, native_enum=False, length=50),
        nullable=False,
        index=True,
    )
    event_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    entity_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )
    request_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    session_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    application_version: Mapped[str] = mapped_column(String(50), default="1.0.0", nullable=False)
    platform: Mapped[str] = mapped_column(String(50), default="mobile", nullable=False)
    locale: Mapped[str] = mapped_column(String(20), default="en", nullable=False)

    # Relationship
    user = relationship("User", foreign_keys=[user_id])
