"""Dynamic deterministic monitoring frequency policy."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from app.monitoring.models.subscription import MonitoringFrequency
from app.monitoring.schemas.policy import FrequencyPolicyResult


class MonitoringFrequencyPolicy:
    """Calculates next check schedule based on deadlines, change velocity, and rate limits."""

    @staticmethod
    def calculate_next_check(
        current_deadline: date | None,
        last_changed_at: datetime | None,
        user_preference: MonitoringFrequency = MonitoringFrequency.DAILY,
        now: datetime | None = None,
    ) -> FrequencyPolicyResult:
        """Determines the optimal check frequency and next scheduled timestamp.

        Principles:
        - Approaching deadlines (< 14 days) escalate frequency.
        - Approaching critical deadlines (< 3 days) escalate to high priority daily checks.
        - Recent changes (< 48 hours) temporarily boost monitoring to verify follow-up updates.
        - Far-off deadlines (> 60 days) or no deadline relax frequency to reduce server load.
        """
        current_time = now or datetime.now(UTC)

        # 1. Deadline-based escalation
        if current_deadline:
            days_to_deadline = (current_deadline - current_time.date()).days
            if days_to_deadline < 0:
                # Opportunity has passed
                return FrequencyPolicyResult(
                    frequency=MonitoringFrequency.MONTHLY,
                    next_check_at=current_time + timedelta(days=30),
                    reason="Deadline has passed; checking monthly for archive/restoration",
                )
            if days_to_deadline <= 3:
                return FrequencyPolicyResult(
                    frequency=MonitoringFrequency.DAILY,
                    next_check_at=current_time + timedelta(hours=12),
                    reason="Critical deadline approaching within 3 days; checking twice daily",
                )
            if days_to_deadline <= 14:
                return FrequencyPolicyResult(
                    frequency=MonitoringFrequency.DAILY,
                    next_check_at=current_time + timedelta(days=1),
                    reason="Deadline approaching within 14 days; checking daily",
                )
            if days_to_deadline <= 30:
                return FrequencyPolicyResult(
                    frequency=MonitoringFrequency.EVERY_3_DAYS,
                    next_check_at=current_time + timedelta(days=3),
                    reason="Deadline within 30 days; checking every 3 days",
                )

        # 2. Change velocity boost
        if last_changed_at and (current_time - last_changed_at) < timedelta(hours=48):
            return FrequencyPolicyResult(
                frequency=MonitoringFrequency.DAILY,
                next_check_at=current_time + timedelta(days=1),
                reason="Recent change detected within 48h; elevated to daily check",
            )

        # 3. Default to user-specified preference with standard delta
        frequency_delta_map = {
            MonitoringFrequency.DAILY: timedelta(days=1),
            MonitoringFrequency.EVERY_3_DAYS: timedelta(days=3),
            MonitoringFrequency.WEEKLY: timedelta(days=7),
            MonitoringFrequency.BIWEEKLY: timedelta(days=14),
            MonitoringFrequency.MONTHLY: timedelta(days=30),
        }
        delta = frequency_delta_map.get(user_preference, timedelta(days=1))
        return FrequencyPolicyResult(
            frequency=user_preference,
            next_check_at=current_time + delta,
            reason=f"Standard check per configured frequency: {user_preference}",
        )
