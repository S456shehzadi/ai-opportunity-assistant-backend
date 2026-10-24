"""Pydantic schemas for structured, source-grounded opportunity extraction."""

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.opportunities.extraction.evidence import Evidence


class FieldStatus(StrEnum):
    """Provenance and extraction certainty status for individual attributes."""

    FOUND = "FOUND"
    NOT_FOUND = "NOT_FOUND"
    UNCLEAR = "UNCLEAR"
    INFERRED = "INFERRED"
    CONFLICTING = "CONFLICTING"


class ExtractedField[T](BaseModel):
    """Generic attribute container preserving source grounding, certainty, and evidence."""

    value: T | None = Field(default=None, description="Extracted attribute value")
    status: FieldStatus = Field(
        default=FieldStatus.NOT_FOUND, description="Extraction certainty state"
    )
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Attribute confidence score")
    evidence: Evidence | None = Field(
        default=None, description="Grounding citation supporting this value"
    )
    normalized_value: Any | None = Field(
        default=None, description="Standardized canonical equivalent if transformed"
    )

    @classmethod
    def found(
        cls,
        value: T,
        evidence: Evidence | None = None,
        confidence: float = 1.0,
        normalized_value: Any | None = None,
    ) -> "ExtractedField[T]":
        return cls(
            value=value,
            status=FieldStatus.FOUND,
            confidence=confidence,
            evidence=evidence,
            normalized_value=normalized_value or value,
        )

    @classmethod
    def not_found(cls, confidence: float = 0.0) -> "ExtractedField[T]":
        return cls(value=None, status=FieldStatus.NOT_FOUND, confidence=confidence, evidence=None)

    @classmethod
    def inferred(
        cls,
        value: T,
        evidence: Evidence,
        confidence: float = 0.7,
        normalized_value: Any | None = None,
    ) -> "ExtractedField[T]":
        return cls(
            value=value,
            status=FieldStatus.INFERRED,
            confidence=confidence,
            evidence=evidence,
            normalized_value=normalized_value or value,
        )

    @classmethod
    def conflicting(
        cls,
        value: T | None,
        evidence: Evidence | None = None,
        confidence: float = 0.5,
    ) -> "ExtractedField[T]":
        return cls(
            value=value,
            status=FieldStatus.CONFLICTING,
            confidence=confidence,
            evidence=evidence,
        )


class OpportunityCategory(StrEnum):
    """Core categories of global opportunity programs."""

    SCHOLARSHIP = "SCHOLARSHIP"
    GRANT = "GRANT"
    FELLOWSHIP = "FELLOWSHIP"
    INTERNSHIP = "INTERNSHIP"
    RESEARCH_FUNDING = "RESEARCH_FUNDING"
    RESEARCH_OPPORTUNITY = "RESEARCH_OPPORTUNITY"
    EXCHANGE_PROGRAM = "EXCHANGE_PROGRAM"
    COMPETITION = "COMPETITION"
    CONFERENCE = "CONFERENCE"
    STARTUP_FUNDING = "STARTUP_FUNDING"
    GOVERNMENT_PROGRAM = "GOVERNMENT_PROGRAM"
    VOLUNTEER_PROGRAM = "VOLUNTEER_PROGRAM"
    TRAINING_PROGRAM = "TRAINING_PROGRAM"
    OTHER = "OTHER"


class OpportunityStatus(StrEnum):
    """Operational lifecycle state of an opportunity."""

    OPEN = "OPEN"
    UPCOMING = "UPCOMING"
    CLOSED = "CLOSED"
    ONGOING = "ONGOING"
    ROLLING = "ROLLING"
    UNKNOWN = "UNKNOWN"


class DeadlineType(StrEnum):
    """Semantic meaning of extracted temporal milestones."""

    APPLICATION_DEADLINE = "APPLICATION_DEADLINE"
    NOMINATION_DEADLINE = "NOMINATION_DEADLINE"
    DOCUMENT_DEADLINE = "DOCUMENT_DEADLINE"
    INTERVIEW_DATE = "INTERVIEW_DATE"
    PROGRAM_START = "PROGRAM_START"
    PROGRAM_END = "PROGRAM_END"
    OPENING_DATE = "OPENING_DATE"
    ANNOUNCEMENT_DATE = "ANNOUNCEMENT_DATE"
    UNKNOWN_DATE = "UNKNOWN_DATE"
    ROLLING = "ROLLING"


class FundingPeriod(StrEnum):
    """Disbursement frequency or total cap of financial support."""

    MONTHLY = "MONTHLY"
    ANNUAL = "ANNUAL"
    TOTAL = "TOTAL"
    PER_TERM = "PER_TERM"
    PER_PROJECT = "PER_PROJECT"
    MAXIMUM = "MAXIMUM"
    MINIMUM = "MINIMUM"
    UNKNOWN = "UNKNOWN"


class ApplicationMethod(StrEnum):
    """Submission mechanism for applicants."""

    ONLINE_PORTAL = "ONLINE_PORTAL"
    EMAIL = "EMAIL"
    UNIVERSITY_PORTAL = "UNIVERSITY_PORTAL"
    EXTERNAL_PORTAL = "EXTERNAL_PORTAL"
    NOMINATION = "NOMINATION"
    INVITATION = "INVITATION"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class SourceTrustType(StrEnum):
    """Authoritative credibility categorization of the origin host."""

    OFFICIAL = "OFFICIAL"
    SECONDARY = "SECONDARY"
    DIRECTORY = "DIRECTORY"
    NEWS = "NEWS"
    BLOG = "BLOG"
    UNKNOWN = "UNKNOWN"


class StructuredFundingAmount(BaseModel):
    """Granular financial benefits preserving currency and frequency."""

    amount: float | None = Field(default=None, description="Numeric magnitude")
    currency: str | None = Field(default=None, description="ISO-4217 currency code (e.g. EUR, USD)")
    period: FundingPeriod = Field(
        default=FundingPeriod.UNKNOWN, description="Disbursement frequency"
    )
    amount_type: str | None = Field(
        default=None, description="'EXACT', 'MAXIMUM', 'ESTIMATED', or 'MINIMUM'"
    )


class ExtractedDeadline(BaseModel):
    """Structured date milestone with explicit semantics and citation."""

    deadline_date: str | None = Field(default=None, description="Normalized ISO date (YYYY-MM-DD)")
    deadline_type: DeadlineType = Field(
        default=DeadlineType.APPLICATION_DEADLINE, description="Semantic milestone category"
    )
    is_rolling: bool = Field(
        default=False, description="True if applications accepted on rolling basis"
    )
    raw_text: str = Field(description="Literal date snippet from source")
    evidence: Evidence = Field(description="Evidence citation for this deadline")


class ExtractedLanguageRequirement(BaseModel):
    """Preserved standardized test or language competency condition."""

    language: str = Field(default="English", description="Target language")
    test_name: str | None = Field(default=None, description="Test name (e.g. IELTS, TOEFL, GRE)")
    minimum_score: str | None = Field(default=None, description="Exact minimum score or grade")
    is_required: bool = Field(default=True, description="False if explicitly optional or exempt")
    waiver_allowed: bool = Field(
        default=False, description="True if English medium of instruction allows waiver"
    )
    waiver_conditions: str | None = Field(default=None, description="Verbatim waiver rules")
    evidence: Evidence = Field(description="Evidence citation for language requirement")


class ExtractedAcademicRequirement(BaseModel):
    """Academic prerequisite preserving degree criteria and thresholds."""

    degree_level: str | None = Field(
        default=None, description="Required degree (e.g. Bachelor's, Master's, PhD)"
    )
    minimum_cgpa: float | None = Field(default=None, description="Minimum CGPA/GPA threshold")
    minimum_percentage: float | None = Field(default=None, description="Minimum percentage cutoff")
    degree_subject: str | None = Field(default=None, description="Required academic discipline")
    raw_text: str = Field(description="Verbatim requirement text from source")
    evidence: Evidence = Field(description="Evidence citation for academic prerequisite")


class ExtractedOpportunity(BaseModel):
    """High-fidelity, source-grounded opportunity record extracted from web documents."""

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4, description="Unique opportunity extraction identifier"
    )
    canonical_key: str = Field(
        description="Deterministic identity key (org + program + category + canonical_url)"
    )
    title: str = Field(description="Official title of the opportunity")
    short_description: str | None = Field(
        default=None, description="Concise synopsis extracted from lead text"
    )
    description: str = Field(default="", description="Sanitized main body description")

    # Organization
    organization: str = Field(description="Hosting entity or university name")
    organization_type: str | None = Field(
        default=None, description="University, Research Institute, Foundation, Government"
    )
    organization_country: str | None = Field(
        default=None, description="Origin country of organization"
    )
    organization_website: str | None = Field(
        default=None, description="Official organization root URL"
    )

    # Category
    category: OpportunityCategory = Field(
        default=OpportunityCategory.SCHOLARSHIP, description="Primary classification"
    )
    subcategory: str | None = Field(
        default=None, description="Specific subcategory (e.g. Fully Funded Scholarship)"
    )

    program_name: str | None = Field(
        default=None, description="Name of degree or fellowship program"
    )
    program_type: str | None = Field(default=None, description="Degree type or track")

    # Geography & Eligibility
    locations: list[str] = Field(default_factory=list, description="Host cities or campuses")
    countries: list[str] = Field(default_factory=list, description="Host destination countries")
    host_country: ExtractedField[str] = Field(
        default_factory=ExtractedField.not_found, description="Host destination country"
    )
    eligible_countries: list[str] = Field(
        default_factory=list, description="Explicitly allowed destination or nationality countries"
    )
    eligible_nationalities: ExtractedField[list[str]] = Field(
        default_factory=ExtractedField.not_found,
        description="Permitted applicant citizenship / nationality",
    )

    # Education & Discipline
    degree_levels: list[str] = Field(
        default_factory=list, description="Target degrees (Bachelor, Master, PhD, Postdoc)"
    )
    fields_of_study: list[str] = Field(
        default_factory=list, description="Target academic fields and disciplines"
    )

    # Funding & Benefits
    funding_type: str = Field(
        default="Unknown", description="Fully Funded, Partially Funded, Tuition Waiver, Unpaid"
    )
    funding_amount: StructuredFundingAmount | None = Field(
        default=None, description="Structured financial magnitude and frequency"
    )
    funding_currency: str | None = Field(default=None, description="Currency code (e.g. EUR, USD)")
    tuition_coverage: ExtractedField[str] = Field(
        default_factory=ExtractedField.not_found, description="Full, Partial, or None"
    )
    stipend: ExtractedField[StructuredFundingAmount] = Field(
        default_factory=ExtractedField.not_found, description="Living allowance disbursement"
    )
    travel_support: ExtractedField[bool] = Field(
        default_factory=ExtractedField.not_found, description="Travel grant or flight allowance"
    )
    accommodation_support: ExtractedField[bool] = Field(
        default_factory=ExtractedField.not_found, description="Housing or dormitory coverage"
    )
    insurance_support: ExtractedField[bool] = Field(
        default_factory=ExtractedField.not_found, description="Health insurance provision"
    )
    other_benefits: list[str] = Field(default_factory=list, description="Auxiliary allowances")

    # Dates & Timelines
    opening_date: ExtractedField[str] = Field(
        default_factory=ExtractedField.not_found, description="Application launch date"
    )
    deadline: ExtractedField[str] = Field(
        default_factory=ExtractedField.not_found, description="Primary application deadline"
    )
    is_rolling: ExtractedField[bool] = Field(
        default_factory=lambda: ExtractedField[bool].found(False),
        description="True if rolling admissions",
    )
    deadlines: list[ExtractedDeadline] = Field(
        default_factory=list,
        description="All milestones preserving multiple rounds or rolling dates",
    )
    duration: ExtractedField[str] = Field(
        default_factory=ExtractedField.not_found,
        description="Program length (e.g. 2 years, 10 weeks)",
    )
    start_date: ExtractedField[str] = Field(
        default_factory=ExtractedField.not_found, description="Expected program intake date"
    )

    # Academic & Profile Prerequisites
    academic_requirements: list[ExtractedAcademicRequirement] = Field(
        default_factory=list, description="Detailed prerequisite academic requirements"
    )
    minimum_cgpa: ExtractedField[float] = Field(
        default_factory=ExtractedField.not_found, description="Grade point threshold"
    )
    minimum_percentage: ExtractedField[float] = Field(
        default_factory=ExtractedField.not_found, description="Percentage cutoff"
    )
    minimum_gpa: ExtractedField[float] = Field(
        default_factory=ExtractedField.not_found, description="Normalized 4.0 GPA equivalent"
    )
    degree_requirement: ExtractedField[str] = Field(
        default_factory=ExtractedField.not_found, description="Required degree credential"
    )
    age_requirement: ExtractedField[str] = Field(
        default_factory=ExtractedField.not_found, description="Age limitations"
    )
    work_experience_requirement: ExtractedField[str] = Field(
        default_factory=ExtractedField.not_found, description="Professional experience requirements"
    )
    research_experience_requirement: ExtractedField[str] = Field(
        default_factory=ExtractedField.not_found, description="Academic research prerequisites"
    )
    publication_requirement: ExtractedField[str] = Field(
        default_factory=ExtractedField.not_found, description="Peer-reviewed publication conditions"
    )
    required_documents: list[str] = Field(
        default_factory=list, description="Required application materials list"
    )

    # Language & Testing
    language_requirements: list[ExtractedLanguageRequirement] = Field(
        default_factory=list, description="Language competencies and test scores"
    )
    english_requirement: ExtractedField[str] = Field(
        default_factory=ExtractedField.not_found, description="English competency overview"
    )
    english_tests: list[str] = Field(
        default_factory=list, description="Accepted test abbreviations (e.g. IELTS, TOEFL, PTE)"
    )
    minimum_ielts: ExtractedField[str] = Field(
        default_factory=ExtractedField.not_found, description="Specific IELTS score with evidence"
    )
    minimum_toefl: ExtractedField[str] = Field(
        default_factory=ExtractedField.not_found, description="Specific TOEFL score with evidence"
    )
    other_language_tests: list[str] = Field(default_factory=list)

    # Application Details
    application_fee: ExtractedField[bool] = Field(
        default_factory=ExtractedField.not_found,
        description="True if fee is required, False if free",
    )
    application_fee_amount: float | None = Field(default=None)
    application_fee_currency: str | None = Field(default=None)
    application_method: ApplicationMethod = Field(default=ApplicationMethod.UNKNOWN)
    application_url: str | None = Field(
        default=None, description="Direct application submission URL"
    )
    official_source_url: str = Field(description="Primary verified authoritative webpage URL")
    contact_information: dict[str, str] = Field(
        default_factory=dict, description="Inquiry emails, phones, helpdesk links"
    )

    status: OpportunityStatus = Field(default=OpportunityStatus.UNKNOWN)
    last_verified_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp of source retrieval and verification",
    )
    source_documents: list[str] = Field(
        default_factory=list, description="Originating WebDocument identifiers or URLs"
    )

    # Separate Quality & Trust Dimensions
    source_type: SourceTrustType = Field(default=SourceTrustType.UNKNOWN)
    source_trust_score: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Inherent domain authority"
    )
    confidence: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Extraction certainty of facts"
    )

    all_evidence: list[Evidence] = Field(
        default_factory=list, description="Complete citation index for all extracted facts"
    )
    conflicts_detected: list[str] = Field(
        default_factory=list, description="Contradictory information between sources"
    )
    notes: list[str] = Field(default_factory=list, description="Audit notes and conflict logs")

    @property
    def application_deadline(self) -> ExtractedField[str]:
        return self.deadline

    @application_deadline.setter
    def application_deadline(self, val: ExtractedField[str]) -> None:
        self.deadline = val

    @property
    def extraction_confidence(self) -> float:
        return self.confidence

    @extraction_confidence.setter
    def extraction_confidence(self, val: float) -> None:
        self.confidence = val

    @property
    def source_trust_type(self) -> SourceTrustType:
        return self.source_type

    @source_trust_type.setter
    def source_trust_type(self, val: SourceTrustType) -> None:
        self.source_type = val

    @property
    def language_requirement(self) -> ExtractedField[str]:
        return self.english_requirement

    @language_requirement.setter
    def language_requirement(self, val: ExtractedField[str]) -> None:
        self.english_requirement = val

    @property
    def is_application_free(self) -> ExtractedField[bool]:
        if self.application_fee.status == FieldStatus.FOUND:
            return ExtractedField[bool].found(
                value=not bool(self.application_fee.value),
                evidence=self.application_fee.evidence,
                confidence=self.application_fee.confidence,
            )
        return ExtractedField[bool].not_found()

    @property
    def benefits(self) -> list[str]:
        return self.other_benefits

    @benefits.setter
    def benefits(self, val: list[str]) -> None:
        self.other_benefits = val

    @property
    def eligible_fields_of_study(self) -> list[str]:
        return self.fields_of_study

    @eligible_fields_of_study.setter
    def eligible_fields_of_study(self, val: list[str]) -> None:
        self.fields_of_study = val
