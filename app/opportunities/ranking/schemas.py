"""Schemas and domain models for Personalized Opportunity Ranking & Recommendations."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.ai.query.intent_schemas import SearchIntent
from app.opportunities.eligibility.profile_adapter import UnifiedUserFacts
from app.opportunities.eligibility.schemas import EligibilityResult, OverallEligibilityStatus
from app.opportunities.extraction.schemas import ExtractedOpportunity
from app.opportunities.schemas.opportunity import OpportunityRead
from app.schemas.ai_profile import NormalizedAIProfile


class RankingFactorType(StrEnum):
    """Explicit dimensions evaluated during personalized ranking."""

    PROFILE_FIT = "PROFILE_FIT"
    ELIGIBILITY_COMPLETENESS = "ELIGIBILITY_COMPLETENESS"
    ACADEMIC_FIT = "ACADEMIC_FIT"
    FIELD_FIT = "FIELD_FIT"
    FUNDING_FIT = "FUNDING_FIT"
    LOCATION_FIT = "LOCATION_FIT"
    DEGREE_LEVEL_FIT = "DEGREE_LEVEL_FIT"
    LANGUAGE_FIT = "LANGUAGE_FIT"
    TEST_REQUIREMENT_FIT = "TEST_REQUIREMENT_FIT"
    EXPERIENCE_FIT = "EXPERIENCE_FIT"
    DEADLINE_RELEVANCE = "DEADLINE_RELEVANCE"
    FRESHNESS = "FRESHNESS"
    SOURCE_QUALITY = "SOURCE_QUALITY"
    USER_PREFERENCE_FIT = "USER_PREFERENCE_FIT"
    OPPORTUNITY_CATEGORY_FIT = "OPPORTUNITY_CATEGORY_FIT"
    QUERY_RELEVANCE = "QUERY_RELEVANCE"


class SortMode(StrEnum):
    """User-controlled ordering modes for personalized opportunity results."""

    RELEVANCE = "RELEVANCE"
    FUNDING = "FUNDING"
    DEADLINE = "DEADLINE"
    FRESHNESS = "FRESHNESS"
    ACADEMIC_FIT = "ACADEMIC_FIT"


class PreferencePriority(StrEnum):
    """Importance weighting of a user preference (Required vs Soft)."""

    REQUIRED = "REQUIRED"  # Hard filter
    HIGH = "HIGH"  # Strong positive multiplier
    MEDIUM = "MEDIUM"  # Moderate multiplier
    LOW = "LOW"  # Slight boost


class PreferenceFilterType(StrEnum):
    """Classification of how a preference is executed."""

    HARD_FILTER = "HARD_FILTER"
    SOFT_PREFERENCE = "SOFT_PREFERENCE"


class RecommendationConfidence(StrEnum):
    """Confidence in recommendation accuracy (independent from relevance score)."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ExplanationCategory(StrEnum):
    """Category of explainable factor insight."""

    WHY_MATCHES = "WHY_MATCHES"
    WHY_RELEVANT = "WHY_RELEVANT"
    WHAT_TO_VERIFY = "WHAT_TO_VERIFY"
    DEADLINE_NOTE = "DEADLINE_NOTE"
    FUNDING_NOTE = "FUNDING_NOTE"
    PROFILE_GAP = "PROFILE_GAP"
    SOURCE_NOTE = "SOURCE_NOTE"
    WARNING_NOTE = "WARNING_NOTE"


class UserPreference(BaseModel):
    """Structured preference constraint or preference from profile/query."""

    category: str = Field(description="e.g. FUNDING, LOCATION, DEGREE_LEVEL, CATEGORY, FEE")
    value: Any = Field(description="e.g. FULLY_FUNDED, ['Germany', 'UK'], 'MASTER'")
    priority: PreferencePriority = Field(
        default=PreferencePriority.HIGH, description="REQUIRED for hard filter, else soft boost"
    )
    source: str = Field(default="user_input", description="Provenance of preference")
    explicit: bool = Field(default=True, description="True if explicitly specified by user")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RankingFactorDetail(BaseModel):
    """Detailed score breakdown for a single ranking dimension."""

    factor_type: RankingFactorType
    score: float = Field(ge=0.0, le=1.0, description="Normalized factor score [0.0, 1.0]")
    weight: float = Field(default=1.0, ge=0.0)
    weighted_score: float = Field(default=0.0, ge=0.0)
    status: str = Field(default="HIGH", description="HIGH, MEDIUM, LOW, UNKNOWN, MISMATCH")
    reason: str = Field(default="")
    confidence: RecommendationConfidence = Field(default=RecommendationConfidence.HIGH)


class StructuredRankingExplanation(BaseModel):
    """Transparent bullet-point explanation explaining rank position."""

    category: ExplanationCategory
    text: str
    evidence_reference: str | None = None


class RankedOpportunity(BaseModel):
    """Individually scored and ranked opportunity candidate."""

    opportunity_id: str
    canonical_key: str | None = None
    title: str = ""
    organization: str = ""
    rank: int = 1
    relevance_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Fit and relevance score (NEVER an admission or selection probability)",
    )
    eligibility_status: OverallEligibilityStatus
    fit_summary: str = ""
    ranking_factors: dict[str, RankingFactorDetail] = Field(default_factory=dict)
    positive_factors: list[str] = Field(default_factory=list)
    negative_factors: list[str] = Field(default_factory=list)
    unknown_factors: list[str] = Field(default_factory=list)
    confidence: RecommendationConfidence = RecommendationConfidence.MEDIUM
    freshness: float = Field(default=1.0, ge=0.0, le=1.0)
    explanations: list[StructuredRankingExplanation] = Field(default_factory=list)
    deadline: str | None = None
    funding_type: str | None = None
    host_country: str | None = None
    opportunity: Any | None = None


class OpportunityRankingContext(BaseModel):
    """Unified context passed into the PersonalizedRankingEngine."""

    normalized_profile: NormalizedAIProfile | None = None
    user_facts: UnifiedUserFacts | None = None
    preferences: list[UserPreference] = Field(default_factory=list)
    search_intent: SearchIntent | None = None
    opportunities: list[Any] = Field(default_factory=list)
    eligibility_results: dict[str, EligibilityResult] = Field(default_factory=dict)
    sort_mode: SortMode = SortMode.RELEVANCE
    include_ineligible: bool = False
    session_id: str | None = None


class RankedOpportunityResult(BaseModel):
    """Complete ranked set and provenance metadata."""

    opportunities: list[RankedOpportunity] = Field(default_factory=list)
    total_evaluated: int = 0
    filtered_out_count: int = 0
    sort_mode: SortMode = SortMode.RELEVANCE
    engine_version: str = "1.0.0"
    config_version: str = "1.0.0"
    cache_key: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
