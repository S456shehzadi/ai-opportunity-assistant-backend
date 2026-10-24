"""Tests for hard filters, soft preferences, and ranking guardrails."""

import pytest

from app.opportunities.eligibility.schemas import OverallEligibilityStatus
from app.opportunities.ranking.rules import HardFilterEngine, SoftPreferenceEngine
from app.opportunities.ranking.schemas import (
    ExplanationCategory,
    PreferencePriority,
    RankedOpportunity,
    StructuredRankingExplanation,
    UserPreference,
)
from app.opportunities.ranking.validators import RankingGuardrails
from app.opportunities.schemas.opportunity import FundingType
from tests.fixtures.ranking.dataset import (
    create_eligibility_result,
    create_opportunity,
)


def test_hard_filter_funding_required():
    opp_full = create_opportunity("1", "Full Scholarship", funding_type=FundingType.FULLY_FUNDED)
    opp_partial = create_opportunity(
        "2", "Partial Scholarship", funding_type=FundingType.PARTIALLY_FUNDED
    )

    pref = [
        UserPreference(
            category="FUNDING", value="FULLY_FUNDED", priority=PreferencePriority.REQUIRED
        )
    ]

    eval_full = HardFilterEngine.evaluate(opp_full, pref)
    assert eval_full.passed is True

    eval_partial = HardFilterEngine.evaluate(opp_partial, pref)
    assert eval_partial.passed is False
    assert "Excludes non-fully funded" in (eval_partial.rejection_reason or "")


def test_hard_filter_location_required():
    opp_de = create_opportunity("1", "Berlin Scholarship", host_country="Germany")
    opp_us = create_opportunity("2", "US Fellowship", host_country="United States")

    pref = [
        UserPreference(category="LOCATION", value=["Germany"], priority=PreferencePriority.REQUIRED)
    ]

    assert HardFilterEngine.evaluate(opp_de, pref).passed is True
    assert HardFilterEngine.evaluate(opp_us, pref).passed is False


def test_hard_filter_degree_required():
    opp_master = create_opportunity("1", "Master Fellowship", degree_levels=["Master's"])
    opp_phd = create_opportunity("2", "Doctoral Fellowship", degree_levels=["PhD"])

    pref = [
        UserPreference(category="DEGREE_LEVEL", value="PhD", priority=PreferencePriority.REQUIRED)
    ]

    assert HardFilterEngine.evaluate(opp_master, pref).passed is False
    assert HardFilterEngine.evaluate(opp_phd, pref).passed is True


def test_hard_filter_ineligibility_exclusion():
    opp = create_opportunity("1", "German Program", host_country="Germany")
    elig_fail = create_eligibility_result(
        "1",
        status=OverallEligibilityStatus.CLEARLY_NOT_ELIGIBLE,
        blocking=["User nationality not supported."],
    )

    # By default, ineligibles are filtered out
    eval_res = HardFilterEngine.evaluate(
        opp, preferences=[], eligibility=elig_fail, include_ineligible=False
    )
    assert eval_res.passed is False
    assert "Ineligible" in (eval_res.rejection_reason or "")

    # When requested, preserved
    eval_res_inc = HardFilterEngine.evaluate(
        opp, preferences=[], eligibility=elig_fail, include_ineligible=True
    )
    assert eval_res_inc.passed is True


def test_hard_filter_unknown_preserved():
    opp = create_opportunity("1", "Program with UNKNOWN IELTS", host_country="Germany")
    elig_unk = create_eligibility_result(
        "1",
        status=OverallEligibilityStatus.POTENTIALLY_ELIGIBLE,
        unknowns=["English test unverified"],
    )

    eval_res = HardFilterEngine.evaluate(
        opp, preferences=[], eligibility=elig_unk, include_ineligible=False
    )
    assert eval_res.passed is True


def test_soft_preference_boost_multipliers():
    assert SoftPreferenceEngine.get_boost_multiplier(PreferencePriority.HIGH) == 1.30
    assert SoftPreferenceEngine.get_boost_multiplier(PreferencePriority.MEDIUM) == 1.15
    assert SoftPreferenceEngine.get_boost_multiplier(PreferencePriority.LOW) == 1.05


def test_guardrails_detect_probabilistic_language():
    # Forbidden terms
    assert RankingGuardrails.audit_text("You have an 85% admission probability.") is True
    assert RankingGuardrails.audit_text("High chance of acceptance for your profile.") is True
    assert RankingGuardrails.audit_text("High scholarship selection probability.") is True
    assert RankingGuardrails.audit_text("High winning probability.") is True
    assert RankingGuardrails.audit_text("User will be selected.") is True

    # Permitted factual terms
    assert RankingGuardrails.audit_text("High academic and field match.") is False
    assert RankingGuardrails.audit_text("Fully funded tuition and stipend.") is False


def test_guardrails_validate_ranked_opportunity():
    ranked_opp = RankedOpportunity(
        opportunity_id="1",
        rank=1,
        relevance_score=0.92,
        eligibility_status=OverallEligibilityStatus.CLEARLY_ELIGIBLE,
        fit_summary="Computer Science matches your background.",
        positive_factors=["High academic fit."],
        negative_factors=[],
        unknown_factors=[],
        explanations=[
            StructuredRankingExplanation(
                category=ExplanationCategory.WHY_MATCHES,
                text="Computer Science degree matches.",
            )
        ],
    )

    # Valid opportunity passes
    RankingGuardrails.validate_ranked_opportunity(ranked_opp, None)

    # Ineligible override attempt: if eligibility is clearly not eligible, cannot override
    elig_ineligible = create_eligibility_result(
        "1", status=OverallEligibilityStatus.CLEARLY_NOT_ELIGIBLE
    )
    with pytest.raises(ValueError, match="Ineligible status must not be overridden"):
        RankingGuardrails.validate_ranked_opportunity(ranked_opp, elig_ineligible)

    # Forbidden term raises ValueError
    violating_opp = ranked_opp.model_copy(
        update={"fit_summary": "Estimated 90% admission probability."}
    )
    with pytest.raises(ValueError, match="Probabilistic prediction"):
        RankingGuardrails.validate_ranked_opportunity(violating_opp, None)
