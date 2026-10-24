"""Database models for vector embeddings and discovery search sessions."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class OpportunityEmbeddingRecord(Base, UUIDMixin, TimestampMixin):
    """Stores versioned vector embeddings and content hashes for opportunities."""

    __tablename__ = "opportunity_embeddings"

    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    embedding_type: Mapped[str] = mapped_column(
        String(50),
        default="FULL",
        nullable=False,
        index=True,
    )
    # Stored as JSON array of floats for universal DB portability
    vector_data: Mapped[list[float]] = mapped_column(
        JSON,
        nullable=False,
    )
    dimension: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    embedding_model: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    embedding_provider: Mapped[str] = mapped_column(
        String(50),
        default="LOCAL",
        nullable=False,
    )
    embedding_version: Mapped[str] = mapped_column(
        String(50),
        default="v1.0.0",
        nullable=False,
        index=True,
    )
    content_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )


class DiscoverySearchSessionRecord(Base, UUIDMixin, TimestampMixin):
    """Audit and analytics record of semantic and hybrid retrieval executions."""

    __tablename__ = "discovery_search_sessions"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    original_query: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    normalized_query: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    expanded_queries: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    retrieval_strategy: Mapped[str] = mapped_column(
        String(50),
        default="HYBRID",
        nullable=False,
    )
    filters_applied: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    candidate_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    result_ids: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    latency_ms: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    embedding_model_used: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    reranker_used: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
