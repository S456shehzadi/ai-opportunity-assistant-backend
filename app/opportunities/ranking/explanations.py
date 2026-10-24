"""Structured explanation builder for personalized ranking transparency."""

from __future__ import annotations

from typing import Any

from app.opportunities.eligibility.profile_adapter import UnifiedUserFacts
from app.opportunities.eligibility.schemas import EligibilityResult, OverallEligibilityStatus
from app.opportunities.ranking.factors import (
    get_opp_funding_type,
    get_opp_org,
    get_opp_title,
)
from app.opportunities.ranking.schemas import (
    ExplanationCategory,
    RankingFactorDetail,
    RankingFactorType,
    StructuredRankingExplanation,
)


class RankingExplanationBuilder:
    """Constructs auditable, user-friendly explanations for rank placement."""

    @classmethod
    def build_explanations(
        cls,
        opp: Any,
        factors: dict[RankingFactorType, RankingFactorDetail],
        eligibility: EligibilityResult | None,
        user_facts: UnifiedUserFacts | None = None,
    ) -> tuple[str, list[str], list[str], list[str], list[StructuredRankingExplanation]]:
        """Builds fit_summary, positive_factors, negative_factors, and structured notes."""
        positive_factors: list[str] = []
        negative_factors: list[str] = []
        unknown_factors: list[str] = []
        structured_notes: list[StructuredRankingExplanation] = []

        # 1. Academic & Field Fit
        field_fac = factors.get(RankingFactorType.FIELD_FIT)
        if field_fac:
            if field_fac.score >= 0.75:
                positive_factors.append(field_fac.reason)
                structured_notes.append(
                    StructuredRankingExplanation(
                        category=ExplanationCategory.WHY_MATCHES,
                        text=field_fac.reason,
                    )
                )
            elif field_fac.status == "UNKNOWN":
                unknown_factors.append(field_fac.reason)
            elif field_fac.score < 0.40:
                negative_factors.append(field_fac.reason)

        degree_fac = factors.get(RankingFactorType.DEGREE_LEVEL_FIT)
        if degree_fac:
            if degree_fac.score >= 0.85:
                positive_factors.append(degree_fac.reason)
            elif degree_fac.score < 0.40:
                negative_factors.append(degree_fac.reason)

        academic_fac = factors.get(RankingFactorType.ACADEMIC_FIT)
        if academic_fac:
            if academic_fac.score >= 0.85 and "No minimum GPA" not in academic_fac.reason:
                positive_factors.append(academic_fac.reason)
            elif academic_fac.status == "UNKNOWN":
                unknown_factors.append(academic_fac.reason)
            elif academic_fac.score < 0.40:
                negative_factors.append(academic_fac.reason)

        # 2. Funding Fit
        funding_fac = factors.get(RankingFactorType.FUNDING_FIT)
        if funding_fac:
            if funding_fac.score >= 0.85:
                positive_factors.append(funding_fac.reason)
                structured_notes.append(
                    StructuredRankingExplanation(
                        category=ExplanationCategory.FUNDING_NOTE,
                        text=funding_fac.reason,
                    )
                )
            elif funding_fac.status == "UNKNOWN":
                unknown_factors.append(funding_fac.reason)
            elif funding_fac.score <= 0.40:
                negative_factors.append(funding_fac.reason)
                structured_notes.append(
                    StructuredRankingExplanation(
                        category=ExplanationCategory.FUNDING_NOTE,
                        text=funding_fac.reason,
                    )
                )

        # 3. Location Fit
        loc_fac = factors.get(RankingFactorType.LOCATION_FIT)
        if loc_fac:
            if loc_fac.score >= 0.85:
                positive_factors.append(loc_fac.reason)
            elif loc_fac.score < 0.50:
                negative_factors.append(loc_fac.reason)

        # 4. Deadline Relevance
        dl_fac = factors.get(RankingFactorType.DEADLINE_RELEVANCE)
        if dl_fac:
            structured_notes.append(
                StructuredRankingExplanation(
                    category=ExplanationCategory.DEADLINE_NOTE,
                    text=dl_fac.reason,
                )
            )
            if dl_fac.score == 0.0:
                negative_factors.append(dl_fac.reason)
            elif dl_fac.status == "UNKNOWN":
                unknown_factors.append(dl_fac.reason)

        # 5. Eligibility Insights
        if eligibility:
            if eligibility.overall_status == OverallEligibilityStatus.CLEARLY_ELIGIBLE:
                positive_factors.append("Satisfies all mandatory eligibility criteria.")
            elif eligibility.overall_status == OverallEligibilityStatus.POTENTIALLY_ELIGIBLE:
                for req in eligibility.unknown_requirements[:2]:
                    reason = (
                        req.explanation
                        if isinstance(req.explanation, str)
                        else getattr(req.explanation, "text", req.requirement_type)
                    )
                    unknown_factors.append(f"Verification needed: {reason}")
                    structured_notes.append(
                        StructuredRankingExplanation(
                            category=ExplanationCategory.WHAT_TO_VERIFY,
                            text=f"Verification needed: {reason}",
                        )
                    )
            elif eligibility.overall_status == OverallEligibilityStatus.NEEDS_VERIFICATION:
                structured_notes.append(
                    StructuredRankingExplanation(
                        category=ExplanationCategory.WHAT_TO_VERIFY,
                        text=eligibility.explanation,
                    )
                )
                unknown_factors.append(eligibility.explanation)
            elif eligibility.overall_status == OverallEligibilityStatus.CONFLICTING_INFORMATION:
                structured_notes.append(
                    StructuredRankingExplanation(
                        category=ExplanationCategory.SOURCE_NOTE,
                        text=(
                            "Conflicting eligibility details detected across sources; "
                            "manual verification advised."
                        ),
                    )
                )
                unknown_factors.append(
                    "Conflicting eligibility information detected across sources."
                )
            elif eligibility.overall_status == OverallEligibilityStatus.CLEARLY_NOT_ELIGIBLE:
                negative_factors.append(eligibility.explanation)

        # 6. Source Quality & Freshness
        source_fac = factors.get(RankingFactorType.SOURCE_QUALITY)
        if source_fac and source_fac.score >= 0.85:
            structured_notes.append(
                StructuredRankingExplanation(
                    category=ExplanationCategory.SOURCE_NOTE,
                    text=source_fac.reason,
                )
            )

        fresh_fac = factors.get(RankingFactorType.FRESHNESS)
        if fresh_fac and fresh_fac.score <= 0.40:
            negative_factors.append(
                "Listing information may be outdated; verify current cycle dates."
            )
            structured_notes.append(
                StructuredRankingExplanation(
                    category=ExplanationCategory.WARNING_NOTE,
                    text="Listing information may be outdated; verify current cycle dates.",
                )
            )

        # Synthesize concise fit summary
        title = get_opp_title(opp)
        org = get_opp_org(opp)
        funding = get_opp_funding_type(opp).replace("_", " ")

        if positive_factors:
            primary_pos = positive_factors[0]
            fit_summary = f"{title} by {org}: {primary_pos}"
        else:
            fit_summary = f"{title} by {org} ({funding.title()})."

        return (
            fit_summary,
            positive_factors,
            negative_factors,
            unknown_factors,
            structured_notes,
        )
