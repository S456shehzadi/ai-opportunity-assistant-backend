"""Service providing automated prioritization, classification, and routing of beta defects."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.analytics.models.event import EventType
from app.analytics.schemas.event import UserEventCreate
from app.analytics.services.analytics_service import AnalyticsService
from app.feedback.schemas.triage import (
    BetaFeedbackSubmission,
    BetaTriageCategory,
    TriagedFeedbackItem,
    TriagePriority,
)

logger = logging.getLogger(__name__)


# Category Base Severity Weights
CATEGORY_BASE_SCORES: dict[BetaTriageCategory, tuple[TriagePriority, float]] = {
    BetaTriageCategory.CRITICAL_SECURITY_PRIVACY: (TriagePriority.CRITICAL_P0, 95.0),
    BetaTriageCategory.ELIGIBILITY_OR_DEADLINE_ERROR: (TriagePriority.HIGH_P1, 75.0),
    BetaTriageCategory.INCORRECT_OPPORTUNITY_INFO: (TriagePriority.HIGH_P1, 70.0),
    BetaTriageCategory.BROKEN_FUNCTIONALITY: (TriagePriority.HIGH_P1, 65.0),
    BetaTriageCategory.SEARCH_QUALITY_ISSUE: (TriagePriority.MEDIUM_P2, 50.0),
    BetaTriageCategory.PERFORMANCE_ISSUE: (TriagePriority.MEDIUM_P2, 45.0),
    BetaTriageCategory.USABILITY_ISSUE: (TriagePriority.MEDIUM_P2, 40.0),
    BetaTriageCategory.FEATURE_REQUEST: (TriagePriority.LOW_P3, 20.0),
}


class BetaFeedbackTriageService:
    """Classifies, scores, and prioritizes beta user feedback reports."""

    _instance: BetaFeedbackTriageService | None = None

    def __init__(self, analytics_service: AnalyticsService | None = None) -> None:
        self.analytics_service = analytics_service or AnalyticsService()
        self._triaged_items: list[TriagedFeedbackItem] = []

    @classmethod
    def get_instance(cls) -> BetaFeedbackTriageService:
        if cls._instance is None:
            cls._instance = BetaFeedbackTriageService()
        return cls._instance

    def calculate_priority_score(
        self,
        category: BetaTriageCategory,
        description: str,
    ) -> tuple[TriagePriority, float]:
        """Calculates deterministic score based on category heuristics and description."""
        base_priority, base_score = CATEGORY_BASE_SCORES.get(
            category, (TriagePriority.MEDIUM_P2, 50.0)
        )

        score_modifier = 0.0
        lower_desc = description.lower()

        # Urgency escalation keywords
        if any(w in lower_desc for w in ["crash", "leak", "token", "password", "vulnerability"]):
            score_modifier += 10.0
        if any(w in lower_desc for w in ["expired", "wrong deadline", "rejected because of date"]):
            score_modifier += 8.0
        if any(w in lower_desc for w in ["cannot apply", "link broken", "404", "error 500"]):
            score_modifier += 5.0

        final_score = min(100.0, max(0.0, base_score + score_modifier))

        if category == BetaTriageCategory.CRITICAL_SECURITY_PRIVACY or final_score >= 95.0:
            assigned_priority = TriagePriority.CRITICAL_P0
        elif final_score >= 65.0:
            assigned_priority = TriagePriority.HIGH_P1
        elif final_score >= 35.0:
            assigned_priority = TriagePriority.MEDIUM_P2
        else:
            assigned_priority = TriagePriority.LOW_P3

        return assigned_priority, final_score

    async def triage_submission(
        self,
        user_id: UUID,
        payload: BetaFeedbackSubmission,
        db: Any | None = None,
    ) -> TriagedFeedbackItem:
        """Processes and enriches feedback, assigning severity and routing flags."""
        priority, score = self.calculate_priority_score(
            category=payload.category,
            description=payload.description,
        )

        item = TriagedFeedbackItem(
            id=uuid.uuid4(),
            user_id=user_id,
            category=payload.category,
            priority=priority,
            priority_score=score,
            title=payload.title,
            description=payload.description,
            target_opportunity_id=payload.target_opportunity_id,
            target_url=payload.target_url,
            status="TRIAGED",
            routed_to_review=(priority in [TriagePriority.CRITICAL_P0, TriagePriority.HIGH_P1]),
            routed_to_eval_dataset=(
                payload.category
                in [
                    BetaTriageCategory.INCORRECT_OPPORTUNITY_INFO,
                    BetaTriageCategory.ELIGIBILITY_OR_DEADLINE_ERROR,
                    BetaTriageCategory.SEARCH_QUALITY_ISSUE,
                ]
            ),
            created_at=datetime.now(UTC),
        )

        self._triaged_items.append(item)

        logger.info(
            "Triaged beta feedback '%s': Category=%s, Priority=%s, Score=%.1f",
            item.title,
            item.category.value,
            item.priority.value,
            item.priority_score,
        )

        # Log privacy-sanitized analytics event if DB session available
        if db is not None:
            try:
                await self.analytics_service.track_event(
                    db=db,
                    user_id=user_id,
                    event=UserEventCreate(
                        event_type=EventType.FEEDBACK_SUBMITTED,
                        entity_type="BETA_FEEDBACK",
                        entity_id=str(item.id),
                        metadata_json={
                            "category": item.category.value,
                            "priority": item.priority.value,
                            "score": item.priority_score,
                        },
                    ),
                )
            except Exception as e:
                logger.warning("Failed to record analytics event for beta feedback: %s", e)

        return item

    def get_triaged_items(
        self,
        category: BetaTriageCategory | None = None,
        priority: TriagePriority | None = None,
        limit: int = 50,
    ) -> list[TriagedFeedbackItem]:
        """Returns filtered triaged items sorted by priority score descending."""
        items = self._triaged_items
        if category:
            items = [i for i in items if i.category == category]
        if priority:
            items = [i for i in items if i.priority == priority]

        # Highest priority first
        sorted_items = sorted(items, key=lambda x: x.priority_score, reverse=True)
        return sorted_items[:limit]

    def get_triage_metrics(self) -> dict[str, Any]:
        """Consolidates feedback distribution metrics for beta dashboard."""
        category_counts: dict[str, int] = {c.value: 0 for c in BetaTriageCategory}
        priority_counts: dict[str, int] = {p.value: 0 for p in TriagePriority}

        for item in self._triaged_items:
            category_counts[item.category.value] = category_counts.get(item.category.value, 0) + 1
            priority_counts[item.priority.value] = priority_counts.get(item.priority.value, 0) + 1

        return {
            "total_feedback_count": len(self._triaged_items),
            "by_category": category_counts,
            "by_priority": priority_counts,
            "critical_unresolved_count": priority_counts.get(TriagePriority.CRITICAL_P0.value, 0),
        }

    def clear_for_testing(self) -> None:
        self._triaged_items.clear()


def get_triage_service() -> BetaFeedbackTriageService:
    return BetaFeedbackTriageService.get_instance()
