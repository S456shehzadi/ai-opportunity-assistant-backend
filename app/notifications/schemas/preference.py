"""Schemas for notification preferences."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class NotificationPreferenceUpdate(BaseModel):
    """Payload to update notification settings."""

    enable_notifications: bool | None = None
    enable_in_app: bool | None = None
    enable_push: bool | None = None
    enable_email: bool | None = None

    enable_deadline_alerts: bool | None = None
    enable_funding_alerts: bool | None = None
    enable_eligibility_alerts: bool | None = None
    enable_new_opportunity_alerts: bool | None = None
    enable_status_alerts: bool | None = None

    important_changes_only: bool | None = None
    daily_notification_limit: int | None = Field(default=None, ge=1, le=50)

    quiet_hours_enabled: bool | None = None
    quiet_hours_start: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    quiet_hours_end: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    quiet_hours_timezone: str | None = None


class NotificationPreferenceResponse(BaseModel):
    """Notification preference response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    enable_notifications: bool
    enable_in_app: bool
    enable_push: bool
    enable_email: bool

    enable_deadline_alerts: bool
    enable_funding_alerts: bool
    enable_eligibility_alerts: bool
    enable_new_opportunity_alerts: bool
    enable_status_alerts: bool

    important_changes_only: bool
    daily_notification_limit: int

    quiet_hours_enabled: bool
    quiet_hours_start: str | None = None
    quiet_hours_end: str | None = None
    quiet_hours_timezone: str
    created_at: datetime
    updated_at: datetime
