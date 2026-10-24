"""Monitoring background jobs and execution tracking models."""

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
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class JobType(StrEnum):
    """Types of asynchronous monitoring background tasks."""

    OPPORTUNITY_CHECK = "OPPORTUNITY_CHECK"
    SEARCH_SWEEP = "SEARCH_SWEEP"
    DEADLINE_SWEEP = "DEADLINE_SWEEP"
    NOTIFICATION_DISPATCH = "NOTIFICATION_DISPATCH"


class JobStatus(StrEnum):
    """Lifecycle status of background execution jobs."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    CANCELLED = "CANCELLED"


class MonitoringJob(Base, UUIDMixin, TimestampMixin):
    """Queued or scheduled background monitoring task."""

    __tablename__ = "monitoring_jobs"

    job_type: Mapped[JobType] = mapped_column(
        Enum(JobType, native_enum=False, length=50),
        nullable=False,
        index=True,
    )
    target_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
        index=True,
    )
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, native_enum=False, length=50),
        default=JobStatus.PENDING,
        nullable=False,
        index=True,
    )
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    executions = relationship(
        "MonitoringExecution", back_populates="job", cascade="all, delete-orphan"
    )


class MonitoringExecution(Base, UUIDMixin):
    """Execution run record for audit, observability, and debugging."""

    __tablename__ = "monitoring_executions"

    job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("monitoring_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, native_enum=False, length=50),
        nullable=False,
    )
    result_summary: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    job = relationship("MonitoringJob", back_populates="executions")
