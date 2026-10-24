from datetime import date

from app.ai.query.intent_schemas import (
    FundingConstraintType,
    TemporalConstraintType,
    TestRequirementType,
    UserIntentType,
)
from app.ai.query.query_understanding_service import QueryUnderstandingService


def test_query_fully_funded_masters_scholarships_in_europe() -> None:
    service = QueryUnderstandingService()
    intent = service.understand_query(
        "Find fully funded master's scholarships in Europe for computer science."
    )

    assert intent.is_search_intent is True
    assert intent.intent_type == UserIntentType.FIND_SCHOLARSHIPS
    assert "Scholarship" in intent.opportunity_categories
    assert "Europe" in intent.regions
    assert "Master's" in intent.degree_levels
    assert "Computer Science" in intent.fields

    # Funding check: must be explicitly fully funded
    assert len(intent.funding_constraints) > 0
    assert intent.funding_constraints[0].constraint_type == FundingConstraintType.FULLY_FUNDED
    assert intent.funding_constraints[0].is_fully_funded is True


def test_query_scholarships_without_ielts() -> None:
    service = QueryUnderstandingService()
    intent = service.understand_query("Which scholarships can I apply for without IELTS?")

    assert intent.is_search_intent is True
    assert "Scholarship" in intent.opportunity_categories
    assert len(intent.language_test_constraints) == 1

    tc = intent.language_test_constraints[0]
    assert tc.test_name == "IELTS"
    assert tc.requirement_type == TestRequirementType.NOT_REQUIRED
    # Verification flag must be preserved
    assert tc.verification_required is True


def test_query_ai_internships_in_germany_international_students() -> None:
    service = QueryUnderstandingService()
    intent = service.understand_query("Find AI internships in Germany for international students.")

    assert intent.intent_type == UserIntentType.FIND_INTERNSHIPS
    assert "Internship" in intent.opportunity_categories
    assert "Germany" in intent.countries
    assert "Artificial Intelligence" in intent.fields
    assert "international students" in intent.nationality_constraints


def test_query_research_fellowships_machine_learning() -> None:
    service = QueryUnderstandingService()
    intent = service.understand_query("Show me research fellowships related to machine learning.")

    assert intent.intent_type == UserIntentType.FIND_RESEARCH_OPPORTUNITIES
    assert (
        "Fellowship" in intent.opportunity_categories or "Research" in intent.opportunity_categories
    )
    assert "Machine Learning" in intent.fields


def test_query_startup_funding_women_founders() -> None:
    service = QueryUnderstandingService()
    intent = service.understand_query(
        "Find startup funding opportunities available to women founders."
    )

    assert intent.intent_type == UserIntentType.FIND_FUNDING
    assert "Startup Funding" in intent.opportunity_categories
    assert "women founders" in intent.nationality_constraints


def test_query_temporal_understanding_this_month() -> None:
    service = QueryUnderstandingService()
    fixed_date = date(2026, 9, 15)
    intent = service.understand_query(
        "Which opportunities can I apply for this month?",
        as_of_date=fixed_date,
    )

    assert intent.is_search_intent is True
    assert len(intent.deadline_constraints) == 1
    dc = intent.deadline_constraints[0]
    assert dc.constraint_type == TemporalConstraintType.THIS_MONTH
    assert dc.window_start == fixed_date
    assert dc.window_end == date(2026, 9, 30)


def test_query_temporal_understanding_next_month_and_days() -> None:
    service = QueryUnderstandingService()
    fixed_date = date(2026, 9, 15)

    intent_next = service.understand_query(
        "Show scholarships closing next month",
        as_of_date=fixed_date,
    )
    assert len(intent_next.deadline_constraints) == 1
    dc_next = intent_next.deadline_constraints[0]
    assert dc_next.constraint_type == TemporalConstraintType.NEXT_MONTH
    assert dc_next.window_start == date(2026, 10, 1)
    assert dc_next.window_end == date(2026, 10, 31)

    intent_days = service.understand_query(
        "Find opportunities closing within 30 days",
        as_of_date=fixed_date,
    )
    assert len(intent_days.deadline_constraints) == 1
    dc_days = intent_days.deadline_constraints[0]
    assert dc_days.constraint_type == TemporalConstraintType.WITHIN_DAYS
    assert dc_days.days_window == 30


def test_query_informational_vs_search() -> None:
    service = QueryUnderstandingService()

    # Informational question: Must NOT be treated as opportunity search
    info_intent = service.understand_query("What does Erasmus Mundus mean?")
    assert info_intent.is_search_intent is False
    assert info_intent.intent_type == UserIntentType.EXPLAIN_OPPORTUNITY

    info_intent_2 = service.understand_query("Explain DAAD scholarship requirements")
    assert info_intent_2.is_search_intent is False
    assert info_intent_2.intent_type == UserIntentType.EXPLAIN_OPPORTUNITY

    # Search question
    search_intent = service.understand_query("Find Erasmus Mundus programs for me")
    assert search_intent.is_search_intent is True


def test_query_distinguishes_funded_from_fully_funded() -> None:
    service = QueryUnderstandingService()

    # Generic "funded"
    intent1 = service.understand_query("Find funded internships in USA")
    assert intent1.funding_constraints[0].constraint_type == FundingConstraintType.ANY_FUNDED
    assert intent1.funding_constraints[0].is_fully_funded is False

    # Explicit "fully funded"
    intent2 = service.understand_query("Find fully funded internships in USA")
    assert intent2.funding_constraints[0].constraint_type == FundingConstraintType.FULLY_FUNDED
    assert intent2.funding_constraints[0].is_fully_funded is True
