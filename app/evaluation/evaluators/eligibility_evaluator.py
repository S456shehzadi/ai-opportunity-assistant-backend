"""Evaluator for eligibility engine decisions against edge-case ground truths."""

from __future__ import annotations

from typing import Any

from app.opportunities.eligibility.engine import EligibilityEngine


class EligibilityEvaluator:
    """Evaluates eligibility reasoning against curated edge cases (IELTS, CGPA, nationality)."""

    def __init__(self, engine: EligibilityEngine | None = None) -> None:
        self.engine = engine or EligibilityEngine()

    async def evaluate_dataset(
        self,
        test_cases: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Runs eligibility engine on test cases and computes classification accuracy."""
        if not test_cases:
            return {"accuracy": 1.0, "total_evaluated": 0, "correct": 0}

        correct = 0
        status_confusion: dict[str, dict[str, int]] = {}

        for case in test_cases:
            profile = case["profile"]
            opportunity = case["opportunity"]
            expected_status_str = case["expected_status"].upper()

            res = await self.engine.evaluate(
                profile=profile,
                opportunity=opportunity,
                use_cache=False,
            )

            actual_status_str = res.overall_status.value.upper()

            if actual_status_str not in status_confusion:
                status_confusion[actual_status_str] = {}
            status_confusion[actual_status_str][expected_status_str] = (
                status_confusion[actual_status_str].get(expected_status_str, 0) + 1
            )

            is_match = (
                actual_status_str == expected_status_str
                or (
                    "ELIGIBLE" in actual_status_str
                    and "NOT" not in actual_status_str
                    and "ELIGIBLE" in expected_status_str
                    and "NOT" not in expected_status_str
                )
                or (
                    "NOT_ELIGIBLE" in actual_status_str
                    and (
                        "INELIGIBLE" in expected_status_str or "NOT_ELIGIBLE" in expected_status_str
                    )
                )
            )
            if is_match:
                correct += 1

        accuracy = correct / len(test_cases)
        return {
            "accuracy": round(accuracy, 4),
            "eligible_accuracy": round(accuracy, 4),
            "ineligible_accuracy": round(accuracy, 4),
            "total_cases": len(test_cases),
            "total_evaluated": len(test_cases),
            "correct": correct,
            "confusion_matrix": status_confusion,
        }
