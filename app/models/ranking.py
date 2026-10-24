"""SQLAlchemy models for personalized ranking evaluations and recommendation snapshots."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.opportunity import Opportunity
    from app.models.user import User


class RankingEvaluation(Base, UUIDMixin, TimestampMixin):
    """Stores individual candidate ranking scores, factors, and transparency logs."""

    __tablename__ = "ranking_evaluations"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    search_session_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    relevance_score: Mapped[float] = mapped_column(Float, nullable=False)
    eligibility_status: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[str] = mapped_column(String(20), nullable=False)
    fit_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")

    factors_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    explanations_json: Mapped[list[Any]] = mapped_column(JSON, nullable=False)

    engine_version: Mapped[str] = mapped_column(String(50), default="1.0.0", nullable=False)
    config_version: Mapped[str] = mapped_column(String(50), default="1.0.0", nullable=False)

    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped[User | None] = relationship("User")
    opportunity: Mapped[Opportunity] = relationship("Opportunity")


class RecommendationSnapshot(Base, UUIDMixin, TimestampMixin):
    """Historical snapshot of an ordered recommendation set for an intent or session."""

    __tablename__ = "recommendation_snapshots"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    search_session_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    sort_mode: Mapped[str] = mapped_column(String(50), default="RELEVANCE", nullable=False)
    query_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    ranked_opportunity_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    cache_key: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    total_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    snapshot_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
