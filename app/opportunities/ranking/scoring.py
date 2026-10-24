"""Transparent scoring engine combining weighted factors into normalized relevance."""

from __future__ import annotations

from typing import Any

from app.opportunities.ranking.schemas import (
    RankingFactorDetail,
    RankingFactorType,
    SortMode,
)
from app.opportunities.ranking.weights import RankingWeightsConfig


class ScoringEngine:
    """Combines individual normalized ranking factors into explainable overall scores."""

    @classmethod
    def calculate_relevance(
        cls,
        factors: dict[RankingFactorType, RankingFactorDetail],
        weights_config: RankingWeightsConfig,
    ) -> float:
        """Calculates normalized overall relevance score [0.0, 1.0]."""
        normalized_weights = weights_config.get_normalized_weights()

        total_score = 0.0
        for factor_type, weight in normalized_weights.items():
            if factor_type in factors:
                factor_detail = factors[factor_type]
                factor_score = factor_detail.score
                weighted = factor_score * weight
                factor_detail.weight = weight
                factor_detail.weighted_score = round(weighted, 4)
                total_score += weighted

        # Clamp strictly between 0.0 and 1.0
        final_score = max(0.0, min(1.0, total_score))
        return round(final_score, 4)

    @classmethod
    def get_sort_key(
        cls,
        item: Any,
        sort_mode: SortMode,
    ) -> tuple[Any, ...]:
        """Produces a deterministic tuple for multi-criteria sorting."""
        # item is expected to have relevance_score, ranking_factors, freshness, deadline
        relevance = getattr(item, "relevance_score", 0.0)
        factors = getattr(item, "ranking_factors", {})
        freshness = getattr(item, "freshness", 1.0)

        funding_score = 0.0
        academic_score = 0.0
        deadline_score = 0.0

        for k, v in factors.items():
            ft = getattr(v, "factor_type", None) or k
            score = getattr(v, "score", 0.0)
            if ft in (RankingFactorType.FUNDING_FIT, "FUNDING_FIT"):
                funding_score = score
            elif ft in (RankingFactorType.ACADEMIC_FIT, "ACADEMIC_FIT"):
                academic_score = score
            elif ft in (RankingFactorType.DEADLINE_RELEVANCE, "DEADLINE_RELEVANCE"):
                deadline_score = score

        if sort_mode == SortMode.RELEVANCE:
            return (-relevance, -funding_score, -freshness)
        elif sort_mode == SortMode.FUNDING:
            return (-funding_score, -relevance, -freshness)
        elif sort_mode == SortMode.ACADEMIC_FIT:
            return (-academic_score, -relevance, -funding_score)
        elif sort_mode == SortMode.FRESHNESS:
            return (-freshness, -relevance, -funding_score)
        elif sort_mode == SortMode.DEADLINE:
            # High deadline score first (open soonest / optimal), then relevance
            return (-deadline_score, -relevance)
        return (-relevance,)
