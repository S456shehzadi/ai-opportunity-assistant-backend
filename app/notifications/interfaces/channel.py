"""Notification channel interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.notifications.models.notification import DeliveryChannel, Notification


class INotificationChannel(ABC):
    """Abstract provider for dispatching notifications to a specific channel."""

    @property
    @abstractmethod
    def channel(self) -> DeliveryChannel:
        """The channel type handled by this provider."""
        pass

    @abstractmethod
    async def send(self, notification: Notification) -> tuple[bool, str | None]:
        """Dispatch notification. Returns (success, error_message)."""
        pass
