"""Notification fatigue, debounce, and quiet hours policy."""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from uuid import UUID

from app.monitoring.schemas.policy import FatiguePolicyDecision
from app.notifications.models.notification import NotificationPriority, NotificationType
from app.notifications.models.preference import NotificationPreference


class NotificationFatiguePolicy:
    """Guards against notification overload via cooldowns, limits, and quiet hours."""

    COOLDOWN_WINDOW = timedelta(hours=1)

    @classmethod
    def evaluate(
        cls,
        user_preference: NotificationPreference,
        notification_type: NotificationType,
        priority: NotificationPriority,
        opportunity_id: UUID | None,
        recent_opportunity_notification_at: datetime | None,
        notifications_sent_today_count: int,
        deduplication_key_exists: bool,
        now: datetime | None = None,
    ) -> FatiguePolicyDecision:
        """Determines if a notification can be sent or must be suppressed/debounced."""
        current_time = now or datetime.now(UTC)

        # 1. Global master toggle
        if not user_preference.enable_notifications:
            return FatiguePolicyDecision(
                allow=False,
                suppress_reason="User has globally disabled notifications",
            )

        # 2. Duplicate prevention
        if deduplication_key_exists:
            return FatiguePolicyDecision(
                allow=False,
                suppress_reason="Identical notification already delivered (deduplication matched)",
            )

        # 3. Category preference toggles
        if (
            notification_type
            in (
                NotificationType.DEADLINE_APPROACHING,
                NotificationType.DEADLINE_CHANGED,
            )
            and not user_preference.enable_deadline_alerts
        ):
            return FatiguePolicyDecision(
                allow=False,
                suppress_reason="User disabled deadline alerts",
            )

        if (
            notification_type == NotificationType.FUNDING_CHANGED
            and not user_preference.enable_funding_alerts
        ):
            return FatiguePolicyDecision(
                allow=False,
                suppress_reason="User disabled funding alerts",
            )

        if (
            notification_type
            in (
                NotificationType.REQUIREMENT_CHANGED,
                NotificationType.ELIGIBILITY_STATUS_CHANGED,
            )
            and not user_preference.enable_eligibility_alerts
        ):
            return FatiguePolicyDecision(
                allow=False,
                suppress_reason="User disabled eligibility/requirement alerts",
            )

        if (
            notification_type == NotificationType.NEW_MATCHING_OPPORTUNITY
            and not user_preference.enable_new_opportunity_alerts
        ):
            return FatiguePolicyDecision(
                allow=False,
                suppress_reason="User disabled new matching opportunity alerts",
            )

        if (
            notification_type
            in (
                NotificationType.STATUS_CHANGED,
                NotificationType.APPLICATION_OPENED,
            )
            and not user_preference.enable_status_alerts
        ):
            return FatiguePolicyDecision(
                allow=False,
                suppress_reason="User disabled opportunity status change alerts",
            )

        # 4. Importance filter
        if user_preference.important_changes_only and priority in (
            NotificationPriority.LOW,
            NotificationPriority.NORMAL,
        ):
            return FatiguePolicyDecision(
                allow=False,
                suppress_reason="User opted for important changes only; normal/low suppressed",
            )

        # 5. Cooldown per opportunity (urgent priority bypasses cooldown)
        if (
            opportunity_id
            and recent_opportunity_notification_at
            and priority != NotificationPriority.URGENT
        ):
            elapsed = current_time - recent_opportunity_notification_at
            if elapsed < cls.COOLDOWN_WINDOW:
                minutes_ago = int(elapsed.total_seconds() / 60)
                window_min = int(cls.COOLDOWN_WINDOW.total_seconds() / 60)
                return FatiguePolicyDecision(
                    allow=False,
                    suppress_reason=(
                        f"Cooldown active: notification sent {minutes_ago}m ago "
                        f"(window is {window_min}m)"
                    ),
                )

        # 6. Daily limit check (urgent priority bypasses daily limit)
        if (
            notifications_sent_today_count >= user_preference.daily_notification_limit
            and priority != NotificationPriority.URGENT
        ):
            return FatiguePolicyDecision(
                allow=False,
                suppress_reason=(
                    f"Daily notification limit ({user_preference.daily_notification_limit}) reached"
                ),
            )

        # 7. Quiet hours evaluation
        if user_preference.quiet_hours_enabled and priority != NotificationPriority.URGENT:
            if cls._is_quiet_hours(
                current_time=current_time,
                start_str=user_preference.quiet_hours_start,
                end_str=user_preference.quiet_hours_end,
            ):
                return FatiguePolicyDecision(
                    allow=False,
                    suppress_reason="Current time falls inside configured quiet hours",
                )

        return FatiguePolicyDecision(allow=True)

    @classmethod
    def _is_quiet_hours(
        cls,
        current_time: datetime,
        start_str: str | None,
        end_str: str | None,
    ) -> bool:
        """Helper to determine if current time is within quiet hours window."""
        if not start_str or not end_str:
            return False

        try:
            start_parts = [int(p) for p in start_str.split(":")]
            end_parts = [int(p) for p in end_str.split(":")]
            start_time = time(start_parts[0], start_parts[1])
            end_time = time(end_parts[0], end_parts[1])
            cur_time = current_time.time()

            if start_time < end_time:
                # e.g., 01:00 to 06:00
                return start_time <= cur_time < end_time
            else:
                # Overnight: e.g., 22:00 to 08:00
                return cur_time >= start_time or cur_time < end_time
        except Exception:
            return False
