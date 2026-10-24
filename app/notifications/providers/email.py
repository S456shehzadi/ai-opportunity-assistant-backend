"""Email notification delivery provider stub."""

from __future__ import annotations

import logging

from app.notifications.interfaces.channel import INotificationChannel
from app.notifications.models.notification import DeliveryChannel, Notification

logger = logging.getLogger(__name__)


class EmailNotificationProvider(INotificationChannel):
    """Handles email notification dispatch."""

    @property
    def channel(self) -> DeliveryChannel:
        return DeliveryChannel.EMAIL

    async def send(self, notification: Notification) -> tuple[bool, str | None]:
        """Dispatches email notification."""
        logger.info(
            "Dispatching email notification: %s to user %s",
            notification.title,
            notification.user_id,
        )
        return True, None
