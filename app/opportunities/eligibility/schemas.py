"""Schemas and domain models for AI Eligibility Matching & Personalized Intelligence."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RequirementStatus(StrEnum):
    """Controlled vocabulary for atomic requirement satisfaction."""

    MATCH = "MATCH"
    NO_MATCH = "NO_MATCH"
    UNKNOWN = "UNKNOWN"
    CONDITIONAL = "CONDITIONAL"
    CONFLICTING = "CONFLICTING"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class OverallEligibilityStatus(StrEnum):
    """Holistic conclusion regarding user eligibility against an opportunity."""

    CLEARLY_ELIGIBLE = "CLEARLY_ELIGIBLE"
    CLEARLY_NOT_ELIGIBLE = "CLEARLY_NOT_ELIGIBLE"
    POTENTIALLY_ELIGIBLE = "POTENTIALLY_ELIGIBLE"
    NEEDS_VERIFICATION = "NEEDS_VERIFICATION"
    CONFLICTING_INFORMATION = "CONFLICTING_INFORMATION"


class RequirementPriority(StrEnum):
    """Severity weighting of an opportunity requirement."""

    MANDATORY = "MANDATORY"
    IMPORTANT = "IMPORTANT"
    INFORMATIONAL = "INFORMATIONAL"


class EligibilityConfidence(StrEnum):
    """Field-level and overall decision confidence (independent from admission probability)."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ExplanationType(StrEnum):
    """Standardized semantic explanation categories for transparent decision-making."""

    MATCH_REASON = "MATCH_REASON"
    NO_MATCH_REASON = "NO_MATCH_REASON"
    UNKNOWN_REASON = "UNKNOWN_REASON"
    CONDITIONAL_REASON = "CONDITIONAL_REASON"
    CONFLICT_REASON = "CONFLICT_REASON"
    MISSING_INFORMATION = "MISSING_INFORMATION"
    SOURCE_NOTE = "SOURCE_NOTE"


class UserEvidenceRecord(BaseModel):
    """Auditable citation pointing to specific declared facts in the user's profile."""

    model_config = ConfigDict(frozen=True)

    source_section: str = Field(description="Profile section (e.g. education, test, nationality)")
    record_id: str | None = Field(default=None, description="UUID or ID of the profile sub-record")
    field_name: str = Field(description="Normalized field evaluated")
    value: Any = Field(description="Value declared by user")
    verified: bool = Field(
        default=False, description="True if verified via document or institution"
    )
    context: str | None = Field(default=None, description="Contextual excerpt or degree name")


class OpportunityEvidenceRecord(BaseModel):
    """Auditable citation pointing to verified claims in the opportunity source."""

    model_config = ConfigDict(frozen=True)

    source_url: str = Field(description="Official URL originating the requirement")
    field_name: str = Field(description="Opportunity attribute key")
    evidence_text: str = Field(description="Verbatim excerpt from document")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class StructuredExplanation(BaseModel):
    """Standardized, machine-readable explanation component."""

    explanation_type: ExplanationType
    message: str = Field(description="Concise, human-readable summary")
    details: dict[str, Any] = Field(default_factory=dict, description="Structured attributes")


class RequirementEvaluation(BaseModel):
    """Field-level eligibility evaluation preserving full evidence provenance."""

    requirement_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    requirement_type: str = Field(
        description="Category (e.g. cgpa, percentage, degree_level, nationality, test, experience)"
    )
    requirement_description: str = Field(description="Human-readable rule definition")
    status: RequirementStatus
    priority: RequirementPriority = Field(default=RequirementPriority.MANDATORY)

    user_value: Any = Field(default=None, description="Extracted user fact")
    required_value: Any = Field(default=None, description="Opportunity constraint benchmark")
    comparison: str | None = Field(
        default=None, description="Literal evaluation formula (e.g. '3.67 >= 3.00')"
    )

    user_evidence: UserEvidenceRecord | None = None
    opportunity_evidence: OpportunityEvidenceRecord | None = None

    explanation: str = Field(description="Concise plain-text rationale")
    structured_explanation: StructuredExplanation | None = None

    confidence: EligibilityConfidence = Field(default=EligibilityConfidence.HIGH)
    requires_verification: bool = Field(
        default=False, description="True if ambiguity or conflict mandates user verification"
    )
    fact_grounding_tier: str = Field(
        default="VERIFIED_SOURCE_FACT",
        description="VERIFIED_SOURCE_FACT, UNCONFIRMED_CLAIM, CONFLICTING_FACT, or MISSING_DATA",
    )


class PersonalizedIntelligenceSummary(BaseModel):
    """Structured insights for user decision-making without predicting selection probability."""

    satisfied_requirements: list[str] = Field(default_factory=list)
    unsatisfied_requirements: list[str] = Field(default_factory=list)
    unknown_requirements: list[str] = Field(default_factory=list)
    conditional_requirements: list[str] = Field(default_factory=list)
    potential_issues: list[str] = Field(
        default_factory=list, description="Approaching deadlines, fee requirements, etc."
    )
    missing_profile_fields: list[str] = Field(
        default_factory=list, description="All missing profile items"
    )
    prioritized_missing_information: list[str] = Field(
        default_factory=list,
        description="Ordered missing fields that would directly resolve UNKNOWN requirements",
    )


class EligibilityResult(BaseModel):
    """Complete, evidence-driven, explainable eligibility evaluation payload."""

    opportunity_id: str = Field(description="Opportunity identifier or canonical key")
    user_id: str = Field(description="User identifier")
    overall_status: OverallEligibilityStatus
    match_percentage: float = Field(
        ge=0.0,
        le=100.0,
        description="Internal requirement fulfillment metric (never an admission probability)",
    )

    requirements: list[RequirementEvaluation] = Field(default_factory=list)
    blocking_requirements: list[RequirementEvaluation] = Field(
        default_factory=list,
        description="Mandatory requirements with status NO_MATCH that cause overall failure",
    )
    unknown_requirements: list[RequirementEvaluation] = Field(default_factory=list)
    conditional_requirements: list[RequirementEvaluation] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)

    explanation: str = Field(description="Concise overall synthesis")
    personalized_intelligence: PersonalizedIntelligenceSummary
    admission_guarantee_disclaimer: str = Field(
        default=(
            "Eligibility evaluations evaluate criteria alignment against extracted official data. "
            "They do not constitute an admission prediction or scholarship funding guarantee. "
            "Final selection decisions rest solely with the issuing institution."
        ),
        description="Explicit notice preventing misinterpretation as admission prediction",
    )

    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    engine_version: str = "1.0.0"
    profile_version: int = 1
    opportunity_version: int = 1
    cache_key: str | None = None
