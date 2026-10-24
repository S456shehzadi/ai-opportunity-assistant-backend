from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class SearchIntent(BaseModel):
    """Structured representation of interpreted user intent."""

    raw_query: str
    target_categories: list[str] = Field(default_factory=list)
    target_countries: list[str] = Field(default_factory=list)
    degree_level: str | None = None
    field_of_study: str | None = None
    generated_search_queries: list[str] = Field(default_factory=list)
    confidence: float = 1.0


class ExtractedRawOpportunity(BaseModel):
    """Raw structured opportunity candidate extracted from retrieved content."""

    title: str
    organization: str
    source_url: str
    snippet: str
    inferred_deadline: str | None = None
    inferred_funding_type: str | None = None
    inferred_eligibility: list[str] = Field(default_factory=list)
    confidence: float = 1.0


class EligibilityEvaluation(BaseModel):
    """Result of assessing user eligibility against opportunity requirements."""

    opportunity_id: str
    is_eligible: bool
    matching_criteria: list[str] = Field(default_factory=list)
    unmet_criteria: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    confidence: float = 1.0


class QueryUnderstandingModel(ABC):
    """Specialized model interface for interpreting user natural language queries."""

    @abstractmethod
    async def analyze_intent(self, query: str, **kwargs: Any) -> SearchIntent:
        pass


class OpportunityExtractionModel(ABC):
    """Specialized model interface for extracting structured opportunity data from web text."""

    @abstractmethod
    async def extract_opportunities(
        self, html_text: str, source_url: str, **kwargs: Any
    ) -> list[ExtractedRawOpportunity]:
        pass


class EligibilityModel(ABC):
    """Specialized model interface for assessing opportunity eligibility."""

    @abstractmethod
    async def evaluate_eligibility(
        self, user_profile: dict[str, Any], opportunity: dict[str, Any], **kwargs: Any
    ) -> EligibilityEvaluation:
        pass


class RankingModel(ABC):
    """Specialized model interface for computing relevance and fit ranking."""

    @abstractmethod
    async def rank_opportunities(
        self,
        user_profile: dict[str, Any],
        opportunities: list[dict[str, Any]],
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        pass


class EmbeddingModel(ABC):
    """Specialized model interface for vector representation."""

    @abstractmethod
    async def get_embeddings(self, texts: list[str], **kwargs: Any) -> list[list[float]]:
        pass


class ResponseGenerationModel(ABC):
    """Specialized model interface for generating grounded natural language responses."""

    @abstractmethod
    async def generate_grounded_answer(
        self,
        query: str,
        facts: list[dict[str, Any]],
        **kwargs: Any,
    ) -> str:
        pass
