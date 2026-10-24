"""Evaluator for source domain trust tier and extraction reliability."""

from __future__ import annotations

from typing import Any


class SourceEvaluator:
    """Evaluates authoritative source reliability, freshness, and stability."""

    TRUST_TIER_WEIGHTS = {
        "OFFICIAL_GOVERNMENT": 1.0,
        "OFFICIAL_PORTAL": 1.0,
        "OFFICIAL_UNIVERSITY": 0.95,
        "OFFICIAL_ORGANIZATION": 0.90,
        "SECONDARY": 0.60,
        "DIRECTORY": 0.40,
        "UNKNOWN": 0.20,
    }

    @classmethod
    def evaluate_source(
        cls,
        source_type: str,
        http_success_rate: float = 1.0,
        freshness_days: int = 0,
    ) -> dict[str, Any]:
        """Scores source quality based on tier, uptime, and freshness."""
        base_trust = cls.TRUST_TIER_WEIGHTS.get(source_type.upper(), 0.2)
        reliability = base_trust * http_success_rate
        is_stale = freshness_days > 90

        return {
            "source_type": source_type,
            "base_trust": base_trust,
            "reliability_score": round(reliability, 2),
            "is_stale": is_stale,
            "is_trusted": reliability >= 0.8,
        }
