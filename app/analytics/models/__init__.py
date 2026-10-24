"""Analytics models module."""

from app.analytics.models.event import EventType, UserEvent
from app.analytics.models.search_evaluation import SearchEvaluationRecord

__all__ = [
    "EventType",
    "SearchEvaluationRecord",
    "UserEvent",
]
