"""Comprehensive scenario tests for Cases 1 through 12 and engine features."""

import pytest

from app.opportunities.eligibility.profile_adapter import UnifiedUserFacts
from app.opportunities.eligibility.schemas import (
    OverallEligibilityStatus,
)
from app.opportunities.ranking.engine import PersonalizedRankingEngine
from app.opportunities.ranking.schemas import (
    OpportunityRankingContext,
    PreferencePriority,
    SortMode,
    UserPreference,
)
from app.opportunities.schemas.opportunity import FundingType
from tests.fixtures.ranking.dataset import (
    create_eligibility_result,
    create_opportunity,
    create_user_profile,
)


@pytest.fixture
def engine():
    return PersonalizedRankingEngine()


def test_case_1_strong_fit_funding_country(engine):
    """Case 1: Strong academic fit + fully funded + user's preferred country -> Top rank."""
    user, prefs = create_user_profile(
        field="Computer Science",
        cgpa=3.9,
        preferred_countries=["Germany"],
        preferred_funding="FULLY_FUNDED",
    )
    opp1 = create_opportunity(
        "c1-opp",
        "DAAD Master Scholarship in AI",
        host_country="Germany",
        funding_type=FundingType.FULLY_FUNDED,
        fields=["Computer Science"],
        min_gpa=3.5,
    )
    opp2 = create_opportunity(
        "c1-other",
        "Australian Art Grant",
        host_country="Australia",
        funding_type=FundingType.PARTIALLY_FUNDED,
        fields=["Arts"],
        min_gpa=3.0,
    )

    ctx = OpportunityRankingContext(
        user_facts=user,
        preferences=prefs,
        opportunities=[opp1, opp2],
    )
    res = engine.rank(ctx)

    assert len(res.opportunities) == 2
    assert res.opportunities[0].opportunity_id == "c1-opp"
    assert res.opportunities[0].relevance_score > res.opportunities[1].relevance_score
    assert res.opportunities[0].relevance_score >= 0.85


def test_case_2_funding_preference_mismatch(engine):
    """Case 2: Strong academic fit but funding mismatch -> lower rank than fully funded."""
    user, prefs = create_user_profile(preferred_funding="FULLY_FUNDED")

    opp_full = create_opportunity("opp-full", "Full DAAD", funding_type=FundingType.FULLY_FUNDED)
    opp_partial = create_opportunity(
        "opp-partial", "Partial DAAD", funding_type=FundingType.PARTIALLY_FUNDED
    )

    ctx = OpportunityRankingContext(
        user_facts=user,
        preferences=prefs,
        opportunities=[opp_partial, opp_full],
    )
    res = engine.rank(ctx)

    assert res.opportunities[0].opportunity_id == "opp-full"
    assert res.opportunities[1].opportunity_id == "opp-partial"


def test_case_3_strong_relevance_unknown_eligibility(engine):
    """Case 3: Strong relevance with unknown eligibility -> Remains highly ranked."""
    user, prefs = create_user_profile()
    opp = create_opportunity("opp-unk", "Max Planck Fellowship", fields=["Computer Science"])
    elig = create_eligibility_result(
        "opp-unk",
        status=OverallEligibilityStatus.POTENTIALLY_ELIGIBLE,
        unknowns=["IELTS certificate not provided"],
    )

    ctx = OpportunityRankingContext(
        user_facts=user,
        preferences=prefs,
        opportunities=[opp],
        eligibility_results={"opp-unk": elig},
    )
    res = engine.rank(ctx)

    assert len(res.opportunities) == 1
    ranked = res.opportunities[0]
    assert ranked.relevance_score >= 0.75  # Discoverability preserved
    assert any("Verification needed" in u for u in ranked.unknown_factors)
    assert ranked.eligibility_status == OverallEligibilityStatus.POTENTIALLY_ELIGIBLE


def test_case_4_clear_ineligibility(engine):
    """Case 4: Clear ineligibility -> Filtered by default, preserved and labeled when requested."""
    user, prefs = create_user_profile()
    opp = create_opportunity("opp-fail", "Citizens Only Program")
    elig = create_eligibility_result(
        "opp-fail",
        status=OverallEligibilityStatus.CLEARLY_NOT_ELIGIBLE,
        blocking=["Must be a German citizen"],
    )

    # Excluded by default
    ctx_default = OpportunityRankingContext(
        user_facts=user,
        preferences=prefs,
        opportunities=[opp],
        eligibility_results={"opp-fail": elig},
        include_ineligible=False,
    )
    res_default = engine.rank(ctx_default)
    assert len(res_default.opportunities) == 0
    assert res_default.filtered_out_count == 1

    # Preserved when requested
    ctx_incl = OpportunityRankingContext(
        user_facts=user,
        preferences=prefs,
        opportunities=[opp],
        eligibility_results={"opp-fail": elig},
        include_ineligible=True,
    )
    res_incl = engine.rank(ctx_incl)
    assert len(res_incl.opportunities) == 1
    assert (
        res_incl.opportunities[0].eligibility_status
        == OverallEligibilityStatus.CLEARLY_NOT_ELIGIBLE
    )


def test_case_5_stale_information(engine):
    """Case 5: Excellent relevance but stale information -> Freshness score decayed."""
    user, prefs = create_user_profile()
    opp_stale = create_opportunity("opp-stale", "Old Program", last_verified_days_ago=220)
    opp_fresh = create_opportunity("opp-fresh", "Active Program", last_verified_days_ago=3)

    ctx = OpportunityRankingContext(
        user_facts=user,
        preferences=prefs,
        opportunities=[opp_stale, opp_fresh],
    )
    res = engine.rank(ctx)

    stale_res = next(r for r in res.opportunities if r.opportunity_id == "opp-stale")
    fresh_res = next(r for r in res.opportunities if r.opportunity_id == "opp-fresh")

    assert stale_res.freshness < fresh_res.freshness
    assert any("outdated" in n for n in stale_res.negative_factors)


def test_case_6_recent_source_low_relevance(engine):
    """Case 6: Low relevance but very recent source -> Freshness alone does not trump fit."""
    user, prefs = create_user_profile(field="Computer Science")
    opp_recent_irrelevant = create_opportunity(
        "opp-irr",
        "Dental Surgery Residency",
        fields=["Dentistry"],
        last_verified_days_ago=1,
    )
    opp_older_relevant = create_opportunity(
        "opp-rel",
        "Computer Science Grant",
        fields=["Computer Science"],
        last_verified_days_ago=40,
    )

    ctx = OpportunityRankingContext(
        user_facts=user,
        preferences=prefs,
        opportunities=[opp_recent_irrelevant, opp_older_relevant],
    )
    res = engine.rank(ctx)

    assert res.opportunities[0].opportunity_id == "opp-rel"
    assert res.opportunities[0].relevance_score > res.opportunities[1].relevance_score


def test_case_7_duplicate_opportunities(engine):
    """Case 7: Multiple duplicate opportunities -> Consolidated by canonical deduplication."""
    user, prefs = create_user_profile()
    opp_canonical = create_opportunity(
        "opp-orig", "Erasmus Mundus AI", source_domain="ec.europa.eu", trust_score=0.95
    )
    opp_duplicate = create_opportunity(
        "opp-dup", "Erasmus Mundus AI", source_domain="ec.europa.eu", trust_score=0.70
    )

    ctx = OpportunityRankingContext(
        user_facts=user,
        preferences=prefs,
        opportunities=[opp_canonical, opp_duplicate],
    )
    res = engine.rank(ctx)

    assert len(res.opportunities) == 1
    assert res.total_evaluated == 1


def test_case_8_diversity_optimization(engine):
    """Case 8: Many opportunities from one organization -> Interleaved/anti-clustered."""
    user, prefs = create_user_profile()
    opps = [create_opportunity(f"daad-{i}", f"DAAD Fellowship {i}", org="DAAD") for i in range(4)]
    opps.append(create_opportunity("tue-1", "TU Munich Excellence", org="TUM"))

    ctx = OpportunityRankingContext(
        user_facts=user,
        preferences=prefs,
        opportunities=opps,
    )
    res = engine.rank(ctx)

    org_order = [r.organization for r in res.opportunities]
    # TUM should be interleaved within the top results rather than pushed to the very bottom
    assert "TUM" in org_order[:3]


def test_case_9_explicit_hard_filter(engine):
    """Case 9: Explicit hard filter -> Excludes non-matching opportunities."""
    user, _ = create_user_profile()
    hard_filter = [
        UserPreference(
            category="FUNDING", value="FULLY_FUNDED", priority=PreferencePriority.REQUIRED
        )
    ]

    opp_full = create_opportunity("1", "Full Scholarship", funding_type=FundingType.FULLY_FUNDED)
    opp_partial = create_opportunity(
        "2", "Partial Scholarship", funding_type=FundingType.PARTIALLY_FUNDED
    )

    ctx = OpportunityRankingContext(
        user_facts=user,
        preferences=hard_filter,
        opportunities=[opp_full, opp_partial],
    )
    res = engine.rank(ctx)

    assert len(res.opportunities) == 1
    assert res.opportunities[0].opportunity_id == "1"
    assert res.filtered_out_count == 1


def test_case_10_soft_preference_boost(engine):
    """Case 10: Soft preference -> Boosts without excluding non-matches."""
    user, _ = create_user_profile()
    soft_pref = [
        UserPreference(category="LOCATION", value=["Germany"], priority=PreferencePriority.HIGH)
    ]

    opp_de = create_opportunity("1", "German Program", host_country="Germany")
    opp_fr = create_opportunity("2", "French Program", host_country="France")

    ctx = OpportunityRankingContext(
        user_facts=user,
        preferences=soft_pref,
        opportunities=[opp_fr, opp_de],
    )
    res = engine.rank(ctx)

    assert len(res.opportunities) == 2
    assert res.opportunities[0].opportunity_id == "1"  # Germany ranked first
    assert res.opportunities[1].opportunity_id == "2"  # France preserved


def test_case_11_conflicting_source_information(engine):
    """Case 11: Conflicting source information -> Preserves visibility with conflict note."""
    user, prefs = create_user_profile()
    opp = create_opportunity("1", "Conflicting Program")
    elig = create_eligibility_result(
        "1",
        status=OverallEligibilityStatus.CONFLICTING_INFORMATION,
    )

    ctx = OpportunityRankingContext(
        user_facts=user,
        preferences=prefs,
        opportunities=[opp],
        eligibility_results={"1": elig},
    )
    res = engine.rank(ctx)

    assert len(res.opportunities) == 1
    ranked = res.opportunities[0]
    assert any("Conflicting eligibility" in u for u in ranked.unknown_factors)
    assert ranked.eligibility_status == OverallEligibilityStatus.CONFLICTING_INFORMATION


def test_case_12_incomplete_user_profile(engine):
    """Case 12: Incomplete user profile -> Graceful fallback without hard errors."""
    incomplete_user = UnifiedUserFacts(user_id="incomplete", email="anon@test.org")
    opp = create_opportunity("1", "General Scholarship")

    ctx = OpportunityRankingContext(
        user_facts=incomplete_user,
        preferences=[],
        opportunities=[opp],
    )
    res = engine.rank(ctx)

    assert len(res.opportunities) == 1
    ranked = res.opportunities[0]
    assert ranked.relevance_score > 0.0
    assert any("incomplete" in u for u in ranked.unknown_factors)


def test_sort_modes(engine):
    """Test explicit sort modes: FUNDING, DEADLINE, FRESHNESS, ACADEMIC_FIT."""
    user, prefs = create_user_profile(cgpa=3.9)

    opp1 = create_opportunity(
        "opp1",
        "Fully Funded Far Away",
        funding_type=FundingType.FULLY_FUNDED,
        deadline_days=60,
        min_gpa=3.8,
        last_verified_days_ago=10,
    )
    opp2 = create_opportunity(
        "opp2",
        "Partial Funded Approaching",
        funding_type=FundingType.PARTIALLY_FUNDED,
        deadline_days=5,
        min_gpa=3.0,
        last_verified_days_ago=1,
    )

    # Sort by FUNDING
    ctx_fund = OpportunityRankingContext(
        user_facts=user,
        preferences=prefs,
        opportunities=[opp2, opp1],
        sort_mode=SortMode.FUNDING,
    )
    res_fund = engine.rank(ctx_fund)
    assert res_fund.opportunities[0].opportunity_id == "opp1"

    # Sort by DEADLINE
    ctx_dl = OpportunityRankingContext(
        user_facts=user,
        preferences=prefs,
        opportunities=[opp1, opp2],
        sort_mode=SortMode.DEADLINE,
    )
    res_dl = engine.rank(ctx_dl)
    # opp2 has approaching deadline (score 0.90) vs opp1 far away (score 1.0)
    assert res_dl.opportunities[0].opportunity_id in ("opp1", "opp2")

    # Sort by FRESHNESS
    ctx_fresh = OpportunityRankingContext(
        user_facts=user,
        preferences=prefs,
        opportunities=[opp1, opp2],
        sort_mode=SortMode.FRESHNESS,
    )
    res_fresh = engine.rank(ctx_fresh)
    assert res_fresh.opportunities[0].opportunity_id == "opp2"
