"""Push notification delivery provider stub."""

from __future__ import annotations

import logging

from app.notifications.interfaces.channel import INotificationChannel
from app.notifications.models.notification import DeliveryChannel, Notification

logger = logging.getLogger(__name__)


class PushNotificationProvider(INotificationChannel):
    """Handles mobile push notification dispatch (FCM/APNs extensible)."""

    @property
    def channel(self) -> DeliveryChannel:
        return DeliveryChannel.PUSH

    async def send(self, notification: Notification) -> tuple[bool, str | None]:
        """Dispatches push message to device tokens."""
        logger.info(
            "Dispatching push notification: [%s] %s to user %s",
            notification.priority,
            notification.title,
            notification.user_id,
        )
        return True, None
