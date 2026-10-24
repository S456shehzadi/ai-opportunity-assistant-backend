"""Search monitoring service tracking query updates and discovering new matching opportunities."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.opportunity import Opportunity
from app.monitoring.models.subscription import MonitoringFrequency, SearchSubscription
from app.notifications.models.notification import NotificationPriority, NotificationType
from app.notifications.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class SearchMonitor:
    """Monitors saved search queries and alerts users when new matching opportunities appear."""

    def __init__(self, notification_service: NotificationService | None = None) -> None:
        self.notification_service = notification_service or NotificationService()

    async def sweep_searches(
        self,
        db: AsyncSession,
        now: datetime | None = None,
    ) -> int:
        """Executes active search subscriptions and alerts users of newly discovered matches."""
        current_time = now or datetime.now(UTC)

        query = select(SearchSubscription).where(
            SearchSubscription.monitoring_status == "ACTIVE",
            or_(
                SearchSubscription.next_search_at.is_(None),
                SearchSubscription.next_search_at <= current_time,
            ),
        )
        result = await db.execute(query)
        subscriptions = result.scalars().all()

        total_new_matches = 0
        for sub in subscriptions:
            try:
                new_matches = await self.execute_search_subscription(db, sub, current_time)
                total_new_matches += new_matches
            except Exception as exc:
                logger.warning("Error running search subscription %s: %s", sub.id, exc)

        return total_new_matches

    async def execute_search_subscription(
        self,
        db: AsyncSession,
        sub: SearchSubscription,
        now: datetime,
    ) -> int:
        """Runs candidate matching for a single search subscription and notifies user."""
        known_ids = set(sub.known_opportunity_ids or [])

        # Match opportunities by title/description containing query terms
        query_terms = [t.strip().lower() for t in sub.query.split() if len(t.strip()) > 2]
        base_query = select(Opportunity).where(Opportunity.status != "expired")

        if query_terms:
            filters = []
            for term in query_terms:
                filters.append(Opportunity.title.ilike(f"%{term}%"))
                filters.append(Opportunity.description.ilike(f"%{term}%"))
                filters.append(Opportunity.organization.ilike(f"%{term}%"))
            base_query = base_query.where(or_(*filters))

        result = await db.execute(base_query.limit(20))
        matching_opps = result.scalars().all()

        new_opps: list[Opportunity] = []
        for opp in matching_opps:
            opp_id_str = str(opp.id)
            if opp_id_str not in known_ids:
                new_opps.append(opp)
                known_ids.add(opp_id_str)

        # Dispatch notifications for new discoveries
        for new_opp in new_opps:
            dedupe_key = f"search_{sub.id}_opp_{new_opp.id}"
            await self.notification_service.dispatch_notification(
                db=db,
                user_id=sub.user_id,
                notification_type=NotificationType.NEW_MATCHING_OPPORTUNITY,
                title=f"New Match for '{sub.query}': {new_opp.title}",
                message=(
                    f"New opportunity matching your search '{sub.query}': "
                    f"{new_opp.title} ({new_opp.organization})."
                ),
                priority=NotificationPriority.NORMAL,
                opportunity_id=new_opp.id,
                deduplication_key=dedupe_key,
                metadata={"monitored_query": sub.query, "search_subscription_id": str(sub.id)},
            )

        # Update subscription state
        sub.known_opportunity_ids = list(known_ids)
        sub.last_searched_at = now

        delta_map = {
            MonitoringFrequency.DAILY: timedelta(days=1),
            MonitoringFrequency.EVERY_3_DAYS: timedelta(days=3),
            MonitoringFrequency.WEEKLY: timedelta(days=7),
            MonitoringFrequency.BIWEEKLY: timedelta(days=14),
            MonitoringFrequency.MONTHLY: timedelta(days=30),
        }
        sub.next_search_at = now + delta_map.get(sub.monitoring_frequency, timedelta(days=7))

        await db.commit()
        return len(new_opps)
