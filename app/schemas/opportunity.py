import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.opportunity import (
    OpportunityCategory,
    OpportunityStatus,
    RequirementOperator,
    SourceType,
)


# Opportunity Requirements
class OpportunityRequirementBase(BaseModel):
    requirement_type: str = Field(min_length=2, max_length=100)
    operator: RequirementOperator = RequirementOperator.GREATER_THAN_EQUAL
    value: Any
    unit: str | None = Field(default=None, max_length=50)
    is_mandatory: bool = True


class OpportunityRequirementCreate(OpportunityRequirementBase):
    pass


class OpportunityRequirementRead(OpportunityRequirementBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    opportunity_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


# Opportunity Sources
class OpportunitySourceBase(BaseModel):
    url: str = Field(min_length=5, max_length=1000)
    domain: str = Field(min_length=3, max_length=255)
    source_type: SourceType = SourceType.OFFICIAL_WEBSITE
    is_official: bool = False
    verification_status: str = Field(default="unverified", max_length=50)
    last_checked_at: datetime | None = None


class OpportunitySourceCreate(OpportunitySourceBase):
    pass


class OpportunitySourceRead(OpportunitySourceBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    opportunity_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


# Opportunity
class OpportunityBase(BaseModel):
    title: str = Field(min_length=3, max_length=300)
    organization: str = Field(min_length=2, max_length=255)
    category: OpportunityCategory = OpportunityCategory.SCHOLARSHIP
    description: str = Field(min_length=10)
    country: str = Field(default="Global", max_length=100)

    eligible_countries: list[str] = Field(default_factory=lambda: ["Global"])
    eligible_nationalities: list[str] = Field(default_factory=lambda: ["Global"])
    degree_levels: list[str] = Field(default_factory=list)
    fields: list[str] = Field(default_factory=list)

    funding_type: str = Field(default="Unknown", max_length=100)
    funding_amount: str | None = Field(default=None, max_length=100)
    currency: str | None = Field(default=None, max_length=10)

    opening_date: date | None = None
    deadline: date | None = None

    application_url: str | None = Field(default=None, max_length=1000)
    official_source_url: str = Field(min_length=5, max_length=1000)
    source_domain: str = Field(min_length=3, max_length=255)

    status: OpportunityStatus = OpportunityStatus.ACTIVE
    last_verified_at: datetime | None = None


class OpportunityCreate(OpportunityBase):
    sources: list[OpportunitySourceCreate] = Field(default_factory=list)
    requirements: list[OpportunityRequirementCreate] = Field(default_factory=list)


class OpportunityUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=300)
    organization: str | None = Field(default=None, max_length=255)
    category: OpportunityCategory | None = None
    description: str | None = None
    country: str | None = None
    eligible_countries: list[str] | None = None
    eligible_nationalities: list[str] | None = None
    degree_levels: list[str] | None = None
    fields: list[str] | None = None
    funding_type: str | None = None
    funding_amount: str | None = None
    currency: str | None = None
    opening_date: date | None = None
    deadline: date | None = None
    application_url: str | None = None
    official_source_url: str | None = None
    source_domain: str | None = None
    status: OpportunityStatus | None = None


class OpportunityRead(OpportunityBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    sources: list[OpportunitySourceRead] = Field(default_factory=list)
    requirements: list[OpportunityRequirementRead] = Field(default_factory=list)
