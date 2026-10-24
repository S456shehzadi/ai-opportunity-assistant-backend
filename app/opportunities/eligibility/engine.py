"""Central AI Eligibility Engine.

Coordinates the evaluation of opportunities against normalized user profiles,
enforcing evidence-driven, explainable, uncertainty-aware decisions without admission predictions.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import Any

from app.opportunities.eligibility.confidence import ProfileCompletenessAnalyzer
from app.opportunities.eligibility.conflicts import EligibilityConflictDetector
from app.opportunities.eligibility.evaluators import (
    AcademicEvaluator,
    ApplicationFeeEvaluator,
    DeadlineEvaluator,
    ExperienceEvaluator,
    NationalityResidencyEvaluator,
    TestEvaluator,
)
from app.opportunities.eligibility.evidence import EligibilityEvidenceLinker
from app.opportunities.eligibility.profile_adapter import ProfileAdapter, UnifiedUserFacts
from app.opportunities.eligibility.requirement_adapter import (
    OpportunityRequirementItem,
    RequirementAdapter,
)
from app.opportunities.eligibility.schemas import (
    EligibilityResult,
    OverallEligibilityStatus,
    PersonalizedIntelligenceSummary,
    RequirementEvaluation,
    RequirementStatus,
)
from app.opportunities.eligibility.validators import EligibilityValidator
from app.opportunities.extraction.schemas import ExtractedOpportunity
from app.schemas.ai_profile import NormalizedAIProfile


class EligibilityReasoningModel(ABC):
    """Abstract interface for eligibility evaluation models."""

    @abstractmethod
    async def evaluate_requirement(
        self, user_facts: UnifiedUserFacts, requirement: OpportunityRequirementItem
    ) -> RequirementEvaluation:
        """Evaluates an atomic requirement against unified user facts."""
        ...


class RuleBasedEligibilityModel(EligibilityReasoningModel):
    """Deterministic, zero-hallucination rule-based evaluator."""

    async def evaluate_requirement(
        self, user_facts: UnifiedUserFacts, requirement: OpportunityRequirementItem
    ) -> RequirementEvaluation:
        req_type = requirement.requirement_type.lower()

        if req_type in ("cgpa", "minimum_cgpa", "gpa"):
            return AcademicEvaluator.evaluate_cgpa(user_facts, requirement)
        if req_type in ("percentage", "minimum_percentage"):
            return AcademicEvaluator.evaluate_percentage(user_facts, requirement)
        if req_type in ("degree_level", "degree", "education_level"):
            return AcademicEvaluator.evaluate_degree_level(user_facts, requirement)
        if req_type in ("field_of_study", "discipline", "major"):
            return AcademicEvaluator.evaluate_field_of_study(user_facts, requirement)
        if req_type in ("nationality", "citizenship", "country"):
            return NationalityResidencyEvaluator.evaluate_nationality(user_facts, requirement)
        if req_type in ("ielts", "toefl", "pte", "duolingo", "english", "english_requirement"):
            return TestEvaluator.evaluate_test(user_facts, requirement)
        if req_type in ("deadline", "application_deadline"):
            return DeadlineEvaluator.evaluate_deadline(user_facts, requirement)
        if req_type in ("work_experience", "experience", "research_experience"):
            return ExperienceEvaluator.evaluate_experience(user_facts, requirement)
        if req_type in ("fee", "application_fee"):
            return ApplicationFeeEvaluator.evaluate_fee(user_facts, requirement)

        # Fallback for generic or unclassified requirements
        return RequirementEvaluation(
            requirement_id=requirement.requirement_id,
            requirement_type=requirement.requirement_type,
            requirement_description=requirement.description,
            status=RequirementStatus.UNKNOWN,
            priority=requirement.priority,
            user_value=None,
            required_value=requirement.required_value,
            explanation=(
                f"Requirement '{requirement.description}' requires individual verification."
            ),
            opportunity_evidence=requirement.opportunity_evidence,
        )


class EligibilityEngine:
    """Orchestrates comprehensive opportunity eligibility matching and personalized intelligence."""

    ENGINE_VERSION = "1.0.0"

    def __init__(
        self,
        reasoning_model: EligibilityReasoningModel | None = None,
    ):
        self.model = reasoning_model or RuleBasedEligibilityModel()
        self._cache: dict[str, EligibilityResult] = {}

    async def evaluate(
        self,
        profile: NormalizedAIProfile | Any,
        opportunity: ExtractedOpportunity | Any,
        use_cache: bool = True,
    ) -> EligibilityResult:
        """Evaluates an opportunity against a user profile."""
        # Adapt inputs to canonical representations
        user_facts = ProfileAdapter.adapt(profile)
        requirements = RequirementAdapter.adapt(opportunity)

        if isinstance(opportunity, dict):
            opp_id = opportunity.get("id") or opportunity.get("canonical_key") or "opp_unknown"
            opp_version = opportunity.get("version") or opportunity.get("opportunity_version", 1)
            raw_opp_conflicts = opportunity.get("conflicts_detected", []) or opportunity.get(
                "conflicts", []
            )
        else:
            opp_id = getattr(
                opportunity, "id", getattr(opportunity, "canonical_key", "opp_unknown")
            )
            opp_version = getattr(
                opportunity, "version", getattr(opportunity, "opportunity_version", 1)
            )
            raw_opp_conflicts = getattr(opportunity, "conflicts_detected", []) or getattr(
                opportunity, "conflicts", []
            )

        if isinstance(profile, dict):
            profile_version = profile.get("version") or profile.get("profile_version", 1)
        else:
            profile_version = getattr(profile, "version", getattr(profile, "profile_version", 1))

        cache_key = (
            f"{user_facts.user_id}_v{profile_version}:{opp_id}_v{opp_version}:{self.ENGINE_VERSION}"
        )
        if use_cache and cache_key in self._cache:
            return self._cache[cache_key]

        # 1. Detect user-side and opportunity-side conflicts
        user_conflicts = EligibilityConflictDetector.detect_user_conflicts(
            user_facts.academic_records
        )
        opp_conflicts = EligibilityConflictDetector.detect_opportunity_conflicts(raw_opp_conflicts)

        all_conflict_notes = [c.reasoning for c in user_conflicts + opp_conflicts]

        # 2. Evaluate each atomic requirement
        evaluations: list[RequirementEvaluation] = []
        for req in requirements:
            # If requirement references a field with unresolved conflict, mark CONFLICTING
            is_conflicting = any(
                req.requirement_type.lower() in c.field_name.lower() for c in user_conflicts
            )
            if is_conflicting:
                ev = RequirementEvaluation(
                    requirement_id=req.requirement_id,
                    requirement_type=req.requirement_type,
                    requirement_description=req.description,
                    status=RequirementStatus.CONFLICTING,
                    priority=req.priority,
                    user_value="Conflicting user records",
                    required_value=req.required_value,
                    explanation="Conflicting profile records prevent a definitive determination.",
                    opportunity_evidence=req.opportunity_evidence,
                    requires_verification=True,
                )
            else:
                ev = await self.model.evaluate_requirement(user_facts, req)
            evaluations.append(ev)

        # 3. Determine overall status and blocking requirements
        overall_status, blocking, unknowns, conditionals = (
            EligibilityValidator.determine_overall_status(evaluations, all_conflict_notes)
        )

        # 4. Calculate internal match percentage (never admission probability)
        match_percentage = EligibilityValidator.calculate_match_percentage(evaluations)

        # 5. Build personalized intelligence summary
        missing_fields, prioritized_missing = (
            ProfileCompletenessAnalyzer.analyze_missing_information(
                evaluations, user_facts.model_dump()
            )
        )

        satisfied = [
            r.requirement_description for r in evaluations if r.status == RequirementStatus.MATCH
        ]
        unsatisfied = [
            r.requirement_description for r in evaluations if r.status == RequirementStatus.NO_MATCH
        ]
        unknown_desc = [
            r.requirement_description for r in evaluations if r.status == RequirementStatus.UNKNOWN
        ]
        cond_desc = [
            r.requirement_description
            for r in evaluations
            if r.status == RequirementStatus.CONDITIONAL
        ]

        potential_issues: list[str] = []
        for r in evaluations:
            if r.requirement_type == "deadline" and r.status == RequirementStatus.MATCH:
                potential_issues.append("Application deadline is active. Verify closing date.")
            if r.requirement_type == "application_fee" and "FEE" in str(r.required_value):
                potential_issues.append("Application fee may be required.")

        intelligence = PersonalizedIntelligenceSummary(
            satisfied_requirements=satisfied,
            unsatisfied_requirements=unsatisfied,
            unknown_requirements=unknown_desc,
            conditional_requirements=cond_desc,
            potential_issues=potential_issues,
            missing_profile_fields=missing_fields,
            prioritized_missing_information=prioritized_missing,
        )

        # 6. Synthesize concise plain-text explanation
        synthesis = self._synthesize_explanation(
            overall_status, satisfied, unsatisfied, unknown_desc
        )

        # 7. Compile complete evidence audit trail
        evidence_trail = EligibilityEvidenceLinker.compile_evidence_audit_trail(evaluations)

        result = EligibilityResult(
            opportunity_id=str(opp_id),
            user_id=user_facts.user_id,
            overall_status=overall_status,
            match_percentage=match_percentage,
            requirements=evaluations,
            blocking_requirements=blocking,
            unknown_requirements=unknowns,
            conditional_requirements=conditionals,
            conflicts=all_conflict_notes,
            evidence=evidence_trail,
            explanation=synthesis,
            personalized_intelligence=intelligence,
            engine_version=self.ENGINE_VERSION,
            profile_version=profile_version,
            opportunity_version=opp_version,
            cache_key=cache_key,
        )

        if use_cache:
            self._cache[cache_key] = result

        return result

    async def evaluate_batch(
        self,
        profile: NormalizedAIProfile | Any,
        opportunities: list[Any],
        max_concurrency: int = 5,
        use_cache: bool = True,
    ) -> list[EligibilityResult]:
        """Evaluates multiple opportunities against a single profile with controlled concurrency."""
        sem = asyncio.Semaphore(max_concurrency)

        async def _eval_one(opp: Any) -> EligibilityResult:
            async with sem:
                return await self.evaluate(profile, opp, use_cache=use_cache)

        tasks = [_eval_one(opp) for opp in opportunities]
        return await asyncio.gather(*tasks)

    def _synthesize_explanation(
        self,
        overall_status: OverallEligibilityStatus,
        satisfied: list[str],
        unsatisfied: list[str],
        unknowns: list[str],
    ) -> str:
        if overall_status == OverallEligibilityStatus.CLEARLY_ELIGIBLE:
            return f"You satisfy all {len(satisfied)} stated mandatory requirements."
        if overall_status == OverallEligibilityStatus.CLEARLY_NOT_ELIGIBLE:
            top_unsatisfied = ", ".join(unsatisfied[:2])
            return (
                f"Your profile does not satisfy {len(unsatisfied)} mandatory requirement(s): "
                f"{top_unsatisfied}."
            )
        if overall_status == OverallEligibilityStatus.POTENTIALLY_ELIGIBLE:
            top_unknowns = ", ".join(unknowns[:2])
            return (
                f"You satisfy {len(satisfied)} requirement(s), but {len(unknowns)} requirement(s) "
                f"cannot be confirmed without additional profile details: {top_unknowns}."
            )
        if overall_status == OverallEligibilityStatus.NEEDS_VERIFICATION:
            return (
                "Some requirements involve conditional waivers or unverified entries that "
                "require your review."
            )
        if overall_status == OverallEligibilityStatus.CONFLICTING_INFORMATION:
            return (
                "Contradictory source or profile data prevents a definitive eligibility "
                "determination."
            )
        return "Eligibility evaluation completed."
