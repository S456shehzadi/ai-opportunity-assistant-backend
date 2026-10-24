from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class OpportunityCategory(StrEnum):
    SCHOLARSHIP = "scholarship"
    GRANT = "grant"
    INTERNSHIP = "internship"
    FELLOWSHIP = "fellowship"
    EXCHANGE_PROGRAM = "exchange_program"
    RESEARCH = "research"
    COMPETITION = "competition"
    CONFERENCE = "conference"
    STARTUP_FUNDING = "startup_funding"
    GOVERNMENT_PROGRAM = "government_program"
    OTHER = "other"


class FundingType(StrEnum):
    FULLY_FUNDED = "fully_funded"
    PARTIALLY_FUNDED = "partially_funded"
    PAID = "paid"
    UNPAID = "unpaid"
    TUITION_WAIVER = "tuition_waiver"
    STIPEND = "stipend"
    UNKNOWN = "unknown"


class OpportunityStatus(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    UPCOMING = "upcoming"
    UNDER_REVIEW = "under_review"


class EligibilityCriteria(BaseModel):
    """Structured criteria defining applicant eligibility."""

    degree_levels: list[str] = Field(
        default_factory=list,
        description="Target degrees: High School, Bachelor, Master, PhD, Postdoc",
    )
    fields_of_study: list[str] = Field(default_factory=list)
    eligible_nationalities: list[str] = Field(
        default_factory=list,
        description="Eligible nationalities (e.g. ['Pakistan', 'Global'])",
    )
    min_gpa: float | None = None
    max_age: int | None = None
    language_requirements: list[str] = Field(default_factory=list)
    test_requirements: list[str] = Field(default_factory=list)
    experience_requirements: list[str] = Field(default_factory=list)
    gender_preference: str | None = None
    custom_rules: list[str] = Field(default_factory=list)


class OpportunityBase(BaseModel):
    """Core domain model representing a global opportunity."""

    title: str = Field(min_length=3, max_length=300)
    organization: str = Field(min_length=2, max_length=200)
    description: str = Field(max_length=10000)
    category: OpportunityCategory = OpportunityCategory.SCHOLARSHIP
    host_country: str = Field(default="Global")
    countries_allowed: list[str] = Field(default_factory=lambda: ["Global"])

    opening_date: date | None = None
    deadline: date | None = None

    funding_type: FundingType = FundingType.UNKNOWN
    funding_amount: str | None = None

    eligibility: EligibilityCriteria = Field(default_factory=EligibilityCriteria)

    application_url: str | None = None
    official_source_url: str
    source_domain: str

    last_verified: datetime = Field(default_factory=lambda: datetime.now(UTC))
    status: OpportunityStatus = OpportunityStatus.ACTIVE


class OpportunityCreate(OpportunityBase):
    pass


class OpportunityRead(OpportunityBase):
    id: str
    created_at: datetime
    updated_at: datetime
    trust_score: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
