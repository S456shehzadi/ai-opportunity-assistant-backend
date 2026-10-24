"""Subscription models for monitoring opportunities and search queries."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class MonitoringFrequency(StrEnum):
    """Execution frequency for recurring monitoring checks."""

    DAILY = "DAILY"
    EVERY_3_DAYS = "EVERY_3_DAYS"
    WEEKLY = "WEEKLY"
    BIWEEKLY = "BIWEEKLY"
    MONTHLY = "MONTHLY"


class MonitoringStatus(StrEnum):
    """Lifecycle status of a monitoring subscription or task."""

    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    ERROR = "ERROR"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    DISABLED = "DISABLED"


class OpportunitySubscription(Base, UUIDMixin, TimestampMixin):
    """User subscription to continuous monitoring of a specific opportunity."""

    __tablename__ = "opportunity_subscriptions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    monitoring_frequency: Mapped[MonitoringFrequency] = mapped_column(
        Enum(MonitoringFrequency, native_enum=False, length=50),
        default=MonitoringFrequency.DAILY,
        nullable=False,
    )
    monitoring_status: Mapped[MonitoringStatus] = mapped_column(
        Enum(MonitoringStatus, native_enum=False, length=50),
        default=MonitoringStatus.ACTIVE,
        nullable=False,
        index=True,
    )
    last_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    next_check_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    notification_channels: Mapped[list[str]] = mapped_column(
        JSON,
        default=lambda: ["IN_APP"],
        nullable=False,
    )
    important_only: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deadline_alerts_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    funding_change_alerts_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    requirement_change_alerts_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    status_change_alerts_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    opportunity = relationship("Opportunity", foreign_keys=[opportunity_id])


class SearchSubscription(Base, UUIDMixin, TimestampMixin):
    """User subscription to continuous monitoring of a search query."""

    __tablename__ = "search_subscriptions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    query: Mapped[str] = mapped_column(String(500), nullable=False)
    normalized_search_intent: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    filters: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    monitoring_frequency: Mapped[MonitoringFrequency] = mapped_column(
        Enum(MonitoringFrequency, native_enum=False, length=50),
        default=MonitoringFrequency.WEEKLY,
        nullable=False,
    )
    monitoring_status: Mapped[MonitoringStatus] = mapped_column(
        Enum(MonitoringStatus, native_enum=False, length=50),
        default=MonitoringStatus.ACTIVE,
        nullable=False,
        index=True,
    )
    last_searched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    next_search_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    last_result_fingerprint: Mapped[str | None] = mapped_column(String(255), nullable=True)
    known_opportunity_ids: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
