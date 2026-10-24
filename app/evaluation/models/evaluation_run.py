"""Evaluation run tracking model for reproducible benchmarks."""

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


class EvaluationStatus(StrEnum):
    """Lifecycle status of a reproducible benchmark execution."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class EvaluationRun(Base, UUIDMixin, TimestampMixin):
    """Auditable execution record pairing a model/prompt version with a dataset version."""

    __tablename__ = "evaluation_runs"

    model_provider: Mapped[str] = mapped_column(String(50), default="deterministic", nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), default="rules", nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), default="1.0.0", nullable=False)
    prompt_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    dataset_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("dataset_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    configuration: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    metrics_summary: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    claim_evaluations: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    status: Mapped[EvaluationStatus] = mapped_column(
        Enum(EvaluationStatus, native_enum=False, length=50),
        default=EvaluationStatus.PENDING,
        nullable=False,
        index=True,
    )
    code_version: Mapped[str] = mapped_column(String(50), default="1.0.0", nullable=False)
    environment: Mapped[str] = mapped_column(String(50), default="test", nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    dataset_version = relationship("DatasetVersion")
