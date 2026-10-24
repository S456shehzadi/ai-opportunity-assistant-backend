from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ConfidenceLevel(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNVERIFIED = "unverified"


class SourceEvidence(BaseModel):
    """Verifiable evidence snippet extracted directly from an official source."""

    source_url: str
    source_domain: str
    exact_text_snippet: str
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    is_official_source: bool = False


class GroundedClaim(BaseModel):
    """An individual assertion that must be backed by verifiable evidence.

    Prevents hallucinating deadlines, funding amounts, eligibility, or requirements.
    """

    claim_text: str
    property_name: str  # e.g., 'deadline', 'funding_amount', 'eligibility_criteria'
    evidence: list[SourceEvidence] = Field(default_factory=list)
    confidence: ConfidenceLevel = ConfidenceLevel.UNVERIFIED
    verified_at: datetime | None = None
    is_inferred: bool = False  # False if directly stated in evidence, True if reasoned


class GroundedResponse(BaseModel):
    """A complete grounded response structure that separates facts from reasoning."""

    summary: str
    claims: list[GroundedClaim] = Field(default_factory=list)
    cited_sources: list[str] = Field(default_factory=list)
    confidence_score: float = Field(ge=0.0, le=1.0, default=1.0)
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
