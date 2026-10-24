from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SourceEvaluationCriteria(BaseModel):
    """Factors evaluated when assessing the reliability of an information source."""

    url: str
    domain: str
    is_https: bool
    is_gov_domain: bool = False
    is_edu_domain: bool = False
    is_recognized_org: bool = False
    publication_date: datetime | None = None
    has_author_or_organization: bool = False
    canonical_url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SourceTrustReport(BaseModel):
    """Trust evaluation assessment for an opportunity source."""

    source_url: str
    source_domain: str
    is_verified: bool = False
    trust_tier: str = Field(
        default="pending", description="unverified, recognized, official, authoritative"
    )
    evaluation_factors: dict[str, bool] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class SourceTrustService(ABC):
    """Abstract interface for verifying source authenticity
    and preventing fraudulent opportunities.
    """

    @abstractmethod
    async def evaluate_source(self, url: str, **kwargs: Any) -> SourceTrustReport:
        pass

    @abstractmethod
    async def is_official_domain(self, domain: str) -> bool:
        """Check if domain belongs to a verified government, university, or official foundation."""
        pass


class DefaultSourceTrustService(SourceTrustService):
    """Foundation implementation for source trust evaluation."""

    async def evaluate_source(self, url: str, **kwargs: Any) -> SourceTrustReport:
        domain = url.split("/")[2] if "/" in url else url
        is_gov = domain.endswith(".gov") or ".gov." in domain
        is_edu = domain.endswith(".edu") or ".edu." in domain or domain.endswith(".ac.uk")

        tier = "unverified"
        if is_gov or is_edu:
            tier = "official"

        return SourceTrustReport(
            source_url=url,
            source_domain=domain,
            is_verified=is_gov or is_edu,
            trust_tier=tier,
            evaluation_factors={
                "is_https": url.startswith("https://"),
                "is_gov_domain": is_gov,
                "is_edu_domain": is_edu,
            },
        )

    async def is_official_domain(self, domain: str) -> bool:
        return (
            domain.endswith(".gov")
            or ".gov." in domain
            or domain.endswith(".edu")
            or ".edu." in domain
        )
