"""Schemas for monitoring policies."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.monitoring.models.subscription import MonitoringFrequency


class FrequencyPolicyResult(BaseModel):
    """Result of dynamic monitoring frequency calculation."""

    frequency: MonitoringFrequency
    next_check_at: datetime
    reason: str


class FatiguePolicyDecision(BaseModel):
    """Decision output from notification fatigue evaluation."""

    allow: bool
    suppress_reason: str | None = None
    scheduled_for: datetime | None = None
