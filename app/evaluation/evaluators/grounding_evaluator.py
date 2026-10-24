"""Evaluator for conversational response grounding and claim verification."""

from __future__ import annotations

from typing import Any

from app.evaluation.metrics.grounding_metrics import GroundingMetricsCalculator


class GroundingEvaluator:
    """Verifies that assistant claims are supported by authoritative source evidence."""

    def __init__(self) -> None:
        self.calculator = GroundingMetricsCalculator()

    def evaluate_claims(
        self,
        claims: list[dict[str, Any]],
    ) -> dict[str, float]:
        """Calculates claim support rate, unsupported rate, and citation coverage."""
        return self.calculator.evaluate_claims(claims)
