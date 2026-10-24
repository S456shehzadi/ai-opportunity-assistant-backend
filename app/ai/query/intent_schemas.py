from datetime import date
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class UserIntentType(StrEnum):
    DISCOVER_OPPORTUNITIES = "discover_opportunities"
    CHECK_ELIGIBILITY = "check_eligibility"
    EXPLAIN_OPPORTUNITY = "explain_opportunity"
    COMPARE_OPPORTUNITIES = "compare_opportunities"
    FIND_DEADLINES = "find_deadlines"
    FIND_FUNDING = "find_funding"
    FIND_INTERNSHIPS = "find_internships"
    FIND_SCHOLARSHIPS = "find_scholarships"
    FIND_RESEARCH_OPPORTUNITIES = "find_research_opportunities"
    GENERAL_INFORMATION = "general_information"


class FundingConstraintType(StrEnum):
    FULLY_FUNDED = "fully_funded"
    PARTIAL = "partial"
    TUITION_WAIVER = "tuition_waiver"
    STIPEND = "stipend"
    TRAVEL_ALLOWANCE = "travel_allowance"
    NO_APPLICATION_FEE = "no_application_fee"
    ANY_FUNDED = "any_funded"
    UNKNOWN = "unknown"


class FundingConstraint(BaseModel):
    constraint_type: FundingConstraintType
    raw_mention: str
    is_fully_funded: bool = False
    details: str | None = None


class TestRequirementType(StrEnum):
    NOT_REQUIRED = "not_required"  # "without IELTS", "no IELTS", "no GRE"
    REQUIRED = "required"  # "GRE required", "IELTS mandatory"
    ACCEPTED = "accepted"  # "TOEFL accepted", "Duolingo accepted"
    WAIVED = "waived"  # "English test waiver available"


class LanguageTestConstraint(BaseModel):
    test_name: str  # e.g., "IELTS", "TOEFL", "GRE", "English Proficiency"
    requirement_type: TestRequirementType
    raw_mention: str
    verification_required: bool = (
        True  # Strict rule: Search constraint; must verify later with sources
    )


class TemporalConstraintType(StrEnum):
    THIS_MONTH = "this_month"
    NEXT_MONTH = "next_month"
    BEFORE_DATE = "before_date"
    CURRENTLY_OPEN = "currently_open"
    CLOSING_SOON = "closing_soon"
    WITHIN_DAYS = "within_days"


class TemporalConstraint(BaseModel):
    constraint_type: TemporalConstraintType
    raw_mention: str
    window_start: date | None = None
    window_end: date | None = None
    days_window: int | None = None


class SearchIntent(BaseModel):
    """Structured interpretation of natural language user query.

    Separates explicit constraints from implicit context and unknowns.
    """

    original_query: str
    intent_type: UserIntentType = UserIntentType.DISCOVER_OPPORTUNITIES
    is_search_intent: bool = True  # False for informational queries like "What is Erasmus Mundus?"

    # Extracted entity constraints
    opportunity_categories: list[str] = Field(default_factory=list)
    countries: list[str] = Field(default_factory=list)
    regions: list[str] = Field(default_factory=list)
    fields: list[str] = Field(default_factory=list)
    degree_levels: list[str] = Field(default_factory=list)
    funding_constraints: list[FundingConstraint] = Field(default_factory=list)
    language_test_constraints: list[LanguageTestConstraint] = Field(default_factory=list)
    experience_constraints: list[str] = Field(default_factory=list)
    nationality_constraints: list[str] = Field(
        default_factory=list
    )  # e.g. "international students", "women founders"
    deadline_constraints: list[TemporalConstraint] = Field(default_factory=list)
    remote_preference: bool | None = None

    # Freeform keywords not mapped to structured constraints
    keywords: list[str] = Field(default_factory=list)

    # Constraint provenance
    explicit_constraints: dict[str, Any] = Field(default_factory=dict)
    implicit_context: dict[str, Any] = Field(default_factory=dict)
    unknown_constraints: list[str] = Field(default_factory=list)

    confidence: float = 1.0
