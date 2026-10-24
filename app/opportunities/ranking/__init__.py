"""Personalized Opportunity Ranking & Recommendation Module."""

from app.opportunities.ranking.confidence import RecommendationConfidenceCalculator
from app.opportunities.ranking.deduplication import CandidateDeduplicator
from app.opportunities.ranking.diversity import DiversityOptimizer
from app.opportunities.ranking.engine import PersonalizedRankingEngine
from app.opportunities.ranking.explanations import RankingExplanationBuilder
from app.opportunities.ranking.freshness import FreshnessCalculator
from app.opportunities.ranking.rules import HardFilterEngine, SoftPreferenceEngine
from app.opportunities.ranking.schemas import (
    ExplanationCategory,
    OpportunityRankingContext,
    PreferenceFilterType,
    PreferencePriority,
    RankedOpportunity,
    RankedOpportunityResult,
    RankingFactorDetail,
    RankingFactorType,
    RecommendationConfidence,
    SortMode,
    StructuredRankingExplanation,
    UserPreference,
)
from app.opportunities.ranking.semantic import (
    DeterministicEmbeddingProvider,
    EmbeddingProvider,
    OpportunityRelevanceModel,
    RuleBasedRelevanceModel,
)
from app.opportunities.ranking.validators import RankingGuardrails
from app.opportunities.ranking.weights import RankingWeightsConfig

__all__ = [
    "CandidateDeduplicator",
    "DeterministicEmbeddingProvider",
    "DiversityOptimizer",
    "EmbeddingProvider",
    "ExplanationCategory",
    "FreshnessCalculator",
    "HardFilterEngine",
    "OpportunityRankingContext",
    "OpportunityRelevanceModel",
    "PersonalizedRankingEngine",
    "PreferenceFilterType",
    "PreferencePriority",
    "RankedOpportunity",
    "RankedOpportunityResult",
    "RankingExplanationBuilder",
    "RankingFactorDetail",
    "RankingFactorType",
    "RankingGuardrails",
    "RankingWeightsConfig",
    "RecommendationConfidence",
    "RecommendationConfidenceCalculator",
    "RuleBasedRelevanceModel",
    "SoftPreferenceEngine",
    "SortMode",
    "StructuredRankingExplanation",
    "UserPreference",
]
