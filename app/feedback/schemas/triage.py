"""Schemas for beta testing feedback classification and prioritized defect triage."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class BetaTriageCategory(StrEnum):
    """Eight canonical triage classifications required for beta defect management."""

    CRITICAL_SECURITY_PRIVACY = "critical_security_privacy"
    INCORRECT_OPPORTUNITY_INFO = "incorrect_opportunity_info"
    ELIGIBILITY_OR_DEADLINE_ERROR = "eligibility_or_deadline_error"
    SEARCH_QUALITY_ISSUE = "search_quality_issue"
    BROKEN_FUNCTIONALITY = "broken_functionality"
    USABILITY_ISSUE = "usability_issue"
    PERFORMANCE_ISSUE = "performance_issue"
    FEATURE_REQUEST = "feature_request"


class TriagePriority(StrEnum):
    """Urgency tier assigned after automated and human triage."""

    CRITICAL_P0 = "CRITICAL_P0"  # Privacy leak, credential exposure, app crash
    HIGH_P1 = "HIGH_P1"          # Factually wrong deadline, false eligibility claim
    MEDIUM_P2 = "MEDIUM_P2"      # Low search relevance, UI layout glitch
    LOW_P3 = "LOW_P3"            # Cosmetic issue, feature enhancement request


class BetaFeedbackSubmission(BaseModel):
    """Direct lightweight in-app feedback payload submitted by beta participants."""

    category: BetaTriageCategory
    title: str = Field(min_length=3, max_length=150)
    description: str = Field(min_length=5, max_length=2000)
    target_opportunity_id: str | None = None
    target_url: str | None = None
    app_version: str = "0.1.0-beta.1"
    platform: str = "flutter"
    context_data: dict[str, Any] = Field(default_factory=dict)


class TriagedFeedbackItem(BaseModel):
    """Enriched, prioritized feedback item ready for developer review and dataset creation."""

    id: UUID
    user_id: UUID
    category: BetaTriageCategory
    priority: TriagePriority
    priority_score: float = Field(ge=0.0, le=100.0)
    title: str
    description: str
    target_opportunity_id: str | None = None
    target_url: str | None = None
    status: str = "TRIAGED"
    routed_to_review: bool = False
    routed_to_eval_dataset: bool = False
    created_at: datetime
