"""Unit tests for individual ranking factor calculators."""

from datetime import UTC, datetime, timedelta

from app.ai.query.intent_schemas import SearchIntent
from app.opportunities.eligibility.profile_adapter import UnifiedUserFacts
from app.opportunities.eligibility.schemas import OverallEligibilityStatus
from app.opportunities.ranking.factors import (
    AcademicFitCalculator,
    DeadlineRelevanceCalculator,
    EligibilityCompletenessCalculator,
    FieldFitCalculator,
    FundingFitCalculator,
    LocationFitCalculator,
    QueryRelevanceCalculator,
    SourceQualityCalculator,
)
from app.opportunities.ranking.freshness import FreshnessCalculator
from app.opportunities.ranking.schemas import (
    PreferencePriority,
    UserPreference,
)
from app.opportunities.schemas.opportunity import (
    FundingType,
)
from tests.fixtures.ranking.dataset import (
    create_eligibility_result,
    create_opportunity,
    create_user_profile,
)


def test_academic_fit_gpa_fulfillment():
    user, _ = create_user_profile(cgpa=3.80)
    opp = create_opportunity("opp-1", "Master Scholarship", min_gpa=3.50)

    res = AcademicFitCalculator.calculate(opp, user)
    assert res.score == 1.0
    assert res.status == "HIGH"
    assert "meets or exceeds" in res.reason


def test_academic_fit_incomplete_profile():
    # User with no CGPA
    user = UnifiedUserFacts(user_id="user-empty", academic_records=[])
    opp = create_opportunity("opp-1", "Master Scholarship", min_gpa=3.50)

    res = AcademicFitCalculator.calculate(opp, user)
    assert res.score == 0.50
    assert res.status == "UNKNOWN"
    assert "incomplete" in res.reason


def test_field_fit_exact_and_taxonomy():
    user, _ = create_user_profile(field="Software Engineering")
    # CS is in same computing discipline as SE in EducationNormalizer
    opp = create_opportunity("opp-1", "AI Grant", fields=["Computer Science"])

    res = FieldFitCalculator.calculate(opp, user)
    assert res.score >= 0.80
    assert res.status == "HIGH"


def test_field_fit_mismatch():
    user, _ = create_user_profile(field="Fine Arts")
    opp = create_opportunity("opp-1", "Surgery Fellowship", fields=["Medicine", "Surgery"])

    res = FieldFitCalculator.calculate(opp, user)
    assert res.score <= 0.20
    assert res.status == "LOW"


def test_funding_fit_preferences():
    opp_full = create_opportunity(
        "opp-full", "Fully Funded DAAD", funding_type=FundingType.FULLY_FUNDED
    )
    opp_partial = create_opportunity(
        "opp-partial", "Tuition Only Grant", funding_type=FundingType.PARTIALLY_FUNDED
    )
    opp_unpaid = create_opportunity(
        "opp-unpaid", "Unpaid Training", funding_type=FundingType.UNPAID
    )

    pref_full = [
        UserPreference(category="FUNDING", value="FULLY_FUNDED", priority=PreferencePriority.HIGH)
    ]

    res_full = FundingFitCalculator.calculate(opp_full, pref_full)
    assert res_full.score == 1.0

    res_partial = FundingFitCalculator.calculate(opp_partial, pref_full)
    assert res_partial.score == 0.50

    res_unpaid = FundingFitCalculator.calculate(opp_unpaid, pref_full)
    assert res_unpaid.score <= 0.10


def test_location_fit_preferences():
    opp_de = create_opportunity("opp-de", "German Excellence", host_country="Germany")
    opp_jp = create_opportunity("opp-jp", "MEXT Scholarship", host_country="Japan")
    opp_global = create_opportunity("opp-glob", "Global Fellowship", host_country="Global")

    pref = [
        UserPreference(
            category="LOCATION", value=["Germany", "France"], priority=PreferencePriority.HIGH
        )
    ]

    res_de = LocationFitCalculator.calculate(opp_de, pref)
    assert res_de.score == 1.0

    res_jp = LocationFitCalculator.calculate(opp_jp, pref)
    assert res_jp.score == 0.40

    res_global = LocationFitCalculator.calculate(opp_global, pref)
    assert res_global.score >= 0.80


def test_deadline_relevance_scenarios():
    now = datetime.now(UTC)

    opp_rolling = create_opportunity("opp-roll", "Rolling Lab", is_rolling=True)
    res_roll = DeadlineRelevanceCalculator.calculate(opp_rolling, now=now)
    assert res_roll.score == 0.90
    assert "Rolling" in res_roll.reason

    opp_open = create_opportunity("opp-open", "Standard Grant", deadline_days=45)
    res_open = DeadlineRelevanceCalculator.calculate(opp_open, now=now)
    assert res_open.score == 1.0

    opp_urgent = create_opportunity("opp-urg", "Urgent Call", deadline_days=2)
    res_urg = DeadlineRelevanceCalculator.calculate(opp_urgent, now=now)
    assert res_urg.score == 0.70

    opp_closed = create_opportunity("opp-closed", "Past Call", deadline_days=-5)
    res_closed = DeadlineRelevanceCalculator.calculate(opp_closed, now=now)
    assert res_closed.score == 0.0
    assert "closed" in res_closed.reason


def test_freshness_calculator_decay():
    now = datetime.now(UTC)

    # Verified 2 days ago
    fresh = FreshnessCalculator.calculate(now - timedelta(days=2), now=now)
    assert fresh.score == 1.0
    assert fresh.is_fresh is True

    # Verified 45 days ago
    mid = FreshnessCalculator.calculate(now - timedelta(days=45), now=now)
    assert mid.score == 0.85

    # Verified 200 days ago
    stale = FreshnessCalculator.calculate(now - timedelta(days=200), now=now)
    assert stale.score == 0.35
    assert stale.is_stale is True

    # Explicitly flagged stale
    flagged = FreshnessCalculator.calculate(now, is_explicitly_stale=True, now=now)
    assert flagged.score == 0.20


def test_source_quality_trust_tiers():
    opp_edu = create_opportunity(
        "opp-edu", "Stanford Research", source_domain="stanford.edu", trust_score=0.98
    )
    res_edu = SourceQualityCalculator.calculate(opp_edu)
    assert res_edu.score == 1.0

    opp_blog = create_opportunity(
        "opp-blog", "Blog Aggregator", source_domain="randomscholarships.info", trust_score=0.40
    )
    res_blog = SourceQualityCalculator.calculate(opp_blog)
    assert res_blog.score <= 0.40


def test_query_relevance_matching():
    opp = create_opportunity("opp-ai", "Fully Funded AI Master in Munich", host_country="Germany")
    intent = SearchIntent(
        original_query="Fully funded AI master scholarships in Europe",
        opportunity_categories=["scholarship"],
        regions=["Europe"],
        fields=["AI"],
    )

    res = QueryRelevanceCalculator.calculate(opp, intent)
    assert res.score >= 0.75
    assert res.status == "HIGH"


def test_eligibility_completeness_states():
    res_elig = EligibilityCompletenessCalculator.calculate(
        create_eligibility_result("1", status=OverallEligibilityStatus.CLEARLY_ELIGIBLE)
    )
    assert res_elig.score == 1.0

    res_pot = EligibilityCompletenessCalculator.calculate(
        create_eligibility_result("2", status=OverallEligibilityStatus.POTENTIALLY_ELIGIBLE)
    )
    assert res_pot.score == 0.75

    res_none = EligibilityCompletenessCalculator.calculate(None)
    assert res_none.score == 0.60
    assert res_none.status == "UNKNOWN"
