"""Training job lifecycle database model."""

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

from app.learning.models.model_registry import ModelType
from app.models.base import Base, TimestampMixin, UUIDMixin


class TrainingJobStatus(StrEnum):
    """Lifecycle status of an asynchronous training job."""

    QUEUED = "QUEUED"
    PREPARING = "PREPARING"
    RUNNING = "RUNNING"
    EVALUATING = "EVALUATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class TrainingJob(Base, UUIDMixin, TimestampMixin):
    """Asynchronous training/fine-tuning execution job."""

    __tablename__ = "training_jobs"

    job_name: Mapped[str] = mapped_column(String(150), index=True, nullable=False)
    task: Mapped[ModelType] = mapped_column(
        Enum(ModelType, native_enum=False, length=50),
        nullable=False,
        index=True,
    )
    dataset_version_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("dataset_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    base_model: Mapped[str] = mapped_column(String(150), nullable=False)
    training_backend: Mapped[str] = mapped_column(String(50), default="LOCAL", nullable=False)
    hyperparameters: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    resource_limits: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    status: Mapped[TrainingJobStatus] = mapped_column(
        Enum(TrainingJobStatus, native_enum=False, length=50),
        default=TrainingJobStatus.QUEUED,
        nullable=False,
        index=True,
    )
    metrics: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    logs: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    artifacts = relationship(
        "ModelArtifactRecord",
        back_populates="training_job",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
