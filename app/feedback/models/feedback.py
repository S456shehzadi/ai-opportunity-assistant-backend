"""Feedback database models capturing explicit user evaluations and signals."""

from __future__ import annotations

import uuid
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    JSON,
    Enum,
    ForeignKey,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class FeedbackType(StrEnum):
    """Concise classification of user feedback."""

    HELPFUL = "HELPFUL"
    NOT_HELPFUL = "NOT_HELPFUL"
    RELEVANT = "RELEVANT"
    NOT_RELEVANT = "NOT_RELEVANT"
    INCORRECT = "INCORRECT"
    OUTDATED = "OUTDATED"
    DUPLICATE = "DUPLICATE"
    WRONG_ELIGIBILITY = "WRONG_ELIGIBILITY"
    WRONG_DEADLINE = "WRONG_DEADLINE"
    WRONG_FUNDING = "WRONG_FUNDING"
    WRONG_SOURCE = "WRONG_SOURCE"
    MISSING_INFORMATION = "MISSING_INFORMATION"


class FeedbackTargetType(StrEnum):
    """Entity or component to which feedback is attached."""

    OPPORTUNITY = "OPPORTUNITY"
    ASSISTANT_RESPONSE = "ASSISTANT_RESPONSE"
    ELIGIBILITY = "ELIGIBILITY"
    SEARCH = "SEARCH"
    RANKING = "RANKING"
    NOTIFICATION = "NOTIFICATION"
    CHANGE_EVENT = "CHANGE_EVENT"


class FeedbackRecord(Base, UUIDMixin, TimestampMixin):
    """Auditable feedback record submitted by a user for system improvement."""

    __tablename__ = "feedback_records"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_type: Mapped[FeedbackTargetType] = mapped_column(
        Enum(FeedbackTargetType, native_enum=False, length=50),
        nullable=False,
        index=True,
    )
    target_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    feedback_type: Mapped[FeedbackType] = mapped_column(
        Enum(FeedbackType, native_enum=False, length=50),
        nullable=False,
        index=True,
    )
    reason: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    context_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(50), default="NEW", nullable=False, index=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
