"""Model card documentation and governance database model."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import (
    JSON,
    ForeignKey,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class ModelCardRecord(Base, UUIDMixin, TimestampMixin):
    """Auditable documentation card for specialized models."""

    __tablename__ = "model_cards"

    model_definition_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("model_definitions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    purpose: Mapped[str] = mapped_column(Text, default="", nullable=False)
    task: Mapped[str] = mapped_column(String(100), nullable=False)
    intended_use: Mapped[str] = mapped_column(Text, default="", nullable=False)
    non_intended_use: Mapped[str] = mapped_column(Text, default="", nullable=False)
    limitations: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    evaluation_metrics: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    training_data_provenance: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    license: Mapped[str] = mapped_column(String(100), default="MIT", nullable=False)
    ethical_considerations: Mapped[str] = mapped_column(Text, default="", nullable=False)

    model_definition = relationship("ModelDefinition", back_populates="model_card")
