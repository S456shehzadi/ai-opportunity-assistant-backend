"""Evaluation dataset, versioning, and split models."""

from __future__ import annotations

import uuid
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    JSON,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class SplitType(StrEnum):
    """Dataset partition splits with holdout isolation."""

    TRAIN = "TRAIN"
    VALIDATION = "VALIDATION"
    TEST = "TEST"
    HOLDOUT = "HOLDOUT"


class DatasetQualityStatus(StrEnum):
    """Quality gating status of a dataset version."""

    DRAFT = "DRAFT"
    CURATED = "CURATED"
    VERIFIED = "VERIFIED"


class Dataset(Base, UUIDMixin, TimestampMixin):
    """Logical benchmark dataset definition."""

    __tablename__ = "datasets"

    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    task_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)

    versions = relationship(
        "DatasetVersion", back_populates="dataset", cascade="all, delete-orphan"
    )


class DatasetVersion(Base, UUIDMixin, TimestampMixin):
    """Immutable versioned snapshot of curated examples."""

    __tablename__ = "dataset_versions"

    dataset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_tag: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    example_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    schema_version: Mapped[str] = mapped_column(String(20), default="1.0.0", nullable=False)
    quality_status: Mapped[DatasetQualityStatus] = mapped_column(
        Enum(DatasetQualityStatus, native_enum=False, length=50),
        default=DatasetQualityStatus.DRAFT,
        nullable=False,
    )
    split_counts: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )

    dataset = relationship("Dataset", back_populates="versions")
    examples = relationship(
        "DatasetExample", back_populates="dataset_version", cascade="all, delete-orphan"
    )


class DatasetExample(Base, UUIDMixin, TimestampMixin):
    """Individual benchmark ground-truth example assigned to a split."""

    __tablename__ = "dataset_examples"

    dataset_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("dataset_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    split: Mapped[SplitType] = mapped_column(
        Enum(SplitType, native_enum=False, length=20),
        default=SplitType.TRAIN,
        nullable=False,
        index=True,
    )
    input_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    expected_output: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    provenance_review_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), nullable=True, index=True
    )

    dataset_version = relationship("DatasetVersion", back_populates="examples")
