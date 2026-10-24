"""Unit tests for notification fatigue, cooldowns, quiet hours, and preferences."""

import uuid
from datetime import UTC, datetime

from app.monitoring.policies.fatigue_policy import NotificationFatiguePolicy
from app.notifications.models.notification import NotificationPriority, NotificationType
from app.notifications.models.preference import NotificationPreference


def test_fatigue_policy_suppresses_duplicate_key():
    """Verify notification is rejected if deduplication key already exists."""
    pref = NotificationPreference(
        user_id=uuid.uuid4(),
        enable_notifications=True,
    )
    decision = NotificationFatiguePolicy.evaluate(
        user_preference=pref,
        notification_type=NotificationType.DEADLINE_APPROACHING,
        priority=NotificationPriority.NORMAL,
        opportunity_id=uuid.uuid4(),
        recent_opportunity_notification_at=None,
        notifications_sent_today_count=0,
        deduplication_key_exists=True,
    )
    assert decision.allow is False
    assert "deduplication matched" in (decision.suppress_reason or "")


def test_fatigue_policy_cooldown_enforced_unless_urgent():
    """Verify cooldown window suppresses non-urgent alerts within 1 hour."""
    pref = NotificationPreference(user_id=uuid.uuid4(), enable_notifications=True)
    now = datetime(2026, 10, 1, 12, 0, 0, tzinfo=UTC)
    recent_notif = datetime(2026, 10, 1, 11, 45, 0, tzinfo=UTC)  # 15 mins ago

    # Normal priority -> suppressed
    decision_normal = NotificationFatiguePolicy.evaluate(
        user_preference=pref,
        notification_type=NotificationType.STATUS_CHANGED,
        priority=NotificationPriority.NORMAL,
        opportunity_id=uuid.uuid4(),
        recent_opportunity_notification_at=recent_notif,
        notifications_sent_today_count=1,
        deduplication_key_exists=False,
        now=now,
    )
    assert decision_normal.allow is False
    assert "Cooldown active" in (decision_normal.suppress_reason or "")

    # Urgent priority -> bypasses cooldown
    decision_urgent = NotificationFatiguePolicy.evaluate(
        user_preference=pref,
        notification_type=NotificationType.STATUS_CHANGED,
        priority=NotificationPriority.URGENT,
        opportunity_id=uuid.uuid4(),
        recent_opportunity_notification_at=recent_notif,
        notifications_sent_today_count=1,
        deduplication_key_exists=False,
        now=now,
    )
    assert decision_urgent.allow is True


def test_fatigue_policy_daily_limit_threshold():
    """Verify daily limit prevents notification fatigue for non-urgent notifications."""
    pref = NotificationPreference(
        user_id=uuid.uuid4(),
        enable_notifications=True,
        daily_notification_limit=5,
    )
    now = datetime(2026, 10, 1, 15, 0, 0, tzinfo=UTC)

    decision = NotificationFatiguePolicy.evaluate(
        user_preference=pref,
        notification_type=NotificationType.FUNDING_CHANGED,
        priority=NotificationPriority.NORMAL,
        opportunity_id=uuid.uuid4(),
        recent_opportunity_notification_at=None,
        notifications_sent_today_count=5,  # already reached limit
        deduplication_key_exists=False,
        now=now,
    )
    assert decision.allow is False
    assert "Daily notification limit" in (decision.suppress_reason or "")


def test_fatigue_policy_quiet_hours_suppression():
    """Verify notifications during configured quiet hours are suppressed."""
    pref = NotificationPreference(
        user_id=uuid.uuid4(),
        enable_notifications=True,
        quiet_hours_enabled=True,
        quiet_hours_start="22:00",
        quiet_hours_end="08:00",
    )

    # 23:30 is within quiet hours
    night_time = datetime(2026, 10, 1, 23, 30, 0, tzinfo=UTC)
    decision = NotificationFatiguePolicy.evaluate(
        user_preference=pref,
        notification_type=NotificationType.STATUS_CHANGED,
        priority=NotificationPriority.NORMAL,
        opportunity_id=uuid.uuid4(),
        recent_opportunity_notification_at=None,
        notifications_sent_today_count=1,
        deduplication_key_exists=False,
        now=night_time,
    )
    assert decision.allow is False
    assert "quiet hours" in (decision.suppress_reason or "")

    # 10:30 is outside quiet hours
    day_time = datetime(2026, 10, 1, 10, 30, 0, tzinfo=UTC)
    decision_day = NotificationFatiguePolicy.evaluate(
        user_preference=pref,
        notification_type=NotificationType.STATUS_CHANGED,
        priority=NotificationPriority.NORMAL,
        opportunity_id=uuid.uuid4(),
        recent_opportunity_notification_at=None,
        notifications_sent_today_count=1,
        deduplication_key_exists=False,
        now=day_time,
    )
    assert decision_day.allow is True


def test_fatigue_policy_category_preferences():
    """Verify disabled categories (e.g. deadline or funding) are respected."""
    pref = NotificationPreference(
        user_id=uuid.uuid4(),
        enable_notifications=True,
        enable_funding_alerts=False,
    )

    decision = NotificationFatiguePolicy.evaluate(
        user_preference=pref,
        notification_type=NotificationType.FUNDING_CHANGED,
        priority=NotificationPriority.HIGH,
        opportunity_id=uuid.uuid4(),
        recent_opportunity_notification_at=None,
        notifications_sent_today_count=0,
        deduplication_key_exists=False,
    )
    assert decision.allow is False
    assert "disabled funding alerts" in (decision.suppress_reason or "")
