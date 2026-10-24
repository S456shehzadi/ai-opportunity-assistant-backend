"""Service coordinating opportunity data refresh and downstream re-evaluations."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.opportunity import Opportunity
from app.models.profile import UserProfile
from app.monitoring.models.change_event import (
    OpportunityChangeEvent,
    OpportunityChangeType,
)
from app.monitoring.models.subscription import OpportunitySubscription
from app.monitoring.policies.frequency_policy import MonitoringFrequencyPolicy
from app.monitoring.services.change_detection_service import ChangeDetectionService
from app.notifications.models.notification import NotificationPriority, NotificationType
from app.notifications.services.notification_service import NotificationService
from app.opportunities.eligibility.engine import EligibilityEngine

logger = logging.getLogger(__name__)


class OpportunityRefreshService:
    """Refreshes structured opportunity details and triggers downstream eligibility updates."""

    def __init__(
        self,
        change_detector: ChangeDetectionService | None = None,
        notification_service: NotificationService | None = None,
        eligibility_engine: EligibilityEngine | None = None,
    ) -> None:
        self.change_detector = change_detector or ChangeDetectionService()
        self.notification_service = notification_service or NotificationService()
        self.eligibility_engine = eligibility_engine or EligibilityEngine()

    async def process_opportunity_updates(
        self,
        db: AsyncSession,
        opportunity_id: UUID,
        new_data: dict[str, Any],
    ) -> list[OpportunityChangeEvent]:
        """Compares incoming facts with stored opportunity, applies updates, and notifies users."""
        now = datetime.now(UTC)

        query = select(Opportunity).where(Opportunity.id == opportunity_id)
        result = await db.execute(query)
        opportunity = result.scalar_one_or_none()
        if not opportunity:
            logger.warning("Opportunity %s not found for refresh", opportunity_id)
            return []

        # 1. Snapshot old state
        old_data: dict[str, Any] = {
            "deadline": opportunity.deadline,
            "status": str(opportunity.status),
            "funding_type": opportunity.funding_type,
            "funding_amount": opportunity.funding_amount,
            "degree_levels": opportunity.degree_levels or [],
            "eligible_nationalities": opportunity.eligible_nationalities or [],
            "application_url": opportunity.application_url,
            "english_tests": getattr(opportunity, "english_tests", []),
        }

        # 2. Detect structured differences
        events = self.change_detector.detect_structured_changes(
            old_data=old_data,
            new_data=new_data,
            opportunity_id=opportunity_id,
        )

        # 3. Apply updates to the Opportunity record
        if "deadline" in new_data and new_data["deadline"]:
            parsed_dl = self.change_detector._parse_date(new_data["deadline"])
            if parsed_dl:
                opportunity.deadline = parsed_dl

        if "status" in new_data and new_data["status"]:
            new_status_str = str(new_data["status"]).lower()
            if hasattr(opportunity.status, "__class__"):
                try:
                    opportunity.status = opportunity.status.__class__(new_status_str)
                except Exception:
                    pass

        if "funding_type" in new_data and new_data["funding_type"]:
            opportunity.funding_type = str(new_data["funding_type"])
        if "funding_amount" in new_data and new_data["funding_amount"]:
            opportunity.funding_amount = str(new_data["funding_amount"])
        if "application_url" in new_data and new_data["application_url"]:
            opportunity.application_url = str(new_data["application_url"])
        if "degree_levels" in new_data and isinstance(new_data["degree_levels"], list):
            opportunity.degree_levels = new_data["degree_levels"]
        if "eligible_nationalities" in new_data and isinstance(
            new_data["eligible_nationalities"], list
        ):
            opportunity.eligible_nationalities = new_data["eligible_nationalities"]

        opportunity.last_verified_at = now

        # Persist change events
        for ev in events:
            db.add(ev)

        # 4. Notify subscribed users and re-evaluate downstream eligibility
        subs_query = select(OpportunitySubscription).where(
            OpportunitySubscription.opportunity_id == opportunity_id,
            OpportunitySubscription.monitoring_status == "ACTIVE",
        )
        subs_result = await db.execute(subs_query)
        subscriptions = subs_result.scalars().all()

        for sub in subscriptions:
            sub.last_checked_at = now
            if events:
                sub.last_changed_at = now

            # Recalculate next check
            freq_result = MonitoringFrequencyPolicy.calculate_next_check(
                current_deadline=opportunity.deadline,
                last_changed_at=sub.last_changed_at,
                user_preference=sub.monitoring_frequency,
                now=now,
            )
            sub.next_check_at = freq_result.next_check_at

            # Dispatch notification for each relevant event
            for ev in events:
                # Check user subscription filter toggles
                if (
                    ev.change_type
                    in (
                        OpportunityChangeType.DEADLINE_CHANGED,
                        OpportunityChangeType.DEADLINE_EXTENDED,
                        OpportunityChangeType.DEADLINE_SHORTENED,
                    )
                    and not sub.deadline_alerts_enabled
                ):
                    continue

                if (
                    ev.change_type == OpportunityChangeType.FUNDING_CHANGED
                    and not sub.funding_change_alerts_enabled
                ):
                    continue

                if (
                    ev.change_type
                    in (
                        OpportunityChangeType.PROGRAM_OPENED,
                        OpportunityChangeType.PROGRAM_CLOSED,
                        OpportunityChangeType.PROGRAM_PAUSED,
                        OpportunityChangeType.APPLICATION_STATUS_CHANGED,
                    )
                    and not sub.status_change_alerts_enabled
                ):
                    continue

                if (
                    ev.change_type
                    in (
                        OpportunityChangeType.DEGREE_REQUIREMENT_CHANGED,
                        OpportunityChangeType.TEST_REQUIREMENT_CHANGED,
                        OpportunityChangeType.NATIONALITY_ELIGIBILITY_CHANGED,
                    )
                    and not sub.requirement_change_alerts_enabled
                ):
                    continue

                notif_type = NotificationType.STATUS_CHANGED
                if "DEADLINE" in ev.change_type.name:
                    notif_type = NotificationType.DEADLINE_CHANGED
                elif "FUNDING" in ev.change_type.name:
                    notif_type = NotificationType.FUNDING_CHANGED
                elif "REQUIREMENT" in ev.change_type.name or "ELIGIBILITY" in ev.change_type.name:
                    notif_type = NotificationType.REQUIREMENT_CHANGED
                elif ev.change_type == OpportunityChangeType.PROGRAM_OPENED:
                    notif_type = NotificationType.APPLICATION_OPENED

                priority = NotificationPriority.NORMAL
                if ev.notification_priority == "HIGH":
                    priority = NotificationPriority.HIGH
                elif ev.notification_priority == "URGENT":
                    priority = NotificationPriority.URGENT

                ts_hour = now.strftime("%Y%m%d_%H")
                dedupe_key = (
                    f"opp_{opportunity_id}_u_{sub.user_id}_e_{ev.change_type.value}_{ts_hour}"
                )

                await self.notification_service.dispatch_notification(
                    db=db,
                    user_id=sub.user_id,
                    notification_type=notif_type,
                    title=f"Update: {opportunity.title}",
                    message=ev.evidence,
                    priority=priority,
                    opportunity_id=opportunity_id,
                    change_event_id=ev.id,
                    deduplication_key=dedupe_key,
                )

            # Re-evaluate eligibility if requirement fields changed
            eligibility_changed = any(
                ev.change_type
                in (
                    OpportunityChangeType.DEGREE_REQUIREMENT_CHANGED,
                    OpportunityChangeType.TEST_REQUIREMENT_CHANGED,
                    OpportunityChangeType.NATIONALITY_ELIGIBILITY_CHANGED,
                    OpportunityChangeType.ELIGIBILITY_CHANGED,
                )
                for ev in events
            )
            if eligibility_changed:
                await self._reevaluate_user_eligibility(
                    db=db,
                    user_id=sub.user_id,
                    opportunity=opportunity,
                )

        await db.commit()
        return events

    async def _reevaluate_user_eligibility(
        self,
        db: AsyncSession,
        user_id: UUID,
        opportunity: Opportunity,
    ) -> None:
        """Runs the EligibilityEngine to check if requirement changes altered user eligibility."""
        try:
            profile_query = select(UserProfile).where(UserProfile.user_id == user_id)
            profile_result = await db.execute(profile_query)
            profile = profile_result.scalar_one_or_none()
            if not profile:
                return

            eval_result = await self.eligibility_engine.evaluate_eligibility(
                profile=profile,
                opportunity=opportunity,
                use_cache=False,
            )

            notif_msg = (
                f"Eligibility status updated to '{eval_result.overall_status.value}' "
                f"({eval_result.satisfaction_percentage:.0f}% requirements met). "
                f"{eval_result.summary.headline}"
            )
            dedupe_key = (
                f"eligibility_{opportunity.id}_{user_id}_{eval_result.overall_status.value}"
            )

            await self.notification_service.dispatch_notification(
                db=db,
                user_id=user_id,
                notification_type=NotificationType.ELIGIBILITY_STATUS_CHANGED,
                title=f"Eligibility Change: {opportunity.title}",
                message=notif_msg,
                priority=NotificationPriority.HIGH,
                opportunity_id=opportunity.id,
                deduplication_key=dedupe_key,
            )
        except Exception as exc:
            logger.warning(
                "Downstream eligibility re-evaluation failed for user %s: %s", user_id, exc
            )
