import uuid
from datetime import date, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
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


class OpportunityCategory(StrEnum):
    SCHOLARSHIP = "Scholarship"
    GRANT = "Grant"
    FELLOWSHIP = "Fellowship"
    INTERNSHIP = "Internship"
    RESEARCH_FUNDING = "Research Funding"
    RESEARCH_OPPORTUNITY = "Research Opportunity"
    EXCHANGE_PROGRAM = "Exchange Program"
    COMPETITION = "Competition"
    CONFERENCE = "Conference"
    STARTUP_FUNDING = "Startup Funding"
    GOVERNMENT_PROGRAM = "Government Program"
    VOLUNTEER_PROGRAM = "Volunteer Program"
    TRAINING_PROGRAM = "Training Program"
    OTHER = "Other"


class OpportunityStatus(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    UPCOMING = "upcoming"
    UNDER_REVIEW = "under_review"
    DRAFT = "draft"


class SourceType(StrEnum):
    OFFICIAL_WEBSITE = "Official Website"
    GOVERNMENT = "Government"
    UNIVERSITY = "University"
    ORGANIZATION = "Organization"
    NEWS = "News"
    AGGREGATOR = "Aggregator"
    OTHER = "Other"


class RequirementOperator(StrEnum):
    GREATER_THAN_EQUAL = ">="
    LESS_THAN_EQUAL = "<="
    EQUALS = "=="
    NOT_EQUALS = "!="
    IN = "in"
    CONTAINS = "contains"


class Opportunity(Base, UUIDMixin, TimestampMixin):
    """Core domain model representing a global opportunity."""

    __tablename__ = "opportunities"

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    organization: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[OpportunityCategory] = mapped_column(
        Enum(OpportunityCategory, native_enum=False, length=50),
        default=OpportunityCategory.SCHOLARSHIP,
        nullable=False,
        index=True,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    country: Mapped[str] = mapped_column(String(100), default="Global", nullable=False)
    host_countries: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    host_regions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    location_type: Mapped[str] = mapped_column(String(50), default="in_person", nullable=False)
    is_remote: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    eligible_countries: Mapped[list[str]] = mapped_column(
        JSON, default=lambda: ["Global"], nullable=False
    )
    eligible_nationalities: Mapped[list[str]] = mapped_column(
        JSON, default=lambda: ["Global"], nullable=False
    )
    restricted_applicant_countries: Mapped[list[str]] = mapped_column(
        JSON, default=list, nullable=False
    )
    degree_levels: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    fields: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    funding_type: Mapped[str] = mapped_column(String(100), default="Unknown", nullable=False)
    funding_amount: Mapped[str | None] = mapped_column(String(100), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(10), nullable=True)

    opening_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)

    application_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    official_source_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    source_domain: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    status: Mapped[OpportunityStatus] = mapped_column(
        Enum(OpportunityStatus, native_enum=False, length=50),
        default=OpportunityStatus.ACTIVE,
        nullable=False,
        index=True,
    )
    last_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    canonical_key: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    # 1-to-many sources
    sources: Mapped[list["OpportunitySource"]] = relationship(
        "OpportunitySource",
        back_populates="opportunity",
        cascade="all, delete-orphan",
    )

    # 1-to-many atomic requirements
    requirements: Mapped[list["OpportunityRequirement"]] = relationship(
        "OpportunityRequirement",
        back_populates="opportunity",
        cascade="all, delete-orphan",
    )

    # 1-to-many atomic evidence records
    evidences: Mapped[list["OpportunityEvidence"]] = relationship(
        "OpportunityEvidence",
        back_populates="opportunity",
        cascade="all, delete-orphan",
    )

    # 1-to-many version history snapshots
    versions: Mapped[list["OpportunityVersion"]] = relationship(
        "OpportunityVersion",
        back_populates="opportunity",
        cascade="all, delete-orphan",
    )


class OpportunitySource(Base, UUIDMixin, TimestampMixin):
    """Verifiable source URL associated with an opportunity."""

    __tablename__ = "opportunity_sources"

    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source_type: Mapped[SourceType] = mapped_column(
        Enum(SourceType, native_enum=False, length=50),
        default=SourceType.OFFICIAL_WEBSITE,
        nullable=False,
    )
    is_official: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verification_status: Mapped[str] = mapped_column(
        String(50), default="unverified", nullable=False
    )
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    opportunity: Mapped["Opportunity"] = relationship("Opportunity", back_populates="sources")


class OpportunityRequirement(Base, UUIDMixin, TimestampMixin):
    """Extensible rule representation of an opportunity constraint for future matching."""

    __tablename__ = "opportunity_requirements"

    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    requirement_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        # e.g., 'cgpa', 'age', 'degree_level', 'nationality', 'ielts', 'work_experience'
    )
    operator: Mapped[RequirementOperator] = mapped_column(
        Enum(RequirementOperator, native_enum=False, length=20),
        default=RequirementOperator.GREATER_THAN_EQUAL,
        nullable=False,
    )
    value: Mapped[Any] = mapped_column(JSON, nullable=False)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    opportunity: Mapped["Opportunity"] = relationship("Opportunity", back_populates="requirements")


class OpportunityEvidence(Base, UUIDMixin, TimestampMixin):
    """Source-grounded evidence snippet linked to an opportunity field."""

    __tablename__ = "opportunity_evidence"

    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    source_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    field_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    evidence_text: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_type: Mapped[str] = mapped_column(String(50), default="direct_text", nullable=False)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    opportunity: Mapped["Opportunity"] = relationship("Opportunity", back_populates="evidences")


class OpportunityVersion(Base, UUIDMixin, TimestampMixin):
    """Tracks chronological change history and snapshots of opportunities."""

    __tablename__ = "opportunity_versions"

    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    changed_fields: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    change_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    opportunity: Mapped["Opportunity"] = relationship("Opportunity", back_populates="versions")
