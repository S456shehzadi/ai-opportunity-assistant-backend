"""Pydantic schemas for opportunity and search subscriptions."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.monitoring.models.subscription import MonitoringFrequency, MonitoringStatus


class OpportunitySubscriptionCreate(BaseModel):
    """Payload to subscribe to monitoring an opportunity."""

    opportunity_id: UUID
    monitoring_frequency: MonitoringFrequency = MonitoringFrequency.DAILY
    notification_channels: list[str] = Field(default_factory=lambda: ["IN_APP"])
    important_only: bool = False
    deadline_alerts_enabled: bool = True
    funding_change_alerts_enabled: bool = True
    requirement_change_alerts_enabled: bool = True
    status_change_alerts_enabled: bool = True


class OpportunitySubscriptionUpdate(BaseModel):
    """Payload to update an existing opportunity subscription."""

    monitoring_frequency: MonitoringFrequency | None = None
    monitoring_status: MonitoringStatus | None = None
    notification_channels: list[str] | None = None
    important_only: bool | None = None
    deadline_alerts_enabled: bool | None = None
    funding_change_alerts_enabled: bool | None = None
    requirement_change_alerts_enabled: bool | None = None
    status_change_alerts_enabled: bool | None = None


class OpportunitySubscriptionResponse(BaseModel):
    """Opportunity subscription representation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    opportunity_id: UUID
    monitoring_frequency: MonitoringFrequency
    monitoring_status: MonitoringStatus
    last_checked_at: datetime | None = None
    last_changed_at: datetime | None = None
    next_check_at: datetime | None = None
    notification_channels: list[str]
    important_only: bool
    deadline_alerts_enabled: bool
    funding_change_alerts_enabled: bool
    requirement_change_alerts_enabled: bool
    status_change_alerts_enabled: bool
    created_at: datetime
    updated_at: datetime


class SearchSubscriptionCreate(BaseModel):
    """Payload to subscribe to monitoring a search query."""

    query: str = Field(min_length=1, max_length=500)
    filters: dict[str, Any] | None = None
    monitoring_frequency: MonitoringFrequency = MonitoringFrequency.WEEKLY


class SearchSubscriptionUpdate(BaseModel):
    """Payload to update an existing search subscription."""

    monitoring_frequency: MonitoringFrequency | None = None
    monitoring_status: MonitoringStatus | None = None
    filters: dict[str, Any] | None = None


class SearchSubscriptionResponse(BaseModel):
    """Search subscription representation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    query: str
    normalized_search_intent: dict[str, Any] | None = None
    filters: dict[str, Any] | None = None
    monitoring_frequency: MonitoringFrequency
    monitoring_status: MonitoringStatus
    last_searched_at: datetime | None = None
    next_search_at: datetime | None = None
    last_result_fingerprint: str | None = None
    known_opportunity_ids: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
