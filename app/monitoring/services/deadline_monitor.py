"""Deadline monitoring service evaluating reminder windows and dispatching alerts."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.opportunity import Opportunity
from app.monitoring.models.subscription import OpportunitySubscription
from app.notifications.models.notification import NotificationPriority, NotificationType
from app.notifications.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class DeadlineMonitor:
    """Evaluates upcoming opportunity deadlines against defined milestone windows."""

    REMINDER_WINDOWS = [30, 14, 7, 3, 1, 0]

    def __init__(self, notification_service: NotificationService | None = None) -> None:
        self.notification_service = notification_service or NotificationService()

    async def sweep_deadlines(
        self,
        db: AsyncSession,
        now: datetime | None = None,
    ) -> int:
        """Evaluates all active subscriptions with deadlines and triggers milestone alerts."""
        current_time = now or datetime.now(UTC)
        today = current_time.date()

        query = (
            select(OpportunitySubscription)
            .options(selectinload(OpportunitySubscription.opportunity))
            .join(Opportunity, OpportunitySubscription.opportunity_id == Opportunity.id)
            .where(
                OpportunitySubscription.monitoring_status == "ACTIVE",
                OpportunitySubscription.deadline_alerts_enabled.is_(True),
                Opportunity.deadline.isnot(None),
            )
        )
        result = await db.execute(query)
        subscriptions = result.scalars().all()

        reminders_sent = 0
        for sub in subscriptions:
            opp = sub.opportunity
            if not opp or not opp.deadline:
                continue

            days_remaining = (opp.deadline - today).days
            if days_remaining in self.REMINDER_WINDOWS:
                sent = await self._dispatch_deadline_reminder(
                    db=db,
                    user_id=sub.user_id,
                    opportunity=opp,
                    days_remaining=days_remaining,
                )
                if sent:
                    reminders_sent += 1

        return reminders_sent

    async def _dispatch_deadline_reminder(
        self,
        db: AsyncSession,
        user_id: UUID,
        opportunity: Opportunity,
        days_remaining: int,
    ) -> bool:
        """Constructs deduplicated, priority-scaled deadline alert."""
        if days_remaining == 0:
            title = f"Final Day: {opportunity.title}"
            message = (
                f"Today is the final deadline to submit your application for {opportunity.title}."
            )
            priority = NotificationPriority.URGENT
        elif days_remaining == 1:
            title = f"1 Day Left: {opportunity.title}"
            message = (
                f"Only 1 day remaining until the deadline ({opportunity.deadline.isoformat()})."
            )
            priority = NotificationPriority.URGENT
        elif days_remaining <= 3:
            title = f"{days_remaining} Days Left: {opportunity.title}"
            message = (
                f"Deadline approaching in {days_remaining} days on "
                f"{opportunity.deadline.isoformat()}."
            )
            priority = NotificationPriority.HIGH
        else:
            title = f"Deadline Reminder: {opportunity.title}"
            message = (
                f"Application deadline is in {days_remaining} days "
                f"({opportunity.deadline.isoformat()})."
            )
            priority = NotificationPriority.NORMAL

        dl_str = opportunity.deadline.isoformat()
        dedupe_key = f"opp_{opportunity.id}_user_{user_id}_w_{days_remaining}_dl_{dl_str}"

        notification = await self.notification_service.dispatch_notification(
            db=db,
            user_id=user_id,
            notification_type=NotificationType.DEADLINE_APPROACHING,
            title=title,
            message=message,
            priority=priority,
            opportunity_id=opportunity.id,
            deduplication_key=dedupe_key,
        )

        return notification is not None
