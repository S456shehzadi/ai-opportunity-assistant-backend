"""User notification preference model."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Integer,
    String,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class NotificationPreference(Base, UUIDMixin, TimestampMixin):
    """User configuration for notification channels, filters, and quiet hours."""

    __tablename__ = "notification_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    enable_notifications: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    enable_in_app: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    enable_push: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    enable_email: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    enable_deadline_alerts: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    enable_funding_alerts: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    enable_eligibility_alerts: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    enable_new_opportunity_alerts: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    enable_status_alerts: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    important_changes_only: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    daily_notification_limit: Mapped[int] = mapped_column(Integer, default=5, nullable=False)

    quiet_hours_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    quiet_hours_start: Mapped[str | None] = mapped_column(String(5), default="22:00", nullable=True)
    quiet_hours_end: Mapped[str | None] = mapped_column(String(5), default="08:00", nullable=True)
    quiet_hours_timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])

    def __init__(
        self,
        user_id: uuid.UUID,
        enable_notifications: bool = True,
        enable_in_app: bool = True,
        enable_push: bool = False,
        enable_email: bool = False,
        enable_deadline_alerts: bool = True,
        enable_funding_alerts: bool = True,
        enable_eligibility_alerts: bool = True,
        enable_new_opportunity_alerts: bool = True,
        enable_status_alerts: bool = True,
        important_changes_only: bool = False,
        daily_notification_limit: int = 5,
        quiet_hours_enabled: bool = False,
        quiet_hours_start: str | None = "22:00",
        quiet_hours_end: str | None = "08:00",
        quiet_hours_timezone: str = "UTC",
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.user_id = user_id
        self.enable_notifications = enable_notifications
        self.enable_in_app = enable_in_app
        self.enable_push = enable_push
        self.enable_email = enable_email
        self.enable_deadline_alerts = enable_deadline_alerts
        self.enable_funding_alerts = enable_funding_alerts
        self.enable_eligibility_alerts = enable_eligibility_alerts
        self.enable_new_opportunity_alerts = enable_new_opportunity_alerts
        self.enable_status_alerts = enable_status_alerts
        self.important_changes_only = important_changes_only
        self.daily_notification_limit = daily_notification_limit
        self.quiet_hours_enabled = quiet_hours_enabled
        self.quiet_hours_start = quiet_hours_start
        self.quiet_hours_end = quiet_hours_end
        self.quiet_hours_timezone = quiet_hours_timezone
