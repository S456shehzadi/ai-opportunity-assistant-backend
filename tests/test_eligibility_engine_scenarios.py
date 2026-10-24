"""End-to-end scenario test suite for EligibilityEngine.

Tests Scenarios A through F, versioned caching, and strict integrity invariants:
- Scenario A: Clearly matching profile & opportunity -> CLEARLY_ELIGIBLE
- Scenario B: Definitive mismatch in mandatory criterion -> CLEARLY_NOT_ELIGIBLE
- Scenario C: Missing test score -> POTENTIALLY_ELIGIBLE (Zero assumptions: never NO_MATCH)
- Scenario D: English-medium degree waiver -> MATCH via waiver
- Scenario E: Contradictory records -> CONFLICTING_INFORMATION
- Scenario F: Missing demographic entry -> UNKNOWN (never inferred)
- Cache & Versioning: Proper invalidation on version increments
"""

from __future__ import annotations

import pytest

from app.opportunities.eligibility.engine import EligibilityEngine
from app.opportunities.eligibility.schemas import (
    OverallEligibilityStatus,
    RequirementStatus,
)
from tests.fixtures.eligibility.dataset import (
    OPPORTUNITY_A_STANDARD_DICT,
    OPPORTUNITY_B_STRICT_CGPA_DICT,
    OPPORTUNITY_C_MANDATORY_IELTS_DICT,
    OPPORTUNITY_D_WAIVER_ALLOWED_DICT,
    OPPORTUNITY_E_CONFLICTING_DICT,
    OPPORTUNITY_F_RESTRICTED_NATIONALITY_DICT,
    USER_PROFILE_A_DICT,
    USER_PROFILE_B_LOW_CGPA_DICT,
    USER_PROFILE_C_MISSING_TEST_DICT,
    USER_PROFILE_D_CONDITIONAL_EMI_DICT,
    USER_PROFILE_E_CONFLICTING_DICT,
    USER_PROFILE_F_UNKNOWN_NATIONALITY_DICT,
    build_extracted_opportunity_a,
    build_normalized_profile_a,
)


@pytest.fixture
def engine() -> EligibilityEngine:
    return EligibilityEngine()


class TestEligibilityEngineScenarios:
    """End-to-end tests for all core eligibility scenarios."""

    @pytest.mark.asyncio
    async def test_scenario_a_clearly_eligible_dict(self, engine: EligibilityEngine):
        """Scenario A: Ahmed meets all academic, test, demographic, and deadline criteria."""
        result = await engine.evaluate(
            profile=USER_PROFILE_A_DICT,
            opportunity=OPPORTUNITY_A_STANDARD_DICT,
        )

        assert result.overall_status == OverallEligibilityStatus.CLEARLY_ELIGIBLE
        assert result.match_percentage >= 95.0
        assert len(result.blocking_requirements) == 0
        assert len(result.unknown_requirements) == 0
        assert len(result.evidence) > 0
        assert "satisfy all" in result.explanation.lower()

    @pytest.mark.asyncio
    async def test_scenario_a_with_pydantic_models(self, engine: EligibilityEngine):
        """Scenario A using full Pydantic NormalizedAIProfile and ExtractedOpportunity models."""
        profile = build_normalized_profile_a()
        opp = build_extracted_opportunity_a()

        result = await engine.evaluate(profile=profile, opportunity=opp)
        assert result.overall_status == OverallEligibilityStatus.CLEARLY_ELIGIBLE
        assert result.match_percentage >= 90.0

    @pytest.mark.asyncio
    async def test_scenario_b_clearly_not_eligible(self, engine: EligibilityEngine):
        """Scenario B: User CGPA is 2.50, but opportunity requires minimum 3.20."""
        result = await engine.evaluate(
            profile=USER_PROFILE_B_LOW_CGPA_DICT,
            opportunity=OPPORTUNITY_B_STRICT_CGPA_DICT,
        )

        assert result.overall_status == OverallEligibilityStatus.CLEARLY_NOT_ELIGIBLE
        assert len(result.blocking_requirements) > 0

        # Blocking requirement must be CGPA
        cgpa_blocking = [b for b in result.blocking_requirements if b.requirement_type == "cgpa"]
        assert len(cgpa_blocking) == 1
        assert cgpa_blocking[0].status == RequirementStatus.NO_MATCH
        assert cgpa_blocking[0].user_value == 2.50
        assert cgpa_blocking[0].required_value == 3.20
        assert "does not satisfy" in result.explanation.lower()

    @pytest.mark.asyncio
    async def test_scenario_c_missing_data_is_potentially_eligible(self, engine: EligibilityEngine):
        """Scenario C: IELTS is required (7.0), but user profile has no test declared.

        STRICT INVARIANT: Must evaluate to POTENTIALLY_ELIGIBLE, NEVER CLEARLY_NOT_ELIGIBLE.
        """
        result = await engine.evaluate(
            profile=USER_PROFILE_C_MISSING_TEST_DICT,
            opportunity=OPPORTUNITY_C_MANDATORY_IELTS_DICT,
        )

        assert result.overall_status == OverallEligibilityStatus.POTENTIALLY_ELIGIBLE
        assert len(result.blocking_requirements) == 0
        assert len(result.unknown_requirements) > 0

        # Check that missing test is highlighted in prioritized missing info
        assert any(
            "ielts" in f.lower() or "test" in f.lower()
            for f in result.personalized_intelligence.prioritized_missing_information
        )
        assert "cannot be confirmed" in result.explanation.lower()

    @pytest.mark.asyncio
    async def test_scenario_d_conditional_waiver_match(self, engine: EligibilityEngine):
        """Scenario D: User has no IELTS test score, but holds a verified English-medium degree.

        Opportunity permits EMI waivers -> requirement should be satisfied via waiver.
        """
        result = await engine.evaluate(
            profile=USER_PROFILE_D_CONDITIONAL_EMI_DICT,
            opportunity=OPPORTUNITY_D_WAIVER_ALLOWED_DICT,
        )

        # IELTS requirement should be MATCH due to waiver
        ielts_req = next((r for r in result.requirements if r.requirement_type == "ielts"), None)
        assert ielts_req is not None
        assert ielts_req.status == RequirementStatus.MATCH
        assert "waived" in ielts_req.explanation.lower()
        assert result.overall_status == OverallEligibilityStatus.CLEARLY_ELIGIBLE

    @pytest.mark.asyncio
    async def test_scenario_d_conditional_waiver_needs_verification_when_emi_unknown(
        self, engine: EligibilityEngine
    ):
        """Opportunity allows waiver, but profile has no EMI -> NEEDS_VERIFICATION."""
        profile = dict(USER_PROFILE_C_MISSING_TEST_DICT)
        profile["has_english_medium_degree"] = False

        result = await engine.evaluate(
            profile=profile,
            opportunity=OPPORTUNITY_D_WAIVER_ALLOWED_DICT,
        )

        assert result.overall_status in (
            OverallEligibilityStatus.NEEDS_VERIFICATION,
            OverallEligibilityStatus.POTENTIALLY_ELIGIBLE,
        )
        ielts_req = next((r for r in result.requirements if r.requirement_type == "ielts"), None)
        assert ielts_req is not None
        assert ielts_req.status == RequirementStatus.CONDITIONAL
        assert ielts_req.requires_verification is True

    @pytest.mark.asyncio
    async def test_scenario_e_conflicting_information(self, engine: EligibilityEngine):
        """Scenario E: Conflicting academic performance records or conflicting opportunity data."""
        # 1. User profile conflicts
        result_user_conflict = await engine.evaluate(
            profile=USER_PROFILE_E_CONFLICTING_DICT,
            opportunity=OPPORTUNITY_A_STANDARD_DICT,
        )
        assert (
            result_user_conflict.overall_status == OverallEligibilityStatus.CONFLICTING_INFORMATION
        )
        assert len(result_user_conflict.conflicts) > 0

        # 2. Opportunity source conflicts
        result_opp_conflict = await engine.evaluate(
            profile=USER_PROFILE_A_DICT,
            opportunity=OPPORTUNITY_E_CONFLICTING_DICT,
        )
        assert (
            result_opp_conflict.overall_status == OverallEligibilityStatus.CONFLICTING_INFORMATION
        )
        assert len(result_opp_conflict.conflicts) > 0

    @pytest.mark.asyncio
    async def test_scenario_f_unknown_nationality_never_assumed(self, engine: EligibilityEngine):
        """Scenario F: User nationality not declared; opportunity requires specific nationalities.

        STRICT INVARIANT: Must evaluate to UNKNOWN, never inferred or assumed.
        """
        result = await engine.evaluate(
            profile=USER_PROFILE_F_UNKNOWN_NATIONALITY_DICT,
            opportunity=OPPORTUNITY_F_RESTRICTED_NATIONALITY_DICT,
        )

        nat_req = next(
            (r for r in result.requirements if r.requirement_type == "nationality"), None
        )
        assert nat_req is not None
        assert nat_req.status == RequirementStatus.UNKNOWN
        assert result.overall_status == OverallEligibilityStatus.POTENTIALLY_ELIGIBLE

    @pytest.mark.asyncio
    async def test_caching_and_version_invalidation(self, engine: EligibilityEngine):
        """Tests that engine caches evaluations and invalidates on version change."""
        profile = dict(USER_PROFILE_A_DICT)
        profile["version"] = 1
        opp = dict(OPPORTUNITY_A_STANDARD_DICT)
        opp["version"] = 1

        res1 = await engine.evaluate(profile, opp, use_cache=True)
        assert res1.cache_key in engine._cache

        # Modify opportunity without changing version: cache hit returns previous result
        opp_mod = dict(opp)
        opp_mod["minimum_cgpa"] = 3.99  # Would fail if re-evaluated
        res2 = await engine.evaluate(profile, opp_mod, use_cache=True)
        assert res2.overall_status == res1.overall_status

        # Increment opportunity version: cache miss recalculates with new criteria
        opp_mod["version"] = 2
        res3 = await engine.evaluate(profile, opp_mod, use_cache=True)
        assert res3.overall_status == OverallEligibilityStatus.CLEARLY_NOT_ELIGIBLE
        assert res3.cache_key != res1.cache_key

    @pytest.mark.asyncio
    async def test_batch_evaluation_concurrency(self, engine: EligibilityEngine):
        """Tests batch evaluation of multiple opportunities against one profile."""
        opportunities = [
            OPPORTUNITY_A_STANDARD_DICT,
            OPPORTUNITY_B_STRICT_CGPA_DICT,
            OPPORTUNITY_D_WAIVER_ALLOWED_DICT,
        ]
        results = await engine.evaluate_batch(
            profile=USER_PROFILE_A_DICT,
            opportunities=opportunities,
            max_concurrency=2,
        )
        assert len(results) == 3
        assert results[0].opportunity_id == str(OPPORTUNITY_A_STANDARD_DICT["id"])
        assert results[1].opportunity_id == str(OPPORTUNITY_B_STRICT_CGPA_DICT["id"])
