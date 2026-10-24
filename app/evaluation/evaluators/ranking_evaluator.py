"""Evaluator for personalized ranking quality and eligibility constraint satisfaction."""

from __future__ import annotations

from app.evaluation.metrics.ranking_metrics import RankingMetricsCalculator


class RankingEvaluator:
    """Evaluates ranking order using Precision@K, NDCG@K, MRR, and constraint satisfaction."""

    def __init__(self) -> None:
        self.calculator = RankingMetricsCalculator()

    def evaluate(
        self,
        predicted_ids: list[str],
        relevance_grades: dict[str, int],
        k: int = 5,
        ineligible_ids: set[str] | None = None,
    ) -> dict[str, float]:
        """Calculates ranking performance metrics."""
        return self.calculator.evaluate_ranking(
            predicted_ids=predicted_ids,
            relevance_dict=relevance_grades,
            k=k,
            ineligible_ids=ineligible_ids,
        )
