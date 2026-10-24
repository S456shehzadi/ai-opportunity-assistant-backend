"""Metrics for conversational grounding, citation support, and claim verification."""

from __future__ import annotations

from typing import Any


class GroundingMetricsCalculator:
    """Calculates claim-level grounding and hallucination metrics."""

    @staticmethod
    def evaluate_claims(
        claims: list[dict[str, Any]],
    ) -> dict[str, float]:
        """Evaluates assertions categorized as SUPPORTED, PARTIALLY_SUPPORTED,
        UNSUPPORTED, or CONTRADICTED.
        """
        if not claims:
            return {
                "grounding_support_rate": 1.0,
                "unsupported_claim_rate": 0.0,
                "contradicted_claim_rate": 0.0,
                "citation_coverage": 1.0,
            }

        total_claims = len(claims)
        supported_count = 0
        unsupported_count = 0
        contradicted_count = 0
        has_citation_count = 0

        for c in claims:
            status = str(c.get("status", c.get("supported", ""))).upper()
            if status in ("SUPPORTED", "TRUE"):
                supported_count += 1
            elif status in ("CONTRADICTED",):
                contradicted_count += 1
            else:
                unsupported_count += 1

            source_ids = c.get("source_ids") or []
            if source_ids or c.get("has_citation"):
                has_citation_count += 1

        return {
            "grounding_support_rate": round(supported_count / total_claims, 4),
            "unsupported_claim_rate": round(unsupported_count / total_claims, 4),
            "contradicted_claim_rate": round(contradicted_count / total_claims, 4),
            "citation_coverage": round(has_citation_count / total_claims, 4),
        }
