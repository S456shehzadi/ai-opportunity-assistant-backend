"""Centralized error taxonomy and recurring error cluster models."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class ErrorTaxonomyType(StrEnum):
    """Centralized taxonomy of failure categories across the platform."""

    SEARCH_RELEVANCE_ERROR = "SEARCH_RELEVANCE_ERROR"
    SEARCH_RECALL_ERROR = "SEARCH_RECALL_ERROR"
    RETRIEVAL_ERROR = "RETRIEVAL_ERROR"
    EXTRACTION_ERROR = "EXTRACTION_ERROR"
    MISSING_FIELD_ERROR = "MISSING_FIELD_ERROR"
    HALLUCINATED_FIELD_ERROR = "HALLUCINATED_FIELD_ERROR"
    ELIGIBILITY_ERROR = "ELIGIBILITY_ERROR"
    RANKING_ERROR = "RANKING_ERROR"
    GROUNDING_ERROR = "GROUNDING_ERROR"
    CITATION_ERROR = "CITATION_ERROR"
    DEADLINE_ERROR = "DEADLINE_ERROR"
    FUNDING_ERROR = "FUNDING_ERROR"
    SOURCE_ERROR = "SOURCE_ERROR"
    DUPLICATION_ERROR = "DUPLICATION_ERROR"
    STALE_DATA_ERROR = "STALE_DATA_ERROR"
    NOTIFICATION_ERROR = "NOTIFICATION_ERROR"


class ErrorCluster(Base, UUIDMixin, TimestampMixin):
    """Aggregated group of recurring errors sharing root causes or patterns."""

    __tablename__ = "error_clusters"

    error_type: Mapped[ErrorTaxonomyType] = mapped_column(
        Enum(ErrorTaxonomyType, native_enum=False, length=50),
        nullable=False,
        index=True,
    )
    fingerprint: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    affected_field: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    occurrence_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    sample_feedback_ids: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE", nullable=False, index=True)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
