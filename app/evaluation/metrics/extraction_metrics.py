"""Metrics for evaluating opportunity field extraction accuracy and unknown detection."""

from __future__ import annotations

from typing import Any


class ExtractionMetricsCalculator:
    """Calculates extraction precision, recall, F1, exact match, and unknown detection."""

    @staticmethod
    def evaluate_extractions(
        predictions: list[dict[str, Any]],
        ground_truths: list[dict[str, Any]],
        fields_to_evaluate: list[str] | None = None,
        fields: list[str] | None = None,
    ) -> dict[str, float]:
        """Compares predicted fields against ground truths."""
        if not predictions or not ground_truths or len(predictions) != len(ground_truths):
            return {
                "exact_match_rate": 0.0,
                "field_precision": 0.0,
                "field_recall": 0.0,
                "field_f1": 0.0,
                "precision": 0.0,
                "recall": 0.0,
                "f1": 0.0,
                "unknown_detection_accuracy": 1.0,
            }

        target_fields = (
            fields
            or fields_to_evaluate
            or [
                "title",
                "organization",
                "category",
                "deadline",
                "funding_type",
                "funding_amount",
                "degree_levels",
                "eligible_nationalities",
                "application_url",
            ]
        )

        total_field_checks = 0
        exact_matches = 0
        true_positives = 0
        false_positives = 0
        false_negatives = 0

        unknown_checks = 0
        unknown_correct = 0

        for pred, gt in zip(predictions, ground_truths, strict=True):
            for field in target_fields:
                total_field_checks += 1
                pred_val = pred.get(field)
                gt_val = gt.get(field)

                is_gt_unknown = gt_val is None or gt_val == "" or gt_val == []
                is_pred_unknown = (
                    pred_val is None or pred_val == "" or pred_val == [] or pred_val == "UNKNOWN"
                )

                # Unknown detection evaluation
                if is_gt_unknown:
                    unknown_checks += 1
                    if is_pred_unknown:
                        unknown_correct += 1
                        exact_matches += 1
                    else:
                        # Model hallucinated / invented a value
                        false_positives += 1
                else:
                    # Ground truth has actual value
                    if is_pred_unknown:
                        false_negatives += 1
                    else:
                        # Compare values
                        if isinstance(gt_val, list):
                            pred_set = set(pred_val) if isinstance(pred_val, list) else {pred_val}
                            gt_set = set(gt_val)
                            overlap = len(pred_set & gt_set)
                            true_positives += overlap
                            false_positives += len(pred_set - gt_set)
                            false_negatives += len(gt_set - pred_set)
                            if pred_set == gt_set:
                                exact_matches += 1
                        else:
                            if str(pred_val).strip().lower() == str(gt_val).strip().lower():
                                exact_matches += 1
                                true_positives += 1
                            else:
                                false_positives += 1

        precision = (
            true_positives / (true_positives + false_positives)
            if (true_positives + false_positives) > 0
            else 0.0
        )
        recall = (
            true_positives / (true_positives + false_negatives)
            if (true_positives + false_negatives) > 0
            else 0.0
        )
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        em_rate = exact_matches / total_field_checks if total_field_checks > 0 else 0.0
        unknown_acc = unknown_correct / unknown_checks if unknown_checks > 0 else 1.0

        return {
            "exact_match_rate": round(em_rate, 4),
            "field_precision": round(precision, 4),
            "field_recall": round(recall, 4),
            "field_f1": round(f1, 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "unknown_detection_accuracy": round(unknown_acc, 4),
        }

    # Alias for evaluator and test callers
    calculate_batch = evaluate_extractions
