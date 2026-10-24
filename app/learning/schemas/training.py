"""Schemas for training jobs, model cards, governance, and model lifecycle."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.learning.models.model_registry import (
    ModelCostTier,
    ModelHealthStatus,
    ModelStatus,
    ModelType,
)
from app.learning.models.training_job import TrainingJobStatus


class TrainingHyperparameters(BaseModel):
    """Configurable training/fine-tuning hyperparameters."""

    epochs: int = Field(default=3, ge=1, le=50)
    learning_rate: float = Field(default=2e-5, gt=0.0)
    batch_size: int = Field(default=8, ge=1, le=512)
    warmup_steps: int = Field(default=100, ge=0)
    weight_decay: float = Field(default=0.01, ge=0.0)
    lora_r: int = Field(default=16, ge=1, le=128)
    lora_alpha: int = Field(default=32, ge=1, le=256)
    lora_dropout: float = Field(default=0.05, ge=0.0, le=0.5)
    extra_params: dict[str, Any] = Field(default_factory=dict)


class ResourceLimits(BaseModel):
    """Computational and temporal limits for training jobs."""

    max_duration_seconds: int = Field(default=3600, ge=10, le=86400)
    max_memory_mb: int = Field(default=8192, ge=512)
    max_epochs: int = Field(default=10, ge=1)
    max_examples: int = Field(default=50000, ge=10)


class TrainingJobCreate(BaseModel):
    """Payload to initiate a new training/fine-tuning job."""

    job_name: str = Field(min_length=3, max_length=150)
    task: ModelType
    dataset_version_id: UUID | None = None
    base_model: str = Field(min_length=2, max_length=150)
    training_backend: str = Field(default="LOCAL", max_length=50)
    hyperparameters: TrainingHyperparameters = Field(default_factory=TrainingHyperparameters)
    resource_limits: ResourceLimits = Field(default_factory=ResourceLimits)


class TrainingJobResponse(BaseModel):
    """Detailed response for an asynchronous training job."""

    id: UUID
    job_name: str
    task: ModelType
    dataset_version_id: UUID | None = None
    base_model: str
    training_backend: str
    hyperparameters: dict[str, Any]
    resource_limits: dict[str, Any]
    status: TrainingJobStatus
    metrics: dict[str, Any]
    logs: list[dict[str, Any]]
    error_message: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ModelCardCreate(BaseModel):
    """Auditable documentation card creation payload."""

    purpose: str = Field(min_length=5)
    task: str = Field(min_length=2, max_length=100)
    intended_use: str = Field(min_length=5)
    non_intended_use: str = Field(default="")
    limitations: list[str] = Field(default_factory=list)
    evaluation_metrics: dict[str, Any] = Field(default_factory=dict)
    training_data_provenance: dict[str, Any] = Field(default_factory=dict)
    license: str = Field(default="MIT", max_length=100)
    ethical_considerations: str = Field(default="")


class ModelCardResponse(BaseModel):
    """Model card response with audit metadata."""

    id: UUID
    model_definition_id: UUID
    purpose: str
    task: str
    intended_use: str
    non_intended_use: str
    limitations: list[str]
    evaluation_metrics: dict[str, Any]
    training_data_provenance: dict[str, Any]
    license: str
    ethical_considerations: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ModelPromotionRequest(BaseModel):
    """Request payload to gate-promote a model to next lifecycle stage."""

    target_status: ModelStatus
    min_metric_threshold: dict[str, float] = Field(default_factory=dict)
    reviewer_notes: str = Field(default="")
    approved_by: str = Field(default="admin")


class ModelRollbackRequest(BaseModel):
    """Atomic rollback request to restore previous stable model version."""

    target_model_id: str | None = None
    reason: str = Field(min_length=3)


class CanaryTrafficUpdate(BaseModel):
    """Configuration payload to alter canary traffic percentage."""

    canary_percentage: float = Field(ge=0.0, le=100.0)


class ModelHealthResponse(BaseModel):
    """Operational health status payload for a model endpoint."""

    model_id: str
    status: ModelStatus
    health_status: ModelHealthStatus
    is_healthy: bool
    latency_ms: float
    message: str


class ModelDetailResponse(BaseModel):
    """Full detail of registered model including governance and status."""

    id: UUID
    model_id: str
    provider: str
    model_name: str
    model_type: ModelType
    version: str
    capabilities: list[str]
    active: bool
    status: ModelStatus
    canary_percentage: float
    rollback_model_id: str | None = None
    architecture: str | None = None
    cost_tier: ModelCostTier
    health_status: ModelHealthStatus
    model_card: ModelCardResponse | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
