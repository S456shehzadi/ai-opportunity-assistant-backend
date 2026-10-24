from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class QueryIntentSample(BaseModel):
    """Training example for query understanding models."""

    query: str
    target_category: str
    target_country: str | None = None
    extracted_keywords: list[str] = Field(default_factory=list)


class ExtractionSample(BaseModel):
    """Training example for web text opportunity extraction."""

    html_snippet: str
    source_url: str
    ground_truth_opportunity: dict[str, Any]


class EligibilitySample(BaseModel):
    """Training example for candidate eligibility determination."""

    user_profile: dict[str, Any]
    opportunity_criteria: dict[str, Any]
    ground_truth_eligible: bool
    ground_truth_reasons: list[str] = Field(default_factory=list)


class UserFeedbackSample(BaseModel):
    """Reinforcement learning and preference alignment feedback."""

    interaction_id: str
    user_query: str
    retrieved_opportunity_id: str
    rating: int = Field(ge=1, le=5)
    feedback_text: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
