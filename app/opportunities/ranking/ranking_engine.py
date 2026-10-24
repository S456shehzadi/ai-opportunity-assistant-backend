from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from app.opportunities.schemas.opportunity import OpportunityRead


class RankingCriteria(BaseModel):
    """Parameters to guide the multi-factor ranking algorithm."""

    user_field_of_study: str | None = None
    user_nationality: str | None = None
    user_degree_level: str | None = None
    preferred_countries: list[str] = Field(default_factory=list)
    prioritize_urgency: bool = True
    prioritize_funding: bool = True
    weights: dict[str, float] = Field(default_factory=dict)


class ScoredOpportunity(BaseModel):
    """Opportunity decorated with explainable ranking scores."""

    opportunity: OpportunityRead
    relevance_score: float = Field(ge=0.0, le=1.0)
    eligibility_fit_score: float = Field(ge=0.0, le=1.0)
    urgency_score: float = Field(ge=0.0, le=1.0)
    final_score: float = Field(ge=0.0, le=1.0)
    match_reasons: list[str] = Field(default_factory=list)


class OpportunityRankingEngine(ABC):
    """Abstract interface for opportunity scoring and candidate ranking."""

    @abstractmethod
    async def rank(
        self,
        opportunities: list[OpportunityRead],
        criteria: RankingCriteria,
        **kwargs: Any,
    ) -> list[ScoredOpportunity]:
        pass
