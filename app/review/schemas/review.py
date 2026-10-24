"""Schemas for human-in-the-loop review queue and corrections."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.review.models.review_item import ReviewCategory, ReviewStatus


class ReviewItemCreate(BaseModel):
    """Payload to enqueue a verification candidate in the review queue."""

    category: ReviewCategory
    entity_id: str = Field(min_length=1, max_length=255)
    reason: str = Field(min_length=1, max_length=255)
    evidence_text: str = ""
    evidence_url: str | None = None
    current_system_output: dict[str, Any] = Field(default_factory=dict)
    priority: str = "NORMAL"
    user_feedback_id: UUID | None = None


class HumanCorrectionResponse(BaseModel):
    """Auditable record of a human correction."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    review_id: UUID
    original_value: dict[str, Any]
    corrected_value: dict[str, Any]
    evidence: str
    reviewer_id: UUID | None = None
    reason: str
    created_at: datetime


class ReviewItemResponse(BaseModel):
    """Review queue item representation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    category: ReviewCategory
    entity_id: str
    reason: str
    evidence_text: str
    evidence_url: str | None = None
    current_system_output: dict[str, Any]
    user_feedback_id: UUID | None = None
    priority: str
    status: ReviewStatus
    assigned_to: UUID | None = None
    resolved_at: datetime | None = None
    resolution_notes: str | None = None
    created_at: datetime
    updated_at: datetime
    corrections: list[HumanCorrectionResponse] = Field(default_factory=list)


class ReviewResolutionCreate(BaseModel):
    """Payload to record a human reviewer's decision and optional correction."""

    status: ReviewStatus
    resolution_notes: str | None = None
    corrected_value: dict[str, Any] | None = None
    evidence: str | None = None
