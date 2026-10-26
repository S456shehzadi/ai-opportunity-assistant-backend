"""Comprehensive verification of Prompt 28:
Opportunity Preferences, Hard vs Soft Constraints, Decision Support, and Ranking Integration.
"""

from datetime import UTC, datetime
import uuid
import pytest
from httpx import AsyncClient

from app.main import app
from app.models.profile import UserPreferences
from app.schemas.profile import UserPreferencesBase, UserPreferencesUpdate
from app.opportunities.ranking.rules import HardFilterEngine
from app.opportunities.ranking.factors import UserPreferenceFitCalculator
from app.opportunities.ranking.engine import PersonalizedRankingEngine
from app.opportunities.ranking.schemas import (
    OpportunityRankingContext,
    PreferencePriority,
    RankingFactorType,
    UserPreference,
)


def test_user_preferences_schema_validation_and_defaults() -> None:
    """Verifies that UserPreferencesBase supports all 10 preference dimensions with typed defaults."""
    prefs = UserPreferencesBase(
        preferred_opportunity_categories=["Scholarship", "Research Grant", "Internship"],
        target_degree_levels=["Bachelor's / Undergraduate", "Master's Degree"],
        preferred_fields=["Computer Science", "Artificial Intelligence"],
        preferred_countries=["Germany", "United Kingdom"],
        preferred_regions=["Europe"],
        excluded_countries=["Country X"],
        willing_to_relocate=True,
        funding_preference="Fully Funded",
        funding_types=["Fully funded", "Full tuition", "Living stipend"],
        funding_priorities=["Tuition fees", "Monthly living allowance", "Health insurance"],
        max_annual_tuition=5000.0,
        financial_currency="EUR",
        requires_no_application_fee=True,
        requires_no_ielts=False,
        language_preferences=["English", "German"],
        language_test_status={"IELTS": "Willing to take", "Duolingo": "Completed"},
        admission_test_status={"GRE": "Preparing", "SAT": "Not applicable"},
        study_formats=["In-person", "Hybrid"],
        duration_preferences=["1-2 years", "More than 2 years"],
        preferred_start_terms=["Fall 2026", "Spring 2027"],
        career_priorities=["Strong financial support", "High academic relevance", "Research opportunities"],
        hard_constraints=["must_be_fully_funded", "must_have_no_fee"],
    )

    assert len(prefs.preferred_opportunity_categories) == 3
    assert prefs.financial_currency == "EUR"
    assert prefs.max_annual_tuition == 5000.0
    assert prefs.requires_no_application_fee is True
    assert prefs.language_test_status["Duolingo"] == "Completed"
    assert "Country X" in prefs.excluded_countries
    assert "must_be_fully_funded" in prefs.hard_constraints


@pytest.mark.asyncio
async def test_preferences_api_crud_endpoints(client: AsyncClient) -> None:
    """Verifies GET, PUT, and PATCH endpoints for /api/v1/profile/preferences."""
    # 1. Update preferences via PUT
    put_payload = {
        "preferred_opportunity_categories": ["Scholarship", "Fellowship"],
        "target_degree_levels": ["Master's Degree"],
        "preferred_countries": ["Germany", "Sweden"],
        "excluded_countries": ["North Korea"],
        "funding_types": ["Fully funded"],
        "funding_priorities": ["Tuition", "Living allowance"],
        "financial_currency": "USD",
        "requires_no_application_fee": True,
        "requires_no_ielts": True,
        "study_formats": ["In-person", "Online"],
        "duration_preferences": ["1-2 years"],
        "career_priorities": ["Strong financial support"],
        "hard_constraints": ["must_be_fully_funded"],
    }
    put_res = await client.put("/api/v1/profile/preferences", json=put_payload)
    assert put_res.status_code == 200
    data = put_res.json()
    assert data["financial_currency"] == "USD"
    assert data["requires_no_application_fee"] is True
    assert data["requires_no_ielts"] is True
    assert "Germany" in data["preferred_countries"]
    assert "North Korea" in data["excluded_countries"]

    # 2. Get preferences via GET
    get_res = await client.get("/api/v1/profile/preferences")
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert get_data["financial_currency"] == "USD"
    assert get_data["requires_no_application_fee"] is True

    # 3. Patch specific field via PATCH
    patch_res = await client.patch(
        "/api/v1/profile/preferences",
        json={"financial_currency": "EUR", "max_annual_tuition": 2500.0},
    )
    assert patch_res.status_code == 200
    patched_data = patch_res.json()
    assert patched_data["financial_currency"] == "EUR"
    assert patched_data["max_annual_tuition"] == 2500.0
    # Prior fields retained
    assert patched_data["requires_no_application_fee"] is True


def test_hard_filter_engine_enforces_strict_constraints() -> None:
    """Verifies HardFilterEngine enforces REQUIRED preferences without eliminating soft options."""
    class MockOpp:
        title = "Global Technology Program"
        category = "scholarship"
        host_country = "France"
        funding_type = "partial"
        application_fee = 75.0
        is_rolling = True
        is_ielts_mandatory = True
        study_format = "in_person"

    opp = MockOpp()

    # 1. Soft preference for fully funded does NOT reject
    soft_prefs = [
        UserPreference(category="FUNDING", value="FULLY_FUNDED", priority=PreferencePriority.HIGH),
    ]
    eval_soft = HardFilterEngine.evaluate(opp, soft_prefs)
    assert eval_soft.passed is True

    # 2. Hard constraint (REQUIRED) for fully funded REJECTS partial
    hard_funding_prefs = [
        UserPreference(category="FUNDING", value="FULLY_FUNDED", priority=PreferencePriority.REQUIRED),
    ]
    eval_hard_fund = HardFilterEngine.evaluate(opp, hard_funding_prefs)
    assert eval_hard_fund.passed is False
    assert eval_hard_fund.filter_category == "FUNDING"

    # 3. Hard constraint for Excluded Country REJECTS
    hard_exclude_prefs = [
        UserPreference(category="EXCLUDED_COUNTRIES", value=["France", "Russia"], priority=PreferencePriority.REQUIRED),
    ]
    eval_exclude = HardFilterEngine.evaluate(opp, hard_exclude_prefs)
    assert eval_exclude.passed is False
    assert eval_exclude.filter_category == "EXCLUDED_COUNTRY"

    # 4. Hard constraint for No Application Fee REJECTS fee > 0
    hard_fee_prefs = [
        UserPreference(category="NO_APPLICATION_FEE", value=True, priority=PreferencePriority.REQUIRED),
    ]
    eval_fee = HardFilterEngine.evaluate(opp, hard_fee_prefs)
    assert eval_fee.passed is False
    assert eval_fee.filter_category == "APPLICATION_FEE"

    # 5. Hard constraint for No IELTS REJECTS when IELTS is mandatory
    hard_ielts_prefs = [
        UserPreference(category="NO_IELTS", value=True, priority=PreferencePriority.REQUIRED),
    ]
    eval_ielts = HardFilterEngine.evaluate(opp, hard_ielts_prefs)
    assert eval_ielts.passed is False
    assert eval_ielts.filter_category == "LANGUAGE_TEST"


def test_user_preference_fit_calculator_scoring() -> None:
    """Verifies UserPreferenceFitCalculator returns multi-attribute scores and transparent reasons."""
    class MockOpp:
        title = "DAAD Master Scholarship"
        category = "scholarship"
        host_country = "Germany"
        funding_type = "fully_funded"
        application_fee = 0.0

    opp = MockOpp()

    matching_prefs = [
        UserPreference(category="LOCATION", value=["Germany", "Austria"], priority=PreferencePriority.HIGH),
        UserPreference(category="CATEGORY", value=["scholarship"], priority=PreferencePriority.HIGH),
        UserPreference(category="FUNDING", value="FULLY_FUNDED", priority=PreferencePriority.HIGH),
        UserPreference(category="NO_APPLICATION_FEE", value=True, priority=PreferencePriority.MEDIUM),
    ]

    fit = UserPreferenceFitCalculator.calculate(opp, matching_prefs)
    assert fit.score == 1.0
    assert fit.status == "HIGH"
    assert "Destination match (Germany)" in fit.reason


def test_ranking_engine_incorporates_user_preference_fit() -> None:
    """Verifies PersonalizedRankingEngine outputs USER_PREFERENCE_FIT in the factor breakdown."""
    engine = PersonalizedRankingEngine()

    class MockCandidate:
        id = "pref-cand-1"
        title = "Erasmus Mundus Master in AI"
        category = "scholarship"
        description = "Fully funded European joint master program in machine learning."
        organization = "European Commission"
        host_country = "Global"
        funding_type = "fully_funded"
        is_rolling = False
        source_domain = "europa.eu"
        trust_score = 0.98

    prefs = [
        UserPreference(category="FUNDING", value="FULLY_FUNDED", priority=PreferencePriority.HIGH),
        UserPreference(category="CATEGORY", value=["scholarship"], priority=PreferencePriority.HIGH),
    ]

    context = OpportunityRankingContext(
        opportunities=[MockCandidate()],
        preferences=prefs,
    )

    result = engine.rank(context)
    assert len(result.opportunities) == 1
    ranked = result.opportunities[0]
    assert "user_preference_fit" in ranked.ranking_factors or RankingFactorType.USER_PREFERENCE_FIT.value in ranked.ranking_factors
    factor_detail = ranked.ranking_factors.get("user_preference_fit") or ranked.ranking_factors.get(RankingFactorType.USER_PREFERENCE_FIT.value)
    assert factor_detail is not None
    assert factor_detail.score >= 0.80
