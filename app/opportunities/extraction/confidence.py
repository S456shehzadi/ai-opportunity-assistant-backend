"""Extraction confidence scoring engine.

Calculates confidence based purely on extraction fidelity, evidence coverage,
and schema completeness, strictly independent from external source trust scores.
"""

from __future__ import annotations

from app.opportunities.extraction.schemas import (
    ExtractedField,
    ExtractedOpportunity,
    FieldStatus,
)


class ConfidenceCalculator:
    """Computes an objective extraction confidence score (0.0 to 1.0)."""

    CORE_FIELDS = [
        "title",
        "organization",
        "category",
        "description",
        "funding_type",
        "application_deadline",
        "application_url",
    ]

    @classmethod
    def calculate(cls, opp: ExtractedOpportunity) -> float:
        """Calculates extraction confidence based on evidence presence and field status."""
        score = 0.0
        max_possible = 0.0

        # Core fields have high weight
        for field_name in cls.CORE_FIELDS:
            field = getattr(opp, field_name, None)
            if field is None:
                continue

            weight = 15.0 if field_name in ("title", "organization", "funding_type") else 10.0
            max_possible += weight

            if isinstance(field, ExtractedField):
                if field.status == FieldStatus.FOUND:
                    field_conf = field.confidence if field.confidence > 0 else 0.8
                    # Give bonus if evidence is attached
                    if field.evidence:
                        field_conf = min(1.0, field_conf + 0.1)
                    score += weight * field_conf
                elif field.status == FieldStatus.INFERRED:
                    score += weight * 0.5
                elif field.status == FieldStatus.NOT_FOUND:
                    # If accurately identified as NOT_FOUND (e.g. rolling deadline or unmentioned),
                    # no penalty if reasonable
                    score += weight * 0.1
            elif isinstance(field, str):
                if field and field.strip() and field.lower() != "unknown":
                    score += weight * 0.95
                else:
                    score += weight * 0.1
            else:
                score += weight * 0.9

        # Check list requirements presence
        if opp.language_requirements:
            score += 10.0
        max_possible += 10.0

        if opp.academic_requirements:
            score += 10.0
        max_possible += 10.0

        if opp.benefits:
            score += 5.0
        max_possible += 5.0

        raw_ratio = score / max(1.0, max_possible)

        # Penalize if conflicts were detected
        conflict_penalty = min(0.3, len(opp.notes) * 0.05)
        final_score = max(0.1, min(1.0, raw_ratio - conflict_penalty))

        return round(final_score, 2)
