"""Unified opportunity monitoring engine orchestrating source checks, diffs, and sweeps."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.opportunity import Opportunity
from app.monitoring.interfaces.monitor import IOpportunityMonitoringEngine
from app.monitoring.models.change_event import OpportunityChangeEvent
from app.monitoring.models.subscription import MonitoringStatus, OpportunitySubscription
from app.monitoring.schemas.monitoring import MonitoringRunSummary
from app.monitoring.services.change_detection_service import ChangeDetectionService
from app.monitoring.services.deadline_monitor import DeadlineMonitor
from app.monitoring.services.opportunity_refresh_service import OpportunityRefreshService
from app.monitoring.services.search_monitor import SearchMonitor
from app.monitoring.services.source_monitor import SourceMonitor
from app.notifications.models.notification import NotificationPriority, NotificationType
from app.notifications.services.notification_service import NotificationService
from app.opportunities.extraction.engine import OpportunityExtractionEngine
from app.web.models.document import WebDocument

logger = logging.getLogger(__name__)


class OpportunityMonitoringEngine(IOpportunityMonitoringEngine):
    """Core monitoring engine for the AI Opportunity Assistant platform."""

    def __init__(
        self,
        source_monitor: SourceMonitor | None = None,
        change_detector: ChangeDetectionService | None = None,
        refresh_service: OpportunityRefreshService | None = None,
        deadline_monitor: DeadlineMonitor | None = None,
        search_monitor: SearchMonitor | None = None,
        notification_service: NotificationService | None = None,
        extraction_engine: OpportunityExtractionEngine | None = None,
    ) -> None:
        self.notification_service = notification_service or NotificationService()
        self.source_monitor = source_monitor or SourceMonitor()
        self.change_detector = change_detector or ChangeDetectionService()
        self.refresh_service = refresh_service or OpportunityRefreshService(
            change_detector=self.change_detector,
            notification_service=self.notification_service,
        )
        self.deadline_monitor = deadline_monitor or DeadlineMonitor(
            notification_service=self.notification_service
        )
        self.search_monitor = search_monitor or SearchMonitor(
            notification_service=self.notification_service
        )
        self.extraction_engine = extraction_engine or OpportunityExtractionEngine()

    async def check_opportunity(
        self,
        db: AsyncSession,
        subscription: OpportunitySubscription,
    ) -> list[OpportunityChangeEvent]:
        """Performs an authoritative source check for a single subscription."""
        query = select(Opportunity).where(Opportunity.id == subscription.opportunity_id)
        result = await db.execute(query)
        opportunity = result.scalar_one_or_none()
        if not opportunity:
            return []

        source_url = opportunity.official_source_url or opportunity.application_url
        if not source_url:
            return []

        # 1. Check availability
        is_avail, status_code, err = await self.source_monitor.check_source_availability(source_url)
        if not is_avail:
            # Deterministic failure handling: mark SOURCE_UNAVAILABLE, NEVER mark as closed
            subscription.monitoring_status = MonitoringStatus.SOURCE_UNAVAILABLE
            await db.commit()

            dedupe_key = (
                f"source_unavail_{opportunity.id}_{subscription.user_id}_{datetime.now(UTC).date()}"
            )
            await self.notification_service.dispatch_notification(
                db=db,
                user_id=subscription.user_id,
                notification_type=NotificationType.SOURCE_UNAVAILABLE,
                title=f"Source Temporarily Unavailable: {opportunity.title}",
                message=(
                    f"Official page returned HTTP {status_code} ({err or 'network error'}). "
                    "We will automatically retry with exponential backoff."
                ),
                priority=NotificationPriority.LOW,
                opportunity_id=opportunity.id,
                deduplication_key=dedupe_key,
            )
            return []

        # If it was previously SOURCE_UNAVAILABLE and is now back
        if subscription.monitoring_status == MonitoringStatus.SOURCE_UNAVAILABLE:
            subscription.monitoring_status = MonitoringStatus.ACTIVE

        # 2. Fetch fresh content and extract facts
        raw_html, clean_text, metadata = await self.source_monitor.fetch_latest_content(source_url)
        if not clean_text and not raw_html:
            return []

        synthetic_doc = WebDocument(
            original_url=source_url,
            final_url=metadata.get("final_url") or source_url,
            raw_html=raw_html or "",
            clean_text=clean_text or "",
            title=metadata.get("title") or opportunity.title,
            domain=metadata.get("domain") or opportunity.source_domain,
            status_code=metadata.get("status_code", 200),
        )

        extracted = await self.extraction_engine.extract(synthetic_doc)

        new_data: dict[str, Any] = {
            "deadline": extracted.deadline.value if extracted.deadline else None,
            "status": "active" if not extracted.is_rolling else "active",
            "funding_type": extracted.funding_type,
            "funding_amount": (
                extracted.funding_amount.amount_text if extracted.funding_amount else None
            ),
            "degree_levels": extracted.degree_levels or [],
            "eligible_nationalities": extracted.eligible_nationalities or [],
            "application_url": opportunity.application_url,
            "english_tests": [t.test_type for t in (extracted.english_tests or [])],
        }

        # 3. Process structured diffs, refresh database, and notify users
        events = await self.refresh_service.process_opportunity_updates(
            db=db,
            opportunity_id=opportunity.id,
            new_data=new_data,
        )

        return events

    async def sweep_deadlines(self, db: AsyncSession) -> int:
        """Sweeps deadlines across all active subscriptions."""
        return await self.deadline_monitor.sweep_deadlines(db)

    async def sweep_searches(self, db: AsyncSession) -> int:
        """Sweeps searches across all active search subscriptions."""
        return await self.search_monitor.sweep_searches(db)

    async def run_monitoring_cycle(
        self,
        db: AsyncSession,
        limit_subscriptions: int = 50,
    ) -> MonitoringRunSummary:
        """Executes a full monitoring cycle: due subscriptions, deadlines, and searches."""
        now = datetime.now(UTC)
        summary = MonitoringRunSummary()

        # 1. Process due opportunity subscriptions
        query = (
            select(OpportunitySubscription)
            .where(
                OpportunitySubscription.monitoring_status == MonitoringStatus.ACTIVE,
                or_(
                    OpportunitySubscription.next_check_at.is_(None),
                    OpportunitySubscription.next_check_at <= now,
                ),
            )
            .limit(limit_subscriptions)
        )
        result = await db.execute(query)
        subs = result.scalars().all()

        for sub in subs:
            summary.checks_run += 1
            try:
                events = await self.check_opportunity(db, sub)
                summary.changes_detected += len(events)
            except Exception:
                logger.exception("Error checking subscription %s", sub.id)
                summary.errors_encountered += 1

        # 2. Deadline sweep
        try:
            deadline_notifs = await self.sweep_deadlines(db)
            summary.notifications_created += deadline_notifs
        except Exception:
            logger.exception("Error during deadline sweep")
            summary.errors_encountered += 1

        # 3. Search sweep
        try:
            search_matches = await self.sweep_searches(db)
            summary.notifications_created += search_matches
        except Exception:
            logger.exception("Error during search sweep")
            summary.errors_encountered += 1

        return summary
