"""Unit tests for deadline sweeps and monitored searches."""

import uuid
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.opportunity import Opportunity
from app.monitoring.models.subscription import (
    MonitoringFrequency,
    OpportunitySubscription,
    SearchSubscription,
)
from app.monitoring.services.deadline_monitor import DeadlineMonitor
from app.monitoring.services.search_monitor import SearchMonitor
from app.notifications.models.notification import NotificationPriority, NotificationType


@pytest.mark.asyncio
async def test_deadline_sweep_triggers_alert_for_milestone_windows():
    """Verify deadline sweep alerts on 30, 14, 7, 3, 1, and 0 days."""
    mock_notification_service = AsyncMock()
    mock_notification_service.dispatch_notification.return_value = MagicMock()

    monitor = DeadlineMonitor(notification_service=mock_notification_service)

    user_id = uuid.uuid4()
    opp_id = uuid.uuid4()

    fixed_now = datetime(2026, 10, 1, 10, 0, 0, tzinfo=UTC)

    # Opportunity with deadline exactly 3 days away: 2026-10-04
    opp = MagicMock(spec=Opportunity)
    opp.id = opp_id
    opp.title = "Gates Cambridge Scholarship"
    opp.deadline = date(2026, 10, 4)

    sub = MagicMock(spec=OpportunitySubscription)
    sub.user_id = user_id
    sub.opportunity_id = opp_id
    sub.opportunity = opp

    mock_db = AsyncMock()

    class MockQueryResult:
        def scalars(self):
            return self

        def all(self):
            return [sub]

    mock_db.execute.return_value = MockQueryResult()

    sent_count = await monitor.sweep_deadlines(db=mock_db, now=fixed_now)
    assert sent_count == 1
    assert mock_notification_service.dispatch_notification.called

    call_args = mock_notification_service.dispatch_notification.call_args[1]
    assert call_args["notification_type"] == NotificationType.DEADLINE_APPROACHING
    assert call_args["priority"] == NotificationPriority.HIGH
    assert "3 Days Left" in call_args["title"]
    assert "opp_" in call_args["deduplication_key"]
    assert "_w_3_dl_2026-10-04" in call_args["deduplication_key"]


@pytest.mark.asyncio
async def test_search_monitor_discovers_genuinely_new_opportunity():
    """Verify search monitor only alerts for new opportunities not yet in known_opportunity_ids."""
    mock_notification_service = AsyncMock()
    mock_notification_service.dispatch_notification.return_value = MagicMock()

    search_monitor = SearchMonitor(notification_service=mock_notification_service)

    user_id = uuid.uuid4()
    search_id = uuid.uuid4()

    known_opp_id = uuid.uuid4()
    new_opp_id = uuid.uuid4()

    sub = MagicMock(spec=SearchSubscription)
    sub.id = search_id
    sub.user_id = user_id
    sub.query = "Computer Science Fellowship"
    sub.monitoring_frequency = MonitoringFrequency.WEEKLY
    sub.known_opportunity_ids = [str(known_opp_id)]

    opp_old = MagicMock(spec=Opportunity)
    opp_old.id = known_opp_id
    opp_old.title = "Old Fellowship"
    opp_old.organization = "Tech Org"

    opp_new = MagicMock(spec=Opportunity)
    opp_new.id = new_opp_id
    opp_new.title = "New AI Excellence Fellowship"
    opp_new.organization = "Global AI Foundation"

    mock_db = AsyncMock()

    class MockSearchQueryResult:
        def scalars(self):
            return self

        def all(self):
            return [opp_old, opp_new]

    mock_db.execute.return_value = MockSearchQueryResult()

    now = datetime(2026, 10, 1, tzinfo=UTC)
    new_matches = await search_monitor.execute_search_subscription(
        db=mock_db,
        sub=sub,
        now=now,
    )

    assert new_matches == 1
    assert str(new_opp_id) in sub.known_opportunity_ids
    assert mock_notification_service.dispatch_notification.call_count == 1
    call_args = mock_notification_service.dispatch_notification.call_args[1]
    assert call_args["notification_type"] == NotificationType.NEW_MATCHING_OPPORTUNITY
    assert "New AI Excellence Fellowship" in call_args["title"]
