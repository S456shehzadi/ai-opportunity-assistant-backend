"""Confidence calculator measuring recommendation fidelity independent from relevance."""

from __future__ import annotations

from app.opportunities.eligibility.profile_adapter import UnifiedUserFacts
from app.opportunities.eligibility.schemas import EligibilityResult, OverallEligibilityStatus
from app.opportunities.ranking.schemas import RecommendationConfidence


class RecommendationConfidenceCalculator:
    """Evaluates whether the recommendation is based on complete, verified facts."""

    @classmethod
    def calculate(
        cls,
        eligibility_result: EligibilityResult | None,
        source_trust_score: float | None,
        user_facts: UnifiedUserFacts | None = None,
        has_conflicts: bool = False,
    ) -> tuple[RecommendationConfidence, str]:
        """Determines confidence tier (HIGH, MEDIUM, LOW) and diagnostic rationale."""
        confidence_points = 0
        reasons: list[str] = []

        # 1. Source Trust
        trust = source_trust_score if source_trust_score is not None else 0.5
        if trust >= 0.8:
            confidence_points += 2
        elif trust >= 0.5:
            confidence_points += 1
        else:
            reasons.append("Unverified or low-trust source domain")

        # 2. Eligibility Information Completeness
        if eligibility_result is not None:
            if eligibility_result.overall_status in (
                OverallEligibilityStatus.CLEARLY_ELIGIBLE,
                OverallEligibilityStatus.CLEARLY_NOT_ELIGIBLE,
            ):
                confidence_points += 2
            elif eligibility_result.overall_status == OverallEligibilityStatus.POTENTIALLY_ELIGIBLE:
                confidence_points += 1
                if eligibility_result.unknown_requirements:
                    reasons.append("Some eligibility criteria remain unverified")
            elif (
                eligibility_result.overall_status
                == OverallEligibilityStatus.CONFLICTING_INFORMATION
            ):
                reasons.append("Source contains conflicting eligibility claims")
            elif eligibility_result.overall_status == OverallEligibilityStatus.NEEDS_VERIFICATION:
                reasons.append("Key criteria (e.g. test score or waiver) need verification")

            # Check if there are active conflicts
            if eligibility_result.conflicts:
                has_conflicts = True
        else:
            reasons.append("Eligibility has not been formally evaluated")

        # 3. User Profile Completeness
        if user_facts is not None:
            has_nationality = bool(user_facts.nationality or user_facts.nationality_country_code)
            has_academics = bool(user_facts.academic_records or user_facts.highest_degree_level)
            if has_nationality and has_academics:
                confidence_points += 1
            else:
                reasons.append(
                    "User profile is partially incomplete (nationality or degree missing)"
                )
        else:
            reasons.append("Anonymous search without user profile data")

        # 4. Conflict penalty
        if has_conflicts:
            confidence_points = max(0, confidence_points - 2)

        # Derive final tier
        if confidence_points >= 4 and not has_conflicts:
            tier = RecommendationConfidence.HIGH
            summary = "High confidence: verified source and complete eligibility facts."
        elif confidence_points >= 2:
            tier = RecommendationConfidence.MEDIUM
            note = "; ".join(reasons) if reasons else "Moderate information completeness"
            summary = f"Medium confidence: {note}."
        else:
            tier = RecommendationConfidence.LOW
            note = "; ".join(reasons) if reasons else "Incomplete data"
            summary = f"Low confidence: {note}."

        return tier, summary
