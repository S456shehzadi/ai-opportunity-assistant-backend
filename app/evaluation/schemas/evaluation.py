"""Schemas for benchmark datasets and reproducible evaluation runs."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.evaluation.models.dataset import DatasetQualityStatus, SplitType
from app.evaluation.models.evaluation_run import EvaluationStatus


class DatasetCreate(BaseModel):
    """Payload to define a new benchmark dataset."""

    name: str = Field(min_length=1, max_length=100)
    task_type: str = Field(min_length=1, max_length=50)
    description: str = ""


class DatasetExampleInput(BaseModel):
    """Ground-truth example specification."""

    split: SplitType = SplitType.TRAIN
    input_data: dict[str, Any]
    expected_output: dict[str, Any]
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    provenance_review_id: UUID | None = None


class DatasetVersionCreate(BaseModel):
    """Payload to release a new version of a dataset."""

    version_tag: str = Field(min_length=1, max_length=50)
    examples: list[DatasetExampleInput] = Field(default_factory=list)
    quality_status: DatasetQualityStatus = DatasetQualityStatus.DRAFT


class DatasetExampleResponse(BaseModel):
    """Example representation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    dataset_version_id: UUID
    split: SplitType
    input_data: dict[str, Any]
    expected_output: dict[str, Any]
    metadata_json: dict[str, Any]
    provenance_review_id: UUID | None = None
    created_at: datetime


class DatasetVersionResponse(BaseModel):
    """Versioned dataset response representation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    dataset_id: UUID
    version_tag: str
    example_count: int
    schema_version: str
    quality_status: DatasetQualityStatus
    split_counts: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class DatasetResponse(BaseModel):
    """Benchmark dataset response representation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    task_type: str
    description: str
    created_at: datetime
    updated_at: datetime
    versions: list[DatasetVersionResponse] = Field(default_factory=list)


class EvaluationRunCreate(BaseModel):
    """Payload to execute and record a benchmark evaluation run."""

    dataset_version_id: UUID
    model_provider: str = "deterministic"
    model_name: str = "rules"
    model_version: str = "1.0.0"
    prompt_name: str | None = None
    prompt_version: str | None = None
    configuration: dict[str, Any] = Field(default_factory=dict)
    claims_to_evaluate: list[dict[str, Any]] | None = None


class EvaluationRunResponse(BaseModel):
    """Auditable execution record of an evaluation run."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    model_provider: str
    model_name: str
    model_version: str
    prompt_name: str | None = None
    prompt_version: str | None = None
    dataset_version_id: UUID
    configuration: dict[str, Any]
    metrics_summary: dict[str, Any]
    claim_evaluations: list[dict[str, Any]]
    status: EvaluationStatus
    code_version: str
    environment: str
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
