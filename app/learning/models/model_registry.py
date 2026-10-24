"""Provider-independent model definition and registry models."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Enum,
    Float,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class ModelType(StrEnum):
    """Categorized model responsibilities in the intelligence architecture."""

    QUERY_UNDERSTANDING = "QUERY_UNDERSTANDING"
    PROFILE_NORMALIZATION = "PROFILE_NORMALIZATION"
    OPPORTUNITY_EXTRACTION = "OPPORTUNITY_EXTRACTION"
    REQUIREMENT_EXTRACTION = "REQUIREMENT_EXTRACTION"
    ELIGIBILITY_ASSIST = "ELIGIBILITY_ASSIST"
    SEMANTIC_RELEVANCE = "SEMANTIC_RELEVANCE"
    SEMANTIC_RANKING = "SEMANTIC_RANKING"
    RERANKING = "RERANKING"
    CHANGE_DETECTION = "CHANGE_DETECTION"
    EMBEDDING = "EMBEDDING"
    RESPONSE_GENERATION = "RESPONSE_GENERATION"


class ModelStatus(StrEnum):
    """Lifecycle status of a model candidate/deployment."""

    DEVELOPMENT = "DEVELOPMENT"
    EVALUATION = "EVALUATION"
    CANDIDATE = "CANDIDATE"
    STAGING = "STAGING"
    PRODUCTION = "PRODUCTION"
    ARCHIVED = "ARCHIVED"
    RETIRED = "RETIRED"


class ModelHealthStatus(StrEnum):
    """Operational health status of a model service/endpoint."""

    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"


class ModelCostTier(StrEnum):
    """Cost tier associated with running the model."""

    ZERO_LOCAL = "ZERO_LOCAL"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ModelDefinition(Base, UUIDMixin, TimestampMixin):
    """Registry entry for available local, self-hosted, or cloud models."""

    __tablename__ = "model_definitions"

    model_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_type: Mapped[ModelType] = mapped_column(
        Enum(ModelType, native_enum=False, length=50),
        nullable=False,
        index=True,
    )
    version: Mapped[str] = mapped_column(String(50), default="1.0.0", nullable=False)
    capabilities: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    configuration_reference: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    status: Mapped[ModelStatus] = mapped_column(
        Enum(ModelStatus, native_enum=False, length=50),
        default=ModelStatus.PRODUCTION,
        nullable=False,
        index=True,
    )
    canary_percentage: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    rollback_model_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    architecture: Mapped[str | None] = mapped_column(
        String(100),
        default="transformer",
        nullable=True,
    )
    cost_tier: Mapped[ModelCostTier] = mapped_column(
        Enum(ModelCostTier, native_enum=False, length=50),
        default=ModelCostTier.LOW,
        nullable=False,
    )
    health_status: Mapped[ModelHealthStatus] = mapped_column(
        Enum(ModelHealthStatus, native_enum=False, length=50),
        default=ModelHealthStatus.HEALTHY,
        nullable=False,
    )

    artifacts = relationship(
        "ModelArtifactRecord",
        back_populates="model_definition",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    model_card = relationship(
        "ModelCardRecord",
        back_populates="model_definition",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )
