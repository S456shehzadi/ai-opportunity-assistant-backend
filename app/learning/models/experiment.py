"""A/B testing and experimentation framework models."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    JSON,
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


class ExperimentStatus(StrEnum):
    """Lifecycle status of an A/B experiment."""

    DRAFT = "DRAFT"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    CONCLUDED = "CONCLUDED"


class Experiment(Base, UUIDMixin, TimestampMixin):
    """A/B experiment testing presentation, query formulation, or notification grouping."""

    __tablename__ = "experiments"

    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    hypothesis: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[ExperimentStatus] = mapped_column(
        Enum(ExperimentStatus, native_enum=False, length=50),
        default=ExperimentStatus.DRAFT,
        nullable=False,
        index=True,
    )
    target_metric: Mapped[str] = mapped_column(String(100), nullable=False)
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    variants = relationship(
        "ExperimentVariant", back_populates="experiment", cascade="all, delete-orphan"
    )


class ExperimentVariant(Base, UUIDMixin, TimestampMixin):
    """Specific variant inside an experiment."""

    __tablename__ = "experiment_variants"

    experiment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("experiments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    variant_key: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    traffic_percentage: Mapped[float] = mapped_column(Float, default=50.0, nullable=False)
    configuration: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )

    experiment = relationship("Experiment", back_populates="variants")


class ExperimentAssignment(Base, UUIDMixin, TimestampMixin):
    """Tracks assignment of a user to an experimental variant."""

    __tablename__ = "experiment_assignments"

    experiment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("experiments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    variant_key: Mapped[str] = mapped_column(String(50), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
