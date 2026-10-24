"""Schemas and domain models for the Grounded AI Opportunity Assistant."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.ai.query.intent_schemas import SearchIntent
from app.opportunities.eligibility.schemas import OverallEligibilityStatus


class AssistantIntentType(StrEnum):
    """Structured categories of user conversational requests."""

    SEARCH_OPPORTUNITIES = "SEARCH_OPPORTUNITIES"
    REFINE_SEARCH = "REFINE_SEARCH"
    EXPLAIN_OPPORTUNITY = "EXPLAIN_OPPORTUNITY"
    CHECK_ELIGIBILITY = "CHECK_ELIGIBILITY"
    COMPARE_OPPORTUNITIES = "COMPARE_OPPORTUNITIES"
    FIND_SIMILAR = "FIND_SIMILAR"
    CHECK_DEADLINE = "CHECK_DEADLINE"
    CHECK_REQUIREMENT = "CHECK_REQUIREMENT"
    CHECK_FUNDING = "CHECK_FUNDING"
    CHECK_APPLICATION = "CHECK_APPLICATION"
    PROFILE_GAP = "PROFILE_GAP"
    UPDATE_PREFERENCES = "UPDATE_PREFERENCES"
    SHOW_SAVED = "SHOW_SAVED"
    GENERAL_OPPORTUNITY_QUESTION = "GENERAL_OPPORTUNITY_QUESTION"
    CLARIFICATION_REQUIRED = "CLARIFICATION_REQUIRED"
    UNKNOWN = "UNKNOWN"


class AssistantResponseType(StrEnum):
    """Controlled vocabulary for assistant message payloads."""

    TEXT = "TEXT"
    OPPORTUNITY_LIST = "OPPORTUNITY_LIST"
    OPPORTUNITY_DETAIL = "OPPORTUNITY_DETAIL"
    COMPARISON = "COMPARISON"
    ELIGIBILITY_EXPLANATION = "ELIGIBILITY_EXPLANATION"
    CLARIFICATION = "CLARIFICATION"
    ERROR = "ERROR"


class ClaimType(StrEnum):
    """Specific factual attribute classification for claim-level grounding."""

    TITLE = "TITLE"
    ORGANIZATION = "ORGANIZATION"
    DEADLINE = "DEADLINE"
    FUNDING = "FUNDING"
    ELIGIBILITY = "ELIGIBILITY"
    REQUIREMENT = "REQUIREMENT"
    LOCATION = "LOCATION"
    APPLICATION = "APPLICATION"
    STATUS = "STATUS"
    PROFILE_MATCH = "PROFILE_MATCH"
    COMPARISON = "COMPARISON"


class ToolPermission(StrEnum):
    """Explicit authorized operations for the assistant planner."""

    SEARCH = "SEARCH"
    RETRIEVE = "RETRIEVE"
    EXTRACT = "EXTRACT"
    CHECK_ELIGIBILITY = "CHECK_ELIGIBILITY"
    RANK = "RANK"
    READ_PROFILE = "READ_PROFILE"
    READ_SAVED = "READ_SAVED"
    COMPARE = "COMPARE"


class AssistantIntent(BaseModel):
    """Structured interpretation of user message determining downstream planner actions."""

    intent_type: AssistantIntentType
    search_intent: SearchIntent | None = None
    opportunity_ids: list[str] = Field(default_factory=list)
    requested_fields: list[str] = Field(default_factory=list)
    filters: dict[str, Any] = Field(default_factory=dict)
    comparison_fields: list[str] = Field(default_factory=list)
    requires_live_search: bool = False
    requires_profile: bool = False
    requires_eligibility: bool = False
    requires_ranking: bool = False
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    raw_query: str = ""


class OpportunitySummary(BaseModel):
    """UI-ready lightweight opportunity representation for conversational cards."""

    id: str
    title: str
    organization: str
    category: str
    location: str
    funding_summary: str
    deadline: str | None = None
    eligibility_status: OverallEligibilityStatus | str = "POTENTIALLY_ELIGIBLE"
    relevance_summary: str = ""
    verification_status: str = "VERIFIED"
    official_url: str | None = None
    source: str = ""


class CitationItem(BaseModel):
    """Specific grounding evidence citation supporting an assistant claim."""

    citation_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str
    url: str
    source_type: str = "OFFICIAL_PORTAL"  # OFFICIAL_PORTAL, UNIVERSITY, SECONDARY, DIRECTORY
    source_domain: str = ""
    trust_tier: str = "HIGH"
    claim_types: list[ClaimType] = Field(default_factory=list)
    exact_snippet: str | None = None


class ComparisonResult(BaseModel):
    """Structured side-by-side comparison of multiple opportunity candidates."""

    opportunity_ids: list[str]
    opportunity_titles: list[str]
    comparison_fields: list[str]
    table_rows: list[dict[str, Any]] = Field(default_factory=list)
    differences: list[str] = Field(default_factory=list)
    similarities: list[str] = Field(default_factory=list)
    sources: list[CitationItem] = Field(default_factory=list)


class OpportunitySearchPage(BaseModel):
    """Paginated collection of opportunity candidates."""

    items: list[OpportunitySummary] = Field(default_factory=list)
    page: int = 1
    page_size: int = 5
    total: int = 0
    has_more: bool = False
    next_cursor: str | None = None


class ResponseClaim(BaseModel):
    """Individual assertion verified by the grounding validator."""

    claim_text: str
    claim_type: ClaimType
    source_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: float = 1.0
    supported: bool = True
    rejection_reason: str | None = None


class AssistantResponse(BaseModel):
    """Structured, evidence-grounded response delivered to user or client."""

    conversation_id: str
    response_type: AssistantResponseType
    message: str
    opportunities: list[OpportunitySummary] = Field(default_factory=list)
    citations: list[CitationItem] = Field(default_factory=list)
    comparison: ComparisonResult | None = None
    search_page: OpportunitySearchPage | None = None
    follow_up_options: list[str] = Field(default_factory=list)
    clarification_prompt: str | None = None
    claims_verified: list[ResponseClaim] = Field(default_factory=list)
    prompt_version: str = "1.0"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ChatRequestPayload(BaseModel):
    """Client API payload for conversational opportunity interaction."""

    conversation_id: str | None = None
    message: str = Field(min_length=1, max_length=2000)
    user_id: uuid.UUID | None = None
    page: int = 1
    page_size: int = 5
    context_override: dict[str, Any] | None = None
