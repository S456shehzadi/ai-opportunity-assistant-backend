"""Opportunity change event models tracking verified semantic differences."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class OpportunityChangeType(StrEnum):
    """Categorization of verified opportunity modifications."""

    NEW_OPPORTUNITY = "NEW_OPPORTUNITY"
    DEADLINE_CHANGED = "DEADLINE_CHANGED"
    DEADLINE_EXTENDED = "DEADLINE_EXTENDED"
    DEADLINE_SHORTENED = "DEADLINE_SHORTENED"
    APPLICATION_STATUS_CHANGED = "APPLICATION_STATUS_CHANGED"
    PROGRAM_OPENED = "PROGRAM_OPENED"
    PROGRAM_CLOSED = "PROGRAM_CLOSED"
    PROGRAM_PAUSED = "PROGRAM_PAUSED"
    FUNDING_CHANGED = "FUNDING_CHANGED"
    STIPEND_CHANGED = "STIPEND_CHANGED"
    TUITION_COVERAGE_CHANGED = "TUITION_COVERAGE_CHANGED"
    TRAVEL_SUPPORT_CHANGED = "TRAVEL_SUPPORT_CHANGED"
    ACCOMMODATION_SUPPORT_CHANGED = "ACCOMMODATION_SUPPORT_CHANGED"
    ELIGIBILITY_CHANGED = "ELIGIBILITY_CHANGED"
    NATIONALITY_ELIGIBILITY_CHANGED = "NATIONALITY_ELIGIBILITY_CHANGED"
    DEGREE_REQUIREMENT_CHANGED = "DEGREE_REQUIREMENT_CHANGED"
    FIELD_REQUIREMENT_CHANGED = "FIELD_REQUIREMENT_CHANGED"
    ACADEMIC_REQUIREMENT_CHANGED = "ACADEMIC_REQUIREMENT_CHANGED"
    LANGUAGE_REQUIREMENT_CHANGED = "LANGUAGE_REQUIREMENT_CHANGED"
    TEST_REQUIREMENT_CHANGED = "TEST_REQUIREMENT_CHANGED"
    AGE_REQUIREMENT_CHANGED = "AGE_REQUIREMENT_CHANGED"
    WORK_EXPERIENCE_REQUIREMENT_CHANGED = "WORK_EXPERIENCE_REQUIREMENT_CHANGED"
    APPLICATION_FEE_CHANGED = "APPLICATION_FEE_CHANGED"
    APPLICATION_URL_CHANGED = "APPLICATION_URL_CHANGED"
    PROGRAM_DURATION_CHANGED = "PROGRAM_DURATION_CHANGED"
    IMPORTANT_SOURCE_UPDATED = "IMPORTANT_SOURCE_UPDATED"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    SOURCE_RESTORED = "SOURCE_RESTORED"
    OPPORTUNITY_REMOVED = "OPPORTUNITY_REMOVED"


class OpportunityChangeEvent(Base, UUIDMixin, TimestampMixin):
    """Auditable, immutable record of an observed opportunity modification."""

    __tablename__ = "opportunity_change_events"

    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("opportunity_sources.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    change_type: Mapped[OpportunityChangeType] = mapped_column(
        Enum(OpportunityChangeType, native_enum=False, length=50),
        nullable=False,
        index=True,
    )
    affected_field: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    old_value: Mapped[Any] = mapped_column(JSON, nullable=True)
    new_value: Mapped[Any] = mapped_column(JSON, nullable=True)
    evidence: Mapped[str] = mapped_column(Text, default="", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    source_trust: Mapped[str] = mapped_column(String(50), default="HIGH", nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    notification_priority: Mapped[str] = mapped_column(
        String(20), default="NORMAL", nullable=False, index=True
    )
    processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Relationship
    opportunity = relationship("Opportunity", foreign_keys=[opportunity_id])
