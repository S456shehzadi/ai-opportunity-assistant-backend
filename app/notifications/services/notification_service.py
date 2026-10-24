"""Notification service managing dispatch, fatigue suppression, and preferences."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.monitoring.policies.fatigue_policy import NotificationFatiguePolicy
from app.notifications.interfaces.channel import INotificationChannel
from app.notifications.models.notification import (
    DeliveryChannel,
    DeliveryStatus,
    Notification,
    NotificationDelivery,
    NotificationPriority,
    NotificationType,
)
from app.notifications.models.preference import NotificationPreference
from app.notifications.providers.email import EmailNotificationProvider
from app.notifications.providers.in_app import InAppNotificationProvider
from app.notifications.providers.push import PushNotificationProvider
from app.notifications.schemas.preference import NotificationPreferenceUpdate

logger = logging.getLogger(__name__)


class NotificationService:
    """Core notification orchestrator ensuring zero-fatigue, auditable alerts."""

    def __init__(
        self,
        channels: dict[DeliveryChannel, INotificationChannel] | None = None,
    ) -> None:
        self.channels = channels or {
            DeliveryChannel.IN_APP: InAppNotificationProvider(),
            DeliveryChannel.PUSH: PushNotificationProvider(),
            DeliveryChannel.EMAIL: EmailNotificationProvider(),
        }

    async def get_or_create_preferences(
        self,
        db: AsyncSession,
        user_id: UUID,
    ) -> NotificationPreference:
        """Fetch existing user preferences or initialize defaults."""
        query = select(NotificationPreference).where(NotificationPreference.user_id == user_id)
        result = await db.execute(query)
        pref = result.scalar_one_or_none()
        if pref is None:
            pref = NotificationPreference(
                user_id=user_id,
                enable_notifications=True,
                enable_in_app=True,
                enable_push=False,
                enable_email=False,
                enable_deadline_alerts=True,
                enable_funding_alerts=True,
                enable_eligibility_alerts=True,
                enable_new_opportunity_alerts=True,
                enable_status_alerts=True,
                important_changes_only=False,
                daily_notification_limit=5,
                quiet_hours_enabled=False,
            )
            db.add(pref)
            await db.commit()
            await db.refresh(pref)
        return pref

    async def update_preferences(
        self,
        db: AsyncSession,
        user_id: UUID,
        update_data: NotificationPreferenceUpdate,
    ) -> NotificationPreference:
        """Update notification settings for a user."""
        pref = await self.get_or_create_preferences(db, user_id)
        for field, value in update_data.model_dump(exclude_unset=True).items():
            setattr(pref, field, value)
        await db.commit()
        await db.refresh(pref)
        return pref

    async def dispatch_notification(
        self,
        db: AsyncSession,
        user_id: UUID,
        notification_type: NotificationType,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        opportunity_id: UUID | None = None,
        change_event_id: UUID | None = None,
        deduplication_key: str | None = None,
        metadata: dict[str, Any] | None = None,
        requested_channels: list[DeliveryChannel] | None = None,
    ) -> Notification | None:
        """Validates fatigue controls, records the notification, and dispatches via channels."""
        now = datetime.now(UTC)
        pref = await self.get_or_create_preferences(db, user_id)

        # 1. Deduplication key check
        dedupe_exists = False
        if deduplication_key:
            dedupe_query = select(func.count(Notification.id)).where(
                Notification.user_id == user_id,
                Notification.deduplication_key == deduplication_key,
            )
            count_result = await db.execute(dedupe_query)
            dedupe_exists = (count_result.scalar() or 0) > 0

        # 2. Daily sent count
        today_start = datetime.combine(now.date(), datetime.min.time(), tzinfo=UTC)
        daily_count_query = select(func.count(Notification.id)).where(
            Notification.user_id == user_id,
            Notification.created_at >= today_start,
        )
        daily_result = await db.execute(daily_count_query)
        daily_count = daily_result.scalar() or 0

        # 3. Recent notification for this opportunity
        recent_notification_at: datetime | None = None
        if opportunity_id:
            recent_query = (
                select(Notification.created_at)
                .where(
                    Notification.user_id == user_id,
                    Notification.opportunity_id == opportunity_id,
                )
                .order_by(Notification.created_at.desc())
                .limit(1)
            )
            recent_result = await db.execute(recent_query)
            recent_notification_at = recent_result.scalar_one_or_none()

        # 4. Evaluate fatigue policy
        decision = NotificationFatiguePolicy.evaluate(
            user_preference=pref,
            notification_type=notification_type,
            priority=priority,
            opportunity_id=opportunity_id,
            recent_opportunity_notification_at=recent_notification_at,
            notifications_sent_today_count=daily_count,
            deduplication_key_exists=dedupe_exists,
            now=now,
        )

        if not decision.allow:
            logger.info(
                "Notification suppressed for user %s: %s (Key: %s)",
                user_id,
                decision.suppress_reason,
                deduplication_key,
            )
            return None

        # 5. Create notification record
        notification = Notification(
            user_id=user_id,
            opportunity_id=opportunity_id,
            change_event_id=change_event_id,
            notification_type=notification_type,
            priority=priority,
            title=title,
            message=message,
            deduplication_key=deduplication_key,
            metadata_json=metadata or {},
        )
        db.add(notification)
        await db.flush()  # populate ID

        # 6. Resolve target channels based on preferences and requests
        target_channels: list[DeliveryChannel] = []
        if pref.enable_in_app:
            target_channels.append(DeliveryChannel.IN_APP)
        if pref.enable_push and (
            requested_channels is None or DeliveryChannel.PUSH in requested_channels
        ):
            target_channels.append(DeliveryChannel.PUSH)
        if pref.enable_email and (
            requested_channels is None or DeliveryChannel.EMAIL in requested_channels
        ):
            target_channels.append(DeliveryChannel.EMAIL)

        # Ensure in-app is at least added if no external channel
        if not target_channels:
            target_channels = [DeliveryChannel.IN_APP]

        # 7. Create delivery records and dispatch
        for chan in target_channels:
            provider = self.channels.get(chan)
            delivery = NotificationDelivery(
                notification_id=notification.id,
                channel=chan,
                status=DeliveryStatus.PENDING,
            )
            db.add(delivery)
            await db.flush()

            settings = get_settings()
            if (
                settings.is_staging
                and settings.STAGING_NOTIFICATION_SANDBOX
                and chan in (DeliveryChannel.PUSH, DeliveryChannel.EMAIL)
            ):
                logger.info("Staging sandbox prevented external dispatch for channel %s", chan)
                delivery.status = DeliveryStatus.DELIVERED
                delivery.delivered_at = datetime.now(UTC)
                delivery.error_message = "[SANDBOX_STAGING_SIMULATION]"
                continue

            if provider:
                success, err = await provider.send(notification)
                if success:
                    delivery.status = DeliveryStatus.DELIVERED
                    delivery.delivered_at = datetime.now(UTC)
                else:
                    delivery.status = DeliveryStatus.FAILED
                    delivery.error_message = err

        await db.commit()
        await db.refresh(notification)
        return notification

    async def get_user_notifications(
        self,
        db: AsyncSession,
        user_id: UUID,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Notification]:
        """Fetch notifications for a specific user with isolation guarantee."""
        query = (
            select(Notification)
            .options(selectinload(Notification.deliveries))
            .where(Notification.user_id == user_id)
        )
        if unread_only:
            query = query.where(Notification.read_at.is_(None))

        query = query.order_by(Notification.created_at.desc()).offset(offset).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_unread_count(self, db: AsyncSession, user_id: UUID) -> int:
        """Count unread notifications for a user."""
        query = select(func.count(Notification.id)).where(
            Notification.user_id == user_id,
            Notification.read_at.is_(None),
        )
        result = await db.execute(query)
        return result.scalar() or 0

    async def mark_as_read(
        self,
        db: AsyncSession,
        user_id: UUID,
        notification_id: UUID,
    ) -> Notification | None:
        """Mark a specific notification as read, enforcing user ownership."""
        query = select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
        result = await db.execute(query)
        notification = result.scalar_one_or_none()
        if notification and notification.read_at is None:
            notification.read_at = datetime.now(UTC)
            await db.commit()
            await db.refresh(notification)
        return notification

    async def mark_all_as_read(self, db: AsyncSession, user_id: UUID) -> int:
        """Mark all unread notifications for a user as read."""
        now = datetime.now(UTC)
        query = select(Notification).where(
            Notification.user_id == user_id,
            Notification.read_at.is_(None),
        )
        result = await db.execute(query)
        notifications = result.scalars().all()
        count = 0
        for notif in notifications:
            notif.read_at = now
            count += 1
        if count > 0:
            await db.commit()
        return count

    async def delete_notification(
        self,
        db: AsyncSession,
        user_id: UUID,
        notification_id: UUID,
    ) -> bool:
        """Delete a notification owned by user."""
        query = select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
        result = await db.execute(query)
        notification = result.scalar_one_or_none()
        if notification:
            await db.delete(notification)
            await db.commit()
            return True
        return False
