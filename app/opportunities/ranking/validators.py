"""Guardrails ensuring zero-outcome-prediction and eligibility non-override invariants."""

from __future__ import annotations

import re
from typing import ClassVar

from app.opportunities.eligibility.schemas import EligibilityResult, OverallEligibilityStatus
from app.opportunities.ranking.schemas import RankedOpportunity


class RankingGuardrails:
    """Audits ranking outputs to enforce non-probabilistic transparency."""

    FORBIDDEN_PROBABILISTIC_PATTERNS: ClassVar[list[re.Pattern]] = [
        re.compile(r"\badmission\s+(?:probability|chance|rate|likelihood)\b", re.I),
        re.compile(r"\bscholarship\s+(?:selection\s+probability|chance|selection\s+rate)\b", re.I),
        re.compile(r"\b(?:winning|acceptance)\s+(?:probability|chance|rate|likelihood)\b", re.I),
        re.compile(
            r"\bchance\s+of\s+(?:acceptance|admission|winning|getting\s+in|selection)\b", re.I
        ),
        re.compile(r"\b(?:you\s+will|user\s+will)\s+be\s+selected\b", re.I),
        re.compile(r"\b(?:guaranteed|probable)\s+admission\b", re.I),
    ]

    @classmethod
    def audit_text(cls, text: str) -> bool:
        """Returns True if text contains forbidden outcome prediction language."""
        for pattern in cls.FORBIDDEN_PROBABILISTIC_PATTERNS:
            if pattern.search(text):
                return True
        return False

    @classmethod
    def validate_ranked_opportunity(
        cls, ranked_opp: RankedOpportunity, eligibility: EligibilityResult | None
    ) -> None:
        """Enforces critical safety and integrity invariants on a ranked opportunity."""
        # 1. Zero-Outcome-Prediction Guardrail
        all_texts = [
            ranked_opp.fit_summary,
            *ranked_opp.positive_factors,
            *ranked_opp.negative_factors,
            *ranked_opp.unknown_factors,
            *(exp.text for exp in ranked_opp.explanations),
        ]

        for txt in all_texts:
            if cls.audit_text(txt):
                raise ValueError(
                    f"Ranking Guardrail Violation: Probabilistic prediction in: '{txt}'."
                )

        # 2. Eligibility Authority Guardrail (Non-override invariant)
        if eligibility is not None:
            if eligibility.overall_status == OverallEligibilityStatus.CLEARLY_NOT_ELIGIBLE:
                if ranked_opp.eligibility_status != OverallEligibilityStatus.CLEARLY_NOT_ELIGIBLE:
                    raise ValueError(
                        "Ranking Guardrail Violation: Ineligible status must not be overridden."
                    )
