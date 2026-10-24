"""Evaluator for opportunity extraction accuracy and unknown detection."""

from __future__ import annotations

from typing import Any

from app.evaluation.metrics.extraction_metrics import ExtractionMetricsCalculator


class ExtractionEvaluator:
    """Evaluates extraction predictions against curated dataset examples."""

    def __init__(self) -> None:
        self.calculator = ExtractionMetricsCalculator()

    def evaluate_batch(
        self,
        predictions: list[dict[str, Any]],
        ground_truths: list[dict[str, Any]],
    ) -> dict[str, float]:
        """Calculates precision, recall, F1, exact match, and unknown detection."""
        return self.calculator.evaluate_extractions(predictions, ground_truths)
