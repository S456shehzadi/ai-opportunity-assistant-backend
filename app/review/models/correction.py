"""Human correction model recording reviewer corrections with provenance."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import (
    JSON,
    ForeignKey,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class HumanCorrection(Base, UUIDMixin, TimestampMixin):
    """Immutable correction record providing verified training/evaluation ground truth."""

    __tablename__ = "human_corrections"

    review_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("review_queue_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    original_value: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    corrected_value: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    evidence: Mapped[str] = mapped_column(Text, nullable=False)
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reason: Mapped[str] = mapped_column(String(255), default="", nullable=False)

    # Relationships
    review_item = relationship("ReviewQueueItem", back_populates="corrections")
    reviewer = relationship("User", foreign_keys=[reviewer_id])
