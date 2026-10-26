from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.interaction import AIInteraction, SearchSession
    from app.models.profile import (
        AcademicRecord,
        Certification,
        Language,
        Project,
        Publication,
        ResearchExperience,
        Skill,
        TestResult,
        UserPreferences,
        UserProfile,
        WorkExperience,
    )


class UserRole(StrEnum):
    """User authorization roles for access control and human review workflows."""

    USER = "USER"
    REVIEWER = "REVIEWER"
    ADMIN = "ADMIN"
    DATA_REVIEWER = "DATA_REVIEWER"
    ML_ENGINEER = "ML_ENGINEER"


class User(Base, UUIDMixin, TimestampMixin):
    """Foundational user entity supporting production authentication."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    full_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    hashed_password: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False, length=20),
        default=UserRole.USER,
        nullable=False,
    )

    # 1-to-1 Profile
    profile: Mapped["UserProfile | None"] = relationship(
        "UserProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # 1-to-1 Preferences
    preferences: Mapped["UserPreferences | None"] = relationship(
        "UserPreferences",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # 1-to-many Profile Sub-Records
    academic_records: Mapped[list["AcademicRecord"]] = relationship(
        "AcademicRecord",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="desc(AcademicRecord.start_year)",
    )
    test_results: Mapped[list["TestResult"]] = relationship(
        "TestResult",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    skills: Mapped[list["Skill"]] = relationship(
        "Skill",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    work_experiences: Mapped[list["WorkExperience"]] = relationship(
        "WorkExperience",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="desc(WorkExperience.start_date)",
    )
    research_experiences: Mapped[list["ResearchExperience"]] = relationship(
        "ResearchExperience",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="desc(ResearchExperience.start_date)",
    )
    publications: Mapped[list["Publication"]] = relationship(
        "Publication",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="desc(Publication.publication_date)",
    )
    projects: Mapped[list["Project"]] = relationship(
        "Project",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="desc(Project.start_date)",
    )
    certifications: Mapped[list["Certification"]] = relationship(
        "Certification",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="desc(Certification.issue_date)",
    )
    languages: Mapped[list["Language"]] = relationship(
        "Language",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    # 1-to-many Sessions & AI Interactions
    search_sessions: Mapped[list["SearchSession"]] = relationship(
        "SearchSession",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    ai_interactions: Mapped[list["AIInteraction"]] = relationship(
        "AIInteraction",
        back_populates="user",
        cascade="all, delete-orphan",
    )
