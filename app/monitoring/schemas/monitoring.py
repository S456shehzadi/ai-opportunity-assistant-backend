"""Schemas for monitoring execution summaries and monitored items."""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.monitoring.schemas.change_event import OpportunityChangeEventResponse
from app.monitoring.schemas.subscription import OpportunitySubscriptionResponse


class MonitoringRunSummary(BaseModel):
    """Execution summary of a monitoring batch or manual check."""

    checks_run: int = 0
    changes_detected: int = 0
    notifications_created: int = 0
    errors_encountered: int = 0
    details: list[dict[str, Any]] = []


class MonitoredOpportunitySummary(BaseModel):
    """Enriched summary for user display."""

    model_config = ConfigDict(from_attributes=True)

    subscription: OpportunitySubscriptionResponse
    opportunity_title: str
    organization: str
    category: str
    country: str
    deadline: date | None = None
    funding_type: str
    application_url: str | None = None
    change_count: int = 0
    latest_change: OpportunityChangeEventResponse | None = None
