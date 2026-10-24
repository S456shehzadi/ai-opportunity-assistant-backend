"""In-app notification delivery provider."""

from __future__ import annotations

from app.notifications.interfaces.channel import INotificationChannel
from app.notifications.models.notification import DeliveryChannel, Notification


class InAppNotificationProvider(INotificationChannel):
    """Handles in-app notification delivery."""

    @property
    def channel(self) -> DeliveryChannel:
        return DeliveryChannel.IN_APP

    async def send(self, notification: Notification) -> tuple[bool, str | None]:
        """In-app notifications are natively available in database queries once created."""
        return True, None
