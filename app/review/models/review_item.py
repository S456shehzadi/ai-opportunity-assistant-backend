"""Human review queue item model."""

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


class ReviewCategory(StrEnum):
    """Categories of candidate items requiring human verification."""

    OPPORTUNITY_EXTRACTION = "OPPORTUNITY_EXTRACTION"
    ELIGIBILITY = "ELIGIBILITY"
    RANKING = "RANKING"
    AI_RESPONSE = "AI_RESPONSE"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"
    DEADLINE = "DEADLINE"
    FUNDING = "FUNDING"
    USER_REPORTED_ERROR = "USER_REPORTED_ERROR"


class ReviewStatus(StrEnum):
    """Lifecycle status for human-in-the-loop review workflow."""

    PENDING = "PENDING"
    IN_REVIEW = "IN_REVIEW"
    VERIFIED = "VERIFIED"
    CORRECTED = "CORRECTED"
    REJECTED = "REJECTED"
    DUPLICATE = "DUPLICATE"
    NEEDS_MORE_EVIDENCE = "NEEDS_MORE_EVIDENCE"


class ReviewQueueItem(Base, UUIDMixin, TimestampMixin):
    """Queue entry containing an unverified claim, extraction, or reported error."""

    __tablename__ = "review_queue_items"

    category: Mapped[ReviewCategory] = mapped_column(
        Enum(ReviewCategory, native_enum=False, length=50),
        nullable=False,
        index=True,
    )
    entity_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    evidence_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    evidence_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    current_system_output: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    user_feedback_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("feedback_records.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    priority: Mapped[str] = mapped_column(String(20), default="NORMAL", nullable=False, index=True)
    status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus, native_enum=False, length=50),
        default=ReviewStatus.PENDING,
        nullable=False,
        index=True,
    )
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    assigned_reviewer = relationship("User", foreign_keys=[assigned_to])
    feedback = relationship("FeedbackRecord", foreign_keys=[user_feedback_id])
    corrections = relationship(
        "HumanCorrection", back_populates="review_item", cascade="all, delete-orphan"
    )
