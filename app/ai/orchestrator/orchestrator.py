from abc import ABC, abstractmethod
from typing import Any

from app.ai.interfaces.grounding import GroundedResponse
from app.ai.interfaces.specialized import (
    EligibilityEvaluation,
    ExtractedRawOpportunity,
    SearchIntent,
)


class AIOrchestrator(ABC):
    """Abstract interface for the AI Orchestration layer.

    Coordinates query understanding, targeted web search, extraction,
    source verification, eligibility assessment, ranking, and grounded response generation.
    """

    @abstractmethod
    async def understand_query(self, user_query: str) -> SearchIntent:
        """Analyze intent and formulate targeted search queries."""
        pass

    @abstractmethod
    async def search_and_retrieve(self, search_queries: list[str]) -> list[dict[str, Any]]:
        """Search the web via configured SearchProvider and
        retrieve page contents via WebRetriever.
        """
        pass

    @abstractmethod
    async def extract_opportunities(
        self, retrieved_documents: list[dict[str, Any]]
    ) -> list[ExtractedRawOpportunity]:
        """Extract structured opportunity candidates using specialized extraction models."""
        pass

    @abstractmethod
    async def verify_sources(
        self, opportunities: list[ExtractedRawOpportunity]
    ) -> list[ExtractedRawOpportunity]:
        """Cross-examine sources with SourceTrustService and verify official domains."""
        pass

    @abstractmethod
    async def evaluate_eligibility(
        self, user_profile: dict[str, Any], opportunities: list[ExtractedRawOpportunity]
    ) -> list[EligibilityEvaluation]:
        """Evaluate applicant fit and hard eligibility constraints."""
        pass

    @abstractmethod
    async def rank_opportunities(
        self,
        user_profile: dict[str, Any],
        opportunities: list[ExtractedRawOpportunity],
        eligibilities: list[EligibilityEvaluation],
    ) -> list[ExtractedRawOpportunity]:
        """Rank opportunities according to relevance, urgency, fit, and source authority."""
        pass

    @abstractmethod
    async def generate_response(
        self,
        user_query: str,
        ranked_opportunities: list[ExtractedRawOpportunity],
        eligibility_evaluations: list[EligibilityEvaluation],
    ) -> GroundedResponse:
        """Synthesize source-grounded response preventing hallucinations."""
        pass


class OpportunityAIOrchestrator(AIOrchestrator):
    """Concrete orchestrator coordinating decoupled AI and search pipelines."""

    def __init__(self, provider_type: str = "mock") -> None:
        self.provider_type = provider_type

    async def understand_query(self, user_query: str) -> SearchIntent:
        return SearchIntent(
            raw_query=user_query,
            generated_search_queries=[user_query],
        )

    async def search_and_retrieve(self, search_queries: list[str]) -> list[dict[str, Any]]:
        return []

    async def extract_opportunities(
        self, retrieved_documents: list[dict[str, Any]]
    ) -> list[ExtractedRawOpportunity]:
        return []

    async def verify_sources(
        self, opportunities: list[ExtractedRawOpportunity]
    ) -> list[ExtractedRawOpportunity]:
        return opportunities

    async def evaluate_eligibility(
        self, user_profile: dict[str, Any], opportunities: list[ExtractedRawOpportunity]
    ) -> list[EligibilityEvaluation]:
        return []

    async def rank_opportunities(
        self,
        user_profile: dict[str, Any],
        opportunities: list[ExtractedRawOpportunity],
        eligibilities: list[EligibilityEvaluation],
    ) -> list[ExtractedRawOpportunity]:
        return opportunities

    async def generate_response(
        self,
        user_query: str,
        ranked_opportunities: list[ExtractedRawOpportunity],
        eligibility_evaluations: list[EligibilityEvaluation],
    ) -> GroundedResponse:
        return GroundedResponse(
            summary="Orchestration pipeline ready for future implementation.",
            claims=[],
            cited_sources=[],
        )
