import uuid
from datetime import date
from typing import Any

from enum import StrEnum
from pydantic import BaseModel, Field


class TestStatus(StrEnum):
    VALID = "valid"
    EXPIRED = "expired"
    TAKEN = "taken"
    NOT_TAKEN = "not_taken"
    UNKNOWN = "unknown"


class IdentityContext(BaseModel):
    nationality: str | None = None
    nationality_country_code: str | None = None
    country_of_residence: str | None = None
    residence_country_code: str | None = None
    city: str | None = None
    is_known: bool = False


class EducationRecordItem(BaseModel):
    raw_degree: str | None = None
    normalized_degree_level: str = (
        "Other"  # Bachelor's, Master's, Doctorate, Postdoc, Associate, Other
    )
    raw_field: str | None = None
    normalized_field: str | None = None
    broad_discipline: str | None = None
    institution: str | None = None
    start_year: int | None = None
    end_year: int | None = None
    grade: str | None = None
    grading_scale: str | None = None
    is_current: bool | None = False


class AcademicPerformance(BaseModel):
    highest_degree_level: str | None = None
    normalized_gpa_4_scale: float | None = None
    raw_cgpa: float | None = None
    raw_percentage: float | None = None
    has_honors: bool = False
    academic_achievements: list[str] = Field(default_factory=list)


class NormalizedTestItem(BaseModel):
    raw_test_name: str
    canonical_test_name: str
    test_type: str  # Language, Aptitude, Academic
    score: str | None = None
    sub_scores: dict[str, Any] = Field(default_factory=dict)
    test_date: date | None = None
    expiry_date: date | None = None
    status: TestStatus = TestStatus.UNKNOWN  # VALID, EXPIRED, TAKEN, NOT_TAKEN, UNKNOWN


class NormalizedSkillItem(BaseModel):
    raw_skill: str
    normalized_name: str
    category: str
    proficiency: str | None = None
    years_of_experience: float | None = None


class WorkExperienceSummary(BaseModel):
    total_years: float = 0.0
    roles: list[str] = Field(default_factory=list)
    organizations: list[str] = Field(default_factory=list)
    current_role: str | None = None


class ResearchExperienceSummary(BaseModel):
    has_research_experience: bool = False
    research_areas: list[str] = Field(default_factory=list)
    lab_institutions: list[str] = Field(default_factory=list)


class PublicationSummary(BaseModel):
    publication_count: int = 0
    recent_venues: list[str] = Field(default_factory=list)
    doi_list: list[str] = Field(default_factory=list)


class ProjectSummary(BaseModel):
    project_count: int = 0
    technologies_used: list[str] = Field(default_factory=list)
    project_titles: list[str] = Field(default_factory=list)


class GeographicPreferences(BaseModel):
    preferred_countries: list[str] = Field(default_factory=list)
    preferred_country_codes: list[str] = Field(default_factory=list)
    preferred_regions: list[str] = Field(default_factory=list)


class OpportunityPreferences(BaseModel):
    preferred_categories: list[str] = Field(default_factory=list)
    preferred_fields: list[str] = Field(default_factory=list)
    study_levels: list[str] = Field(default_factory=list)


class FundingPreferences(BaseModel):
    funding_requirement: str | None = None  # e.g. "fully_funded", "partial", "any"
    requires_visa_sponsorship: bool | None = None


class InformationCompleteness(BaseModel):
    is_profile_complete: bool = False
    known_fields: list[str] = Field(default_factory=list)
    unknown_fields: list[str] = Field(default_factory=list)
    missing_critical_signals: list[str] = Field(default_factory=list)


class NormalizedAIProfile(BaseModel):
    """Compact, consistent, AI-ready representation of user profile for opportunity discovery."""

    user_id: uuid.UUID
    email: str

    identity_context: IdentityContext
    education: list[EducationRecordItem] = Field(default_factory=list)
    academic_performance: AcademicPerformance
    tests: dict[str, NormalizedTestItem] = Field(default_factory=dict)
    skills: list[NormalizedSkillItem] = Field(default_factory=list)
    languages: dict[str, str] = Field(default_factory=dict)  # language -> proficiency

    work_experience: WorkExperienceSummary
    research_experience: ResearchExperienceSummary
    publications: PublicationSummary
    projects: ProjectSummary

    geographic_preferences: GeographicPreferences
    opportunity_preferences: OpportunityPreferences
    funding_preferences: FundingPreferences

    completeness: InformationCompleteness

    # Fast-lookup signals for filtering
    matching_signals: dict[str, Any] = Field(default_factory=dict)
