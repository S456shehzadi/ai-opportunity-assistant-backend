"""Schemas for model registry, prompt versioning, and experimentation."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.learning.models.experiment import ExperimentStatus
from app.learning.models.model_registry import ModelType


class ModelDefinitionCreate(BaseModel):
    """Payload to register a provider-independent model."""

    model_id: str = Field(min_length=1, max_length=100)
    provider: str = Field(min_length=1, max_length=50)
    model_name: str = Field(min_length=1, max_length=100)
    model_type: ModelType
    version: str = "1.0.0"
    capabilities: list[str] = Field(default_factory=list)
    active: bool = True
    configuration_reference: dict[str, Any] = Field(default_factory=dict)


class ModelDefinitionResponse(BaseModel):
    """Registered model representation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    model_id: str
    provider: str
    model_name: str
    model_type: ModelType
    version: str
    capabilities: list[str]
    active: bool
    configuration_reference: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class PromptVersionCreate(BaseModel):
    """Payload to register an explicit prompt template version."""

    prompt_name: str = Field(min_length=1, max_length=100)
    prompt_version: str = Field(min_length=1, max_length=50)
    task: str = Field(min_length=1, max_length=100)
    template: str = Field(min_length=1)
    active: bool = True


class PromptVersionResponse(BaseModel):
    """Prompt version representation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    prompt_name: str
    prompt_version: str
    task: str
    template: str
    active: bool
    created_at: datetime
    updated_at: datetime


class ExperimentVariantCreate(BaseModel):
    """Variant specification for an experiment."""

    variant_key: str = Field(min_length=1, max_length=50)
    traffic_percentage: float = Field(default=50.0, ge=0.0, le=100.0)
    configuration: dict[str, Any] = Field(default_factory=dict)


class ExperimentCreate(BaseModel):
    """Payload to launch a controlled product experiment (non-sensitive scope)."""

    name: str = Field(min_length=1, max_length=100)
    description: str = ""
    hypothesis: str = ""
    target_metric: str = Field(min_length=1, max_length=100)
    variants: list[ExperimentVariantCreate] = Field(default_factory=list)


class ExperimentResponse(BaseModel):
    """Experiment representation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str
    hypothesis: str
    status: ExperimentStatus
    target_metric: str
    start_time: datetime | None = None
    end_time: datetime | None = None
    created_at: datetime
    updated_at: datetime
