"""Pydantic schemas for opportunity change events."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.monitoring.models.change_event import OpportunityChangeType


class OpportunityChangeEventBase(BaseModel):
    """Base schema for change event attributes."""

    opportunity_id: UUID
    source_id: UUID | None = None
    change_type: OpportunityChangeType
    affected_field: str
    old_value: Any = None
    new_value: Any = None
    evidence: str = ""
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source_trust: str = "HIGH"
    verified: bool = True
    notification_priority: str = "NORMAL"
    effective_date: date | None = None


class OpportunityChangeEventCreate(OpportunityChangeEventBase):
    """Schema for recording a new observed change."""

    pass


class OpportunityChangeEventResponse(OpportunityChangeEventBase):
    """Schema returned by API endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    processed: bool
    detected_at: datetime
    created_at: datetime
    updated_at: datetime
