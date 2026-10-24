"""Tests for evaluation metrics calculators and benchmark evaluators."""

from __future__ import annotations

import pytest

from app.evaluation.evaluators.eligibility_evaluator import EligibilityEvaluator
from app.evaluation.metrics.extraction_metrics import ExtractionMetricsCalculator
from app.evaluation.metrics.grounding_metrics import GroundingMetricsCalculator
from app.evaluation.metrics.ranking_metrics import RankingMetricsCalculator


def test_extraction_metrics_perfect_and_unknown_detection() -> None:
    # Ground truth has known title and deadline, but unknown funding amount
    ground_truths = [
        {
            "title": "Global Excellence Scholarship",
            "deadline": "2026-11-01",
            "amount": None,
        }
    ]

    # Predictor correctly extracts title and deadline, and correctly predicts UNKNOWN for amount
    predictions = [
        {
            "title": "Global Excellence Scholarship",
            "deadline": "2026-11-01",
            "amount": "UNKNOWN",
        }
    ]

    metrics = ExtractionMetricsCalculator.calculate_batch(
        predictions=predictions,
        ground_truths=ground_truths,
        fields=["title", "deadline", "amount"],
    )

    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["f1"] == 1.0
    assert metrics["exact_match_rate"] == 1.0
    assert metrics["unknown_detection_accuracy"] == 1.0


def test_extraction_metrics_penalizes_hallucinations_on_unknowns() -> None:
    # Ground truth has unknown funding amount
    ground_truths = [{"title": "Merit Grant", "amount": None}]

    # Predictor hallucinates $50,000 for amount
    hallucinating_predictions = [{"title": "Merit Grant", "amount": "$50,000"}]

    metrics = ExtractionMetricsCalculator.calculate_batch(
        predictions=hallucinating_predictions,
        ground_truths=ground_truths,
        fields=["title", "amount"],
    )

    # False positive penalized
    assert metrics["unknown_detection_accuracy"] == 0.0
    assert metrics["precision"] < 1.0


def test_ranking_metrics_ndcg_and_eligibility_violations() -> None:
    # Predicted top 4 items
    predicted_ids = ["opp_1", "opp_2", "opp_3", "opp_4"]
    relevance_grades = {"opp_1": 3.0, "opp_2": 2.0, "opp_3": 0.0, "opp_4": 1.0}

    # NDCG@3
    ndcg = RankingMetricsCalculator.calculate_ndcg_at_k(predicted_ids, relevance_grades, k=3)
    assert 0.0 <= ndcg <= 1.0
    assert ndcg > 0.8  # Highly relevant items are first

    # MRR
    mrr = RankingMetricsCalculator.calculate_mrr(predicted_ids, relevance_grades)
    assert mrr == 1.0  # Top item has grade 3.0

    # Eligibility violation rate (opp_2 was ranked high but user was ineligible)
    violation_rate = RankingMetricsCalculator.calculate_eligibility_violation_rate(
        ranked_opportunity_ids=predicted_ids,
        ineligible_opportunity_ids={"opp_2"},
    )
    assert violation_rate == 0.25  # 1 out of 4


def test_grounding_metrics_claim_evaluations() -> None:
    claims = [
        {"claim": "Covers tuition", "status": "SUPPORTED", "has_citation": True},
        {"claim": "Provides monthly stipend", "status": "SUPPORTED", "has_citation": True},
        {
            "claim": "Guarantees admission to Oxford",
            "status": "CONTRADICTED",
            "has_citation": False,
        },
        {"claim": "Open to high school students", "status": "UNSUPPORTED", "has_citation": False},
    ]

    metrics = GroundingMetricsCalculator.evaluate_claims(claims)

    assert metrics["grounding_support_rate"] == 0.5  # 2 out of 4
    assert metrics["unsupported_claim_rate"] == 0.25  # 1 out of 4
    assert metrics["contradicted_claim_rate"] == 0.25  # 1 out of 4
    assert metrics["citation_coverage"] == 0.5


@pytest.mark.asyncio
async def test_eligibility_evaluator_dataset() -> None:
    evaluator = EligibilityEvaluator()

    test_cases = [
        {
            "profile": {
                "user_id": "u1",
                "normalized_gpa_4_scale": 3.8,
                "highest_cgpa": 3.8,
                "highest_degree_level": "BACHELOR",
            },
            "opportunity": {
                "id": "opp1",
                "title": "STEM Scholarship",
                "minimum_cgpa": 3.5,
                "degree_levels": ["BACHELOR"],
            },
            "expected_status": "ELIGIBLE",
        },
        {
            "profile": {
                "user_id": "u2",
                "normalized_gpa_4_scale": 2.5,
                "highest_cgpa": 2.5,
                "highest_degree_level": "BACHELOR",
            },
            "opportunity": {
                "id": "opp2",
                "title": "High Honors Award",
                "minimum_cgpa": 3.5,
                "degree_levels": ["BACHELOR"],
            },
            "expected_status": "INELIGIBLE",
        },
    ]

    results = await evaluator.evaluate_dataset(test_cases)
    assert results["total_cases"] == 2
    assert results["accuracy"] == 1.0
    assert results["eligible_accuracy"] == 1.0
    assert results["ineligible_accuracy"] == 1.0
