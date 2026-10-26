import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.profile import (
    EducationLevel,
    LanguageProficiency,
    SkillProficiency,
    TestType,
)


class UserProfileBase(BaseModel):
    nationality: str | None = Field(default=None, max_length=100)
    country_of_residence: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    date_of_birth: date | None = None

    education_level: EducationLevel | None = None
    current_education_level: EducationLevel | None = None
    education_status: str | None = Field(default=None, max_length=50)
    degree_title: str | None = Field(default=None, max_length=200)
    field_of_study: str | None = Field(default=None, max_length=200)
    university: str | None = Field(default=None, max_length=255)
    graduation_year: int | None = Field(default=None, ge=1950, le=2100)
    cgpa: float | None = Field(default=None, ge=0.0, le=10.0)
    percentage: float | None = Field(default=None, ge=0.0, le=100.0)

    # Professional Fields, Specializations, and Goals
    primary_field: str | None = Field(default=None, max_length=150)
    secondary_fields: list[str] | None = None
    specializations: list[str] | None = None
    career_goals: list[str] | None = None
    learning_goals: list[str] | None = None

    # Professional Fields, Specializations, and Goals
    primary_field: str | None = Field(default=None, max_length=150)
    secondary_fields: list[str] = Field(default_factory=list)
    specializations: list[str] = Field(default_factory=list)
    career_goals: list[str] = Field(default_factory=list)
    learning_goals: list[str] = Field(default_factory=list)

    @field_validator("nationality", "country_of_residence", "city", mode="before")
    @classmethod
    def strip_whitespace(cls, v: Any) -> Any:
        if isinstance(v, str):
            v = v.strip()
            return v if v else None
        return v


class UserProfileCreate(UserProfileBase):
    pass


class UserProfileUpdate(BaseModel):
    nationality: str | None = Field(default=None, max_length=100)
    country_of_residence: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    date_of_birth: date | None = None
    education_level: EducationLevel | None = None
    current_education_level: EducationLevel | None = None
    education_status: str | None = Field(default=None, max_length=50)
    degree_title: str | None = Field(default=None, max_length=200)
    field_of_study: str | None = Field(default=None, max_length=200)
    university: str | None = Field(default=None, max_length=255)
    graduation_year: int | None = Field(default=None, ge=1950, le=2100)
    cgpa: float | None = Field(default=None, ge=0.0, le=10.0)
    percentage: float | None = Field(default=None, ge=0.0, le=100.0)

    # Professional Fields, Specializations, and Goals
    primary_field: str | None = Field(default=None, max_length=150)
    secondary_fields: list[str] | None = None
    specializations: list[str] | None = None
    career_goals: list[str] | None = None
    learning_goals: list[str] | None = None


class UserProfileRead(UserProfileBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


# Academic Records
class AcademicRecordBase(BaseModel):
    institution: str = Field(default="School / Institution", max_length=255)
    degree: str = Field(default="General Qualification", max_length=200)
    field_of_study: str = Field(default="General", max_length=200)
    education_level: EducationLevel | None = None
    academic_stream: str | None = Field(default=None, max_length=100)
    status: str | None = Field(default=None, max_length=50)
    grading_system: str | None = Field(default=None, max_length=50)
    start_year: int | None = Field(default=None, ge=1950, le=2100)
    end_year: int | None = Field(default=None, ge=1950, le=2100)
    grade: str | None = Field(default=None, max_length=50)
    grading_scale: str | None = Field(default=None, max_length=50)
    country: str | None = Field(default=None, max_length=100)
    is_current: bool = False
    is_highest: bool = False

    @model_validator(mode="after")
    def validate_year_range(self) -> "AcademicRecordBase":
        if self.start_year and self.end_year and self.end_year < self.start_year:
            raise ValueError("end_year cannot be before start_year.")
        return self


class AcademicRecordCreate(AcademicRecordBase):
    pass


class AcademicRecordUpdate(BaseModel):
    institution: str | None = Field(default=None, max_length=255)
    degree: str | None = Field(default=None, max_length=200)
    field_of_study: str | None = Field(default=None, max_length=200)
    education_level: EducationLevel | None = None
    academic_stream: str | None = Field(default=None, max_length=100)
    status: str | None = Field(default=None, max_length=50)
    grading_system: str | None = Field(default=None, max_length=50)
    start_year: int | None = Field(default=None, ge=1950, le=2100)
    end_year: int | None = Field(default=None, ge=1950, le=2100)
    grade: str | None = Field(default=None, max_length=50)
    grading_scale: str | None = Field(default=None, max_length=50)
    country: str | None = Field(default=None, max_length=100)
    is_current: bool | None = None
    is_highest: bool | None = None


class AcademicRecordRead(AcademicRecordBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


# Test Results
class TestResultBase(BaseModel):
    __test__ = False

    test_name: str = Field(min_length=2, max_length=100)
    test_type: TestType = TestType.OTHER
    score: str = Field(min_length=1, max_length=50)
    score_details: dict[str, Any] = Field(default_factory=dict)
    test_date: date | None = None
    expiry_date: date | None = None
    notes: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_test_dates(self) -> "TestResultBase":
        if self.test_date and self.expiry_date and self.expiry_date < self.test_date:
            raise ValueError("expiry_date cannot be before test_date.")
        return self


class TestResultCreate(TestResultBase):
    pass


class TestResultRead(TestResultBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


# Skills
class SkillBase(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    category: str | None = Field(default=None, max_length=100)
    proficiency: SkillProficiency = SkillProficiency.INTERMEDIATE
    years_of_experience: float | None = Field(default=None, ge=0.0, le=70.0)
    status: str = Field(default="have", max_length=30)
    acquisition_source: str | None = Field(default=None, max_length=100)


class SkillCreate(SkillBase):
    pass


class SkillRead(SkillBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


# Work Experience
class WorkExperienceBase(BaseModel):
    organization: str = Field(min_length=2, max_length=255)
    job_title: str = Field(min_length=2, max_length=200)
    employment_type: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=100)
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool = False
    description: str | None = Field(default=None, max_length=5000)
    skills_used: list[str] = Field(default_factory=list)
    portfolio_url: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_dates(self) -> "WorkExperienceBase":
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date cannot be before start_date.")
        return self


class WorkExperienceCreate(WorkExperienceBase):
    pass


class WorkExperienceRead(WorkExperienceBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


# Research Experience
class ResearchExperienceBase(BaseModel):
    research_area: str = Field(min_length=2, max_length=255)
    title: str = Field(min_length=2, max_length=255)
    institution: str = Field(min_length=2, max_length=255)
    role: str | None = Field(default=None, max_length=150)
    start_date: date | None = None
    end_date: date | None = None
    description: str | None = Field(default=None, max_length=5000)

    @model_validator(mode="after")
    def validate_dates(self) -> "ResearchExperienceBase":
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date cannot be before start_date.")
        return self


class ResearchExperienceCreate(ResearchExperienceBase):
    pass


class ResearchExperienceRead(ResearchExperienceBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


# Publications
class PublicationBase(BaseModel):
    title: str = Field(min_length=3, max_length=500)
    publication_type: str | None = Field(default=None, max_length=100)
    venue: str | None = Field(default=None, max_length=255)
    publication_date: date | None = None
    doi: str | None = Field(default=None, max_length=150)
    url: str | None = Field(default=None, max_length=500)
    authors: list[str] = Field(default_factory=list)
    description: str | None = Field(default=None, max_length=3000)


class PublicationCreate(PublicationBase):
    pass


class PublicationRead(PublicationBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


# Projects
class ProjectBase(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=3000)
    project_type: str | None = Field(default="Personal", max_length=100)
    role: str | None = Field(default=None, max_length=150)
    technologies: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    project_url: str | None = Field(default=None, max_length=500)
    outcome: str | None = Field(default=None, max_length=3000)
    start_date: date | None = None
    end_date: date | None = None

    @model_validator(mode="after")
    def validate_dates(self) -> "ProjectBase":
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date cannot be before start_date.")
        return self


class ProjectCreate(ProjectBase):
    pass


class ProjectRead(ProjectBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


# Certifications & Training
class CertificationBase(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    issuing_organization: str = Field(min_length=2, max_length=255)
    category: str | None = Field(default=None, max_length=100)
    status: str = Field(default="Completed", max_length=50)
    issue_date: date | None = None
    expiry_date: date | None = None
    credential_id: str | None = Field(default=None, max_length=150)
    verification_url: str | None = Field(default=None, max_length=500)
    skills: list[str] = Field(default_factory=list)


class CertificationCreate(CertificationBase):
    pass


class CertificationRead(CertificationBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


# Languages
class LanguageBase(BaseModel):
    language_name: str = Field(min_length=2, max_length=100)
    proficiency: LanguageProficiency = LanguageProficiency.CONVERSATIONAL


class LanguageCreate(LanguageBase):
    pass


class LanguageRead(LanguageBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


# User Preferences
class UserPreferencesBase(BaseModel):
    preferred_countries: list[str] = Field(default_factory=list)
    preferred_regions: list[str] = Field(default_factory=list)
    preferred_opportunity_categories: list[str] = Field(default_factory=list)
    preferred_fields: list[str] = Field(default_factory=list)
    funding_preference: str | None = Field(default=None, max_length=100)
    remote_preference: str | None = Field(default=None, max_length=100)
    study_mode: str | None = Field(default=None, max_length=100)


class UserPreferencesUpdate(UserPreferencesBase):
    pass


class UserPreferencesRead(UserPreferencesBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


# Aggregated Profile View
class FullUserProfileRead(BaseModel):
    """Consolidated representation of all profile dimensions."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    is_active: bool
    profile: UserProfileRead | None = None
    preferences: UserPreferencesRead | None = None
    academic_records: list[AcademicRecordRead] = Field(default_factory=list)
    test_results: list[TestResultRead] = Field(default_factory=list)
    skills: list[SkillRead] = Field(default_factory=list)
    certifications: list[CertificationRead] = Field(default_factory=list)
    work_experiences: list[WorkExperienceRead] = Field(default_factory=list)
    research_experiences: list[ResearchExperienceRead] = Field(default_factory=list)
    publications: list[PublicationRead] = Field(default_factory=list)
    projects: list[ProjectRead] = Field(default_factory=list)
    languages: list[LanguageRead] = Field(default_factory=list)
