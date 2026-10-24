"""Schemas for product events and analytics dashboards."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.analytics.models.event import EventType


class UserEventCreate(BaseModel):
    """Payload to record an analytics behavioral event."""

    event_type: EventType
    event_version: int = Field(default=1, ge=1)
    anonymous_session_id: str | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    request_id: str | None = None
    session_id: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    application_version: str = "1.0.0"
    platform: str = "mobile"
    locale: str = "en"


class UserEventResponse(BaseModel):
    """Event representation returned by queries."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID | None = None
    anonymous_session_id: str | None = None
    event_type: EventType
    event_version: int
    entity_type: str | None = None
    entity_id: str | None = None
    timestamp: datetime
    request_id: str | None = None
    session_id: str | None = None
    metadata_json: dict[str, Any]
    application_version: str
    platform: str
    locale: str


class AnalyticsOverviewResponse(BaseModel):
    """High-level system quality and product analytics overview."""

    total_events: int = 0
    search_success_rate: float = 1.0
    retrieval_success_rate: float = 1.0
    extraction_success_rate: float = 1.0
    grounding_rate: float = 1.0
    unsupported_claim_rate: float = 0.0
    feedback_counts: dict[str, int] = Field(default_factory=dict)
    active_error_clusters_count: int = 0
