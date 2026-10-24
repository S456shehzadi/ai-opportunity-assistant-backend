"""Notifications schemas module."""

from app.notifications.schemas.notification import (
    NotificationBase,
    NotificationCreate,
    NotificationDeliveryResponse,
    NotificationResponse,
    UnreadCountResponse,
)
from app.notifications.schemas.preference import (
    NotificationPreferenceResponse,
    NotificationPreferenceUpdate,
)

__all__ = [
    "NotificationBase",
    "NotificationCreate",
    "NotificationDeliveryResponse",
    "NotificationPreferenceResponse",
    "NotificationPreferenceUpdate",
    "NotificationResponse",
    "UnreadCountResponse",
]
