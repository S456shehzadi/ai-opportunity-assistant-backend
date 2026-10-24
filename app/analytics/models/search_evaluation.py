"""Search evaluation and performance record model."""

from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, Boolean, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class SearchEvaluationRecord(Base, UUIDMixin, TimestampMixin):
    """Auditable metric snapshot capturing search quality, latency, and domain diversity."""

    __tablename__ = "search_evaluation_records"

    query: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    search_session_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    results_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unique_domains_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duplicate_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    no_results: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    source_quality_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
