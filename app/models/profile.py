from __future__ import annotations

import uuid
from datetime import date
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class EducationLevel(StrEnum):
    """Normalized education levels covering all global education pathways."""

    PRIMARY = "Primary / Elementary School"
    MIDDLE_SCHOOL = "Middle School / Lower Secondary"
    MATRICULATION = "Matriculation / Secondary School"
    INTERMEDIATE = "Intermediate / Higher Secondary"
    A_LEVELS_IB = "A-Levels / IB Diploma / Equivalent"
    VOCATIONAL = "Certificate / Vocational Training"
    ASSOCIATE = "Diploma / Associate Degree"
    BACHELORS = "Bachelor's / Undergraduate"
    MASTERS = "Master's / Postgraduate"
    DOCTORATE = "PhD / Doctorate"
    POSTDOCTORAL = "Postdoctoral Research"
    PROFESSIONAL = "Professional Qualification"
    NO_FORMAL = "No Formal Qualification / Other"

    # Backward compatibility aliases
    HIGH_SCHOOL = "High School"
    UNDERGRADUATE = "Undergraduate"
    GRADUATE = "Graduate"
    PHD = "PhD"
    OTHER = "Other"

    @classmethod
    def _missing_(cls, value: object) -> EducationLevel | None:
        if isinstance(value, str):
            val_norm = value.strip().lower()
            if any(term in val_norm for term in ("master", "graduate", "msc", "ms ")):
                return cls.MASTERS
            if any(term in val_norm for term in ("bachelor", "undergraduate", "bsc", "bs ")):
                return cls.BACHELORS
            if any(term in val_norm for term in ("phd", "doctor")):
                return cls.DOCTORATE
            if "postdoc" in val_norm:
                return cls.POSTDOCTORAL
            if any(term in val_norm for term in ("intermediate", "fsc", "hssc", "12th", "fa ", "ics")):
                return cls.INTERMEDIATE
            if any(term in val_norm for term in ("matric", "ssc", "high school", "10th", "o-level", "gcse")):
                return cls.MATRICULATION
            if any(term in val_norm for term in ("a-level", "ib diploma", "baccalaureate")):
                return cls.A_LEVELS_IB
            if any(term in val_norm for term in ("vocational", "tvet", "trade")):
                return cls.VOCATIONAL
            if any(term in val_norm for term in ("associate", "dae", "adp", "diploma")):
                return cls.ASSOCIATE
            if "middle" in val_norm:
                return cls.MIDDLE_SCHOOL
            if any(term in val_norm for term in ("primary", "elementary")):
                return cls.PRIMARY
            if any(term in val_norm for term in ("professional", "acca", "ca ", "cfa")):
                return cls.PROFESSIONAL
            if any(term in val_norm for term in ("none", "informal", "self", "other")):
                return cls.NO_FORMAL
        return None


class TestType(StrEnum):
    LANGUAGE = "Language"
    ADMISSION = "Standardized Admission"
    CERTIFICATION = "Certification"
    OTHER = "Other"


class SkillProficiency(StrEnum):
    BEGINNER = "Beginner"
    INTERMEDIATE = "Intermediate"
    ADVANCED = "Advanced"
    EXPERT = "Expert"


class LanguageProficiency(StrEnum):
    BASIC = "Basic"
    CONVERSATIONAL = "Conversational"
    FLUENT = "Fluent"
    NATIVE = "Native/Bilingual"


class UserProfile(Base, UUIDMixin, TimestampMixin):
    """Core profile model storing user demographics and primary academic background."""

    __tablename__ = "user_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    nationality: Mapped[str | None] = mapped_column(String(100), nullable=True)
    country_of_residence: Mapped[str | None] = mapped_column(String(100), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Primary Education Summary
    education_level: Mapped[EducationLevel | None] = mapped_column(
        Enum(EducationLevel, native_enum=False, length=60),
        nullable=True,
    )
    current_education_level: Mapped[EducationLevel | None] = mapped_column(
        Enum(EducationLevel, native_enum=False, length=60),
        nullable=True,
    )
    education_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    degree_title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    field_of_study: Mapped[str | None] = mapped_column(String(200), nullable=True)
    university: Mapped[str | None] = mapped_column(String(255), nullable=True)
    graduation_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cgpa: Mapped[float | None] = mapped_column(Float, nullable=True)
    percentage: Mapped[float | None] = mapped_column(Float, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="profile")


class AcademicRecord(Base, UUIDMixin, TimestampMixin):
    """Supports multiple historical and current academic degrees/qualifications."""

    __tablename__ = "academic_records"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    institution: Mapped[str] = mapped_column(String(255), default="School / Institution", nullable=False)
    degree: Mapped[str] = mapped_column(String(200), default="General Qualification", nullable=False)
    field_of_study: Mapped[str] = mapped_column(String(200), default="General", nullable=False)
    education_level: Mapped[EducationLevel | None] = mapped_column(
        Enum(EducationLevel, native_enum=False, length=60),
        nullable=True,
    )
    academic_stream: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    grading_system: Mapped[str | None] = mapped_column(String(50), nullable=True)
    start_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    grade: Mapped[str | None] = mapped_column(String(50), nullable=True)
    grading_scale: Mapped[str | None] = mapped_column(String(50), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_highest: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="academic_records")


class TestResult(Base, UUIDMixin, TimestampMixin):
    """Standardized test scores (IELTS, TOEFL, GRE, GMAT, SAT, etc.) and certifications."""

    __test__ = False

    __tablename__ = "test_results"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    test_name: Mapped[str] = mapped_column(String(100), nullable=False)
    test_type: Mapped[TestType] = mapped_column(
        Enum(TestType, native_enum=False, length=50),
        default=TestType.OTHER,
        nullable=False,
    )
    score: Mapped[str] = mapped_column(String(50), nullable=False)
    score_details: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    test_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="test_results")


class Skill(Base, UUIDMixin, TimestampMixin):
    """User skills across technical, research, or domain-specific areas."""

    __tablename__ = "user_skills"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    proficiency: Mapped[SkillProficiency] = mapped_column(
        Enum(SkillProficiency, native_enum=False, length=50),
        default=SkillProficiency.INTERMEDIATE,
        nullable=False,
    )
    years_of_experience: Mapped[float | None] = mapped_column(Float, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="skills")


class WorkExperience(Base, UUIDMixin, TimestampMixin):
    """User employment history."""

    __tablename__ = "work_experiences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    organization: Mapped[str] = mapped_column(String(255), nullable=False)
    job_title: Mapped[str] = mapped_column(String(200), nullable=False)
    employment_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="work_experiences")


class ResearchExperience(Base, UUIDMixin, TimestampMixin):
    """Academic and industrial research history."""

    __tablename__ = "research_experiences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    research_area: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    institution: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str | None] = mapped_column(String(150), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="research_experiences")


class Publication(Base, UUIDMixin, TimestampMixin):
    """Scholarly articles, conference proceedings, preprints, and patents."""

    __tablename__ = "publications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    publication_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    venue: Mapped[str | None] = mapped_column(String(255), nullable=True)
    publication_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    doi: Mapped[str | None] = mapped_column(String(150), nullable=True)
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    authors: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="publications")


class Project(Base, UUIDMixin, TimestampMixin):
    """Personal, open-source, or institutional practical projects."""

    __tablename__ = "projects"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    technologies: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    project_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="projects")


class Language(Base, UUIDMixin, TimestampMixin):
    """Spoken and written language proficiencies."""

    __tablename__ = "user_languages"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    language_name: Mapped[str] = mapped_column(String(100), nullable=False)
    proficiency: Mapped[LanguageProficiency] = mapped_column(
        Enum(LanguageProficiency, native_enum=False, length=50),
        default=LanguageProficiency.CONVERSATIONAL,
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="languages")


class UserPreferences(Base, UUIDMixin, TimestampMixin):
    """Target countries, fields, categories, and funding preferences for AI matching."""

    __tablename__ = "user_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    preferred_countries: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    preferred_regions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    preferred_opportunity_categories: Mapped[list[str]] = mapped_column(
        JSON, default=list, nullable=False
    )
    preferred_fields: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    funding_preference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    remote_preference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    study_mode: Mapped[str | None] = mapped_column(String(100), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="preferences")
