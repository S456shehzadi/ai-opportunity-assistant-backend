"""Validation guardrails and integrity enforcement for eligibility evaluations."""

from __future__ import annotations

from app.opportunities.eligibility.schemas import (
    OverallEligibilityStatus,
    RequirementEvaluation,
    RequirementPriority,
    RequirementStatus,
)


class EligibilityValidator:
    """Enforces zero-assumption integrity and determines overall eligibility status."""

    @classmethod
    def determine_overall_status(
        cls,
        evaluations: list[RequirementEvaluation],
        conflicts: list[str],
    ) -> tuple[
        OverallEligibilityStatus,
        list[RequirementEvaluation],
        list[RequirementEvaluation],
        list[RequirementEvaluation],
    ]:
        """Computes holistic eligibility status based on strict logical constraints.

        Returns:
            tuple of (status, blocking_reqs, unknown_reqs, conditional_reqs)
        """
        blocking: list[RequirementEvaluation] = []
        unknowns: list[RequirementEvaluation] = []
        conditionals: list[RequirementEvaluation] = []

        has_conflicts = bool(conflicts)

        for req in evaluations:
            if req.status == RequirementStatus.CONFLICTING:
                has_conflicts = True

            if req.priority == RequirementPriority.MANDATORY:
                if req.status == RequirementStatus.NO_MATCH:
                    blocking.append(req)
                elif req.status == RequirementStatus.UNKNOWN:
                    unknowns.append(req)
                elif req.status == RequirementStatus.CONDITIONAL:
                    conditionals.append(req)
            elif req.priority == RequirementPriority.IMPORTANT:
                if req.status == RequirementStatus.NO_MATCH:
                    # Non-mandatory but important (e.g. deadline expired) can also block if deadline
                    if req.requirement_type == "deadline":
                        blocking.append(req)
                elif req.status == RequirementStatus.UNKNOWN:
                    unknowns.append(req)
                elif req.status == RequirementStatus.CONDITIONAL:
                    conditionals.append(req)

        # 1. Any definitive blocking failure in mandatory requirements => CLEARLY_NOT_ELIGIBLE
        if blocking:
            return (
                OverallEligibilityStatus.CLEARLY_NOT_ELIGIBLE,
                blocking,
                unknowns,
                conditionals,
            )

        # 2. Conflicting information prevents a definitive decision => CONFLICTING_INFORMATION
        if has_conflicts:
            return (
                OverallEligibilityStatus.CONFLICTING_INFORMATION,
                blocking,
                unknowns,
                conditionals,
            )

        # 3. If any requirement requires verification => NEEDS_VERIFICATION
        if any(c.requires_verification for c in conditionals):
            return (
                OverallEligibilityStatus.NEEDS_VERIFICATION,
                blocking,
                unknowns,
                conditionals,
            )

        # 4. If any mandatory requirement is UNKNOWN => POTENTIALLY_ELIGIBLE
        if unknowns:
            return (
                OverallEligibilityStatus.POTENTIALLY_ELIGIBLE,
                blocking,
                unknowns,
                conditionals,
            )

        # 5. Conditionals that remain unresolved
        if conditionals:
            return (
                OverallEligibilityStatus.POTENTIALLY_ELIGIBLE,
                blocking,
                unknowns,
                conditionals,
            )

        # 6. All mandatory/important requirements satisfied => CLEARLY_ELIGIBLE
        return (
            OverallEligibilityStatus.CLEARLY_ELIGIBLE,
            blocking,
            unknowns,
            conditionals,
        )

    @classmethod
    def calculate_match_percentage(cls, evaluations: list[RequirementEvaluation]) -> float:
        """Calculates requirement fulfillment ratio.

        NOTE: This is strictly an internal requirement completion metric and MUST NEVER
        be displayed or interpreted as a probability of admission.
        """
        if not evaluations:
            return 0.0

        total_weight = 0.0
        earned_weight = 0.0

        for req in evaluations:
            weight = (
                3.0
                if req.priority == RequirementPriority.MANDATORY
                else 2.0
                if req.priority == RequirementPriority.IMPORTANT
                else 1.0
            )
            total_weight += weight

            if req.status == RequirementStatus.MATCH:
                earned_weight += weight
            elif req.status == RequirementStatus.CONDITIONAL:
                earned_weight += weight * 0.5
            elif req.status == RequirementStatus.UNKNOWN:
                earned_weight += weight * 0.2

        if total_weight <= 0.0:
            return 0.0

        ratio = (earned_weight / total_weight) * 100.0
        return round(min(100.0, max(0.0, ratio)), 1)
