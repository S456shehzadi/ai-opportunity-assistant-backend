from datetime import UTC, datetime, timedelta
import uuid
import pytest
from app.models.opportunity import Opportunity, OpportunityCategory, OpportunityStatus
from app.opportunities.ranking.schemas import PreferencePriority, RankingFactorType, UserPreference
from app.opportunities.ranking.factors import LocationFitCalculator
from app.opportunities.ranking.rules import HardFilterEngine
from app.schemas.opportunity import OpportunityBase
from app.schemas.profile import UserPreferencesBase, UserProfileBase
from app.services.normalization.geo_normalizer import GeoNormalizer
from app.services.query_optimizer import QueryOptimizer
from app.ai.query.intent_schemas import SearchIntent


class DummyOpportunity:
    def __init__(
        self,
        country="Germany",
        host_countries=None,
        is_remote=False,
        restricted_applicant_countries=None,
        status="active",
        deadline=None,
    ):
        self.id = uuid.uuid4()
        self.title = "International Excellence Award"
        self.country = country
        self.host_countries = host_countries or [country]
        self.is_remote = is_remote
        self.restricted_applicant_countries = restricted_applicant_countries or []
        self.status = status
        self.deadline = deadline or (datetime.now(UTC) + timedelta(days=60)).date()
        self.category = OpportunityCategory.SCHOLARSHIP
        self.degree_levels = ["Master's Degree"]
        self.funding_type = "Fully funded"


def test_geo_normalizer_catalog_and_regions():
    # ISO 3166-1 Normalization
    us_info = GeoNormalizer.normalize_country("USA")
    assert us_info is not None
    assert us_info.code == "US"
    assert us_info.continent == "Americas"

    de_info = GeoNormalizer.normalize_country("deutschland")
    assert de_info is not None
    assert de_info.code == "DE"

    pk_info = GeoNormalizer.normalize_country("pakistan")
    assert pk_info is not None
    assert pk_info.code == "PK"
    assert pk_info.region == "South Asia"

    # Region Normalization & Inclusions
    assert GeoNormalizer.normalize_region("worldwide") == "Worldwide"
    assert GeoNormalizer.normalize_region("Europe") == "Europe"
    assert GeoNormalizer.normalize_region("The Caribbean") == "The Caribbean"

    assert GeoNormalizer.is_in_region("DE", "Europe") is True
    assert GeoNormalizer.is_in_region("DE", "Western Europe") is True
    assert GeoNormalizer.is_in_region("US", "North America") is True
    assert GeoNormalizer.is_in_region("PK", "South Asia") is True
    assert GeoNormalizer.is_in_region("JP", "East Asia") is True
    assert GeoNormalizer.is_in_region("DE", "Worldwide") is True


def test_profile_and_preferences_schemas():
    profile = UserProfileBase(
        nationality="Pakistan",
        citizenships=["Pakistan", "United Kingdom"],
        country_of_residence="Germany",
        previous_education_country="Pakistan",
        city="Munich",
    )
    assert profile.citizenships == ["Pakistan", "United Kingdom"]
    assert profile.previous_education_country == "Pakistan"

    prefs = UserPreferencesBase(
        discovery_mode="worldwide",
        preferred_countries=["Germany", "United Kingdom"],
        acceptable_countries=["Canada", "Australia", "Switzerland"],
        preferred_regions=["Europe", "North America"],
        excluded_countries=["United States"],
        willing_to_relocate=True,
        willing_to_travel=True,
        open_to_remote=True,
    )
    assert prefs.discovery_mode == "worldwide"
    assert "Canada" in prefs.acceptable_countries
    assert prefs.willing_to_travel is True


def test_hard_filter_location_and_eligibility():
    engine = HardFilterEngine()

    # 1. Worldwide mode allows opportunity anywhere
    opp_de = DummyOpportunity(country="Germany")
    worldwide_pref = [
        UserPreference(
            category="LOCATION",
            value=["Worldwide"],
            priority=PreferencePriority.REQUIRED,
        )
    ]
    eval_res = engine.evaluate(opp_de, worldwide_pref)
    assert eval_res.passed is True

    # 2. Remote programs are globally accessible regardless of host country
    opp_remote = DummyOpportunity(country="Australia", is_remote=True)
    strict_germany = [
        UserPreference(
            category="LOCATION",
            value=["Germany"],
            priority=PreferencePriority.REQUIRED,
        )
    ]
    eval_remote = engine.evaluate(opp_remote, strict_germany)
    assert eval_remote.passed is True

    # 3. Excluded country is strictly rejected
    opp_us = DummyOpportunity(country="United States")
    exclude_us = [
        UserPreference(
            category="EXCLUDED_COUNTRIES",
            value=["United States"],
            priority=PreferencePriority.REQUIRED,
        )
    ]
    eval_exclude = engine.evaluate(opp_us, exclude_us)
    assert eval_exclude.passed is False
    assert "excluded destination" in eval_exclude.rejection_reason.lower()

    # 4. Restricted applicant country rejection
    opp_restricted = DummyOpportunity(
        country="Germany", restricted_applicant_countries=["India", "China"]
    )
    user_cit = [
        UserPreference(
            category="CITIZENSHIP",
            value=["India"],
            priority=PreferencePriority.REQUIRED,
        )
    ]
    eval_restr = engine.evaluate(opp_restricted, user_cit)
    assert eval_restr.passed is False
    assert eval_restr.filter_category == "ELIGIBILITY"


def test_location_fit_calculator_scoring():
    opp_de = DummyOpportunity(country="Germany")

    # Preferred location match -> 1.0
    prefs_pref = [
        UserPreference(
            category="LOCATION",
            value=["Germany", "United Kingdom"],
            priority=PreferencePriority.HIGH,
        )
    ]
    fit_pref = LocationFitCalculator.calculate(opp_de, prefs_pref)
    assert fit_pref.score == 1.0
    assert "matches preferred destination" in fit_pref.reason.lower()

    # Acceptable location -> 0.78
    prefs_acc = [
        UserPreference(
            category="LOCATION",
            value=["United Kingdom"],
            priority=PreferencePriority.HIGH,
        ),
        UserPreference(
            category="ACCEPTABLE_COUNTRIES",
            value=["Germany"],
            priority=PreferencePriority.MEDIUM,
        ),
    ]
    fit_acc = LocationFitCalculator.calculate(opp_de, prefs_acc)
    assert fit_acc.score == 0.78
    assert "acceptable" in fit_acc.reason.lower()

    # Worldwide mode -> 0.88
    prefs_ww = [
        UserPreference(
            category="DISCOVERY_MODE",
            value="worldwide",
            priority=PreferencePriority.HIGH,
        )
    ]
    fit_ww = LocationFitCalculator.calculate(opp_de, prefs_ww)
    assert fit_ww.score == 0.88
    assert "worldwide discovery" in fit_ww.reason.lower()

    # Remote program -> 0.92
    opp_online = DummyOpportunity(country="Japan", is_remote=True)
    fit_remote = LocationFitCalculator.calculate(opp_online, prefs_pref)
    assert fit_remote.score == 0.92
    assert "online / remote" in fit_remote.reason.lower()

    # Excluded country -> 0.0 MISMATCH
    prefs_exc = [
        UserPreference(
            category="EXCLUDE_COUNTRY",
            value=["Germany"],
            priority=PreferencePriority.REQUIRED,
        )
    ]
    fit_exc = LocationFitCalculator.calculate(opp_de, prefs_exc)
    assert fit_exc.score == 0.0
    assert fit_exc.status == "MISMATCH"


def test_query_optimizer_worldwide_and_exclusions():
    intent = SearchIntent(
        original_query="computer science scholarships",
        is_search_intent=True,
        opportunity_categories=["Scholarship"],
        degree_levels=["Master's"],
        fields=["Computer Science"],
        countries=[],
        regions=[],
    )

    class MockProfile:
        matching_signals = {
            "discovery_mode": "worldwide",
            "excluded_countries": ["United States"],
        }
        identity_context = type("Identity", (), {"nationality": "Pakistan"})()

    queries = QueryOptimizer.optimize_queries(intent, MockProfile())

    purposes = [q.purpose for q in queries]
    assert "worldwide_open_applicant_search" in purposes
    assert "global_remote_opportunity_search" in purposes

    # Check that excluded countries are in excluded_terms
    ww_query = next(q for q in queries if q.purpose == "worldwide_open_applicant_search")
    assert "united states" in ww_query.excluded_terms
