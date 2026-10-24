"""Pydantic schemas for explicit user feedback."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.feedback.models.feedback import FeedbackTargetType, FeedbackType


class FeedbackCreate(BaseModel):
    """Payload submitted by user to provide explicit feedback."""

    target_type: FeedbackTargetType
    target_id: str = Field(min_length=1, max_length=255)
    feedback_type: FeedbackType
    reason: str | None = Field(default=None, max_length=100)
    comment: str | None = Field(default=None, max_length=1000)
    context_snapshot: dict[str, Any] = Field(default_factory=dict)


class FeedbackResponse(BaseModel):
    """Auditable feedback record response representation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    target_type: FeedbackTargetType
    target_id: str
    feedback_type: FeedbackType
    reason: str | None = None
    comment: str | None = None
    context_snapshot: dict[str, Any]
    status: str
    created_at: datetime
    updated_at: datetime
