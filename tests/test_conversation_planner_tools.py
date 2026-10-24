"""Unit tests for Assistant Planner and Assistant Tools."""

from __future__ import annotations

import pytest

from app.ai.conversation.context import ConversationContext
from app.ai.conversation.planner import AssistantPlanner
from app.ai.conversation.safety import ToolPermissionGuardrails
from app.ai.conversation.schemas import (
    AssistantIntent,
    AssistantIntentType,
)
from app.ai.conversation.tools import AssistantTools
from app.opportunities.eligibility.schemas import (
    EligibilityResult,
    OverallEligibilityStatus,
    PersonalizedIntelligenceSummary,
    RequirementEvaluation,
    RequirementPriority,
    RequirementStatus,
)


@pytest.fixture
def sample_opportunities() -> list[dict]:
    return [
        {
            "id": "opp-daad",
            "title": "DAAD EPOS Scholarship",
            "organization": "DAAD",
            "description": "Full Master scholarship in Germany with monthly stipend.",
            "category": "scholarship",
            "host_country": "Germany",
            "funding_type": "fully_funded",
            "funding_amount": "934 EUR/month",
            "deadline": "2026-10-31",
            "official_source_url": "https://daad.de/epos",
            "source_domain": "daad.de",
            "eligibility": {
                "degree_levels": ["Master's"],
                "min_gpa": 3.0,
                "language_requirements": ["IELTS 6.0"],
            },
        },
        {
            "id": "opp-erasmus",
            "title": "Erasmus Mundus Joint Master",
            "organization": "European Union",
            "description": "Full scholarship for study in multiple EU countries.",
            "category": "scholarship",
            "host_country": "Global",
            "funding_type": "fully_funded",
            "funding_amount": "1400 EUR/month",
            "deadline": "2026-12-15",
            "official_source_url": "https://erasmus-plus.ec.europa.eu",
            "source_domain": "europa.eu",
            "eligibility": {
                "degree_levels": ["Master's"],
                "min_gpa": 3.2,
                "language_requirements": ["IELTS 6.5"],
            },
        },
    ]


def test_planner_existing_results_first(sample_opportunities: list[dict]) -> None:
    planner = AssistantPlanner()
    ctx = ConversationContext(conversation_id="conv-1")
    ctx.active_opportunities = sample_opportunities

    intent = AssistantIntent(
        intent_type=AssistantIntentType.CHECK_DEADLINE,
        opportunity_ids=["opp-daad"],
        raw_query="When is the deadline for DAAD?",
    )

    plan = planner.plan(intent, ctx)
    # Must NOT trigger live search since opportunity is in active memory
    assert plan.requires_live_search is False
    assert len(plan.steps) >= 1
    assert plan.steps[0].tool_name == "retrieve_opportunity"


def test_planner_new_search_requires_live() -> None:
    planner = AssistantPlanner()
    ctx = ConversationContext(conversation_id="conv-2")

    intent = AssistantIntent(
        intent_type=AssistantIntentType.SEARCH_OPPORTUNITIES,
        raw_query="Find CS scholarships in Germany",
        requires_live_search=True,
        requires_eligibility=True,
        requires_ranking=True,
    )

    plan = planner.plan(intent, ctx)
    assert plan.requires_live_search is True
    tool_names = [s.tool_name for s in plan.steps]
    assert "search_opportunities" in tool_names
    assert "check_eligibility" in tool_names
    assert "rank_opportunities" in tool_names


def test_guardrails_unauthorized_permission() -> None:
    # Attempting an unauthorized tool permission raises PermissionError
    with pytest.raises(PermissionError):
        ToolPermissionGuardrails.validate_tool_permission("SYSTEM_SHELL")  # type: ignore


@pytest.mark.asyncio
async def test_tools_search(sample_opportunities: list[dict]) -> None:
    tools = AssistantTools()
    results = await tools.search_opportunities(
        query="DAAD",
        filters={"country": "Germany"},
        candidate_pool=sample_opportunities,
    )
    assert len(results) == 1
    assert results[0]["id"] == "opp-daad"


def test_tools_compare(sample_opportunities: list[dict]) -> None:
    tools = AssistantTools()
    comp = tools.compare_opportunities(sample_opportunities)
    assert comp.opportunity_ids == ["opp-daad", "opp-erasmus"]
    assert len(comp.table_rows) > 0
    assert len(comp.differences) > 0


def test_tools_profile_gaps(sample_opportunities: list[dict]) -> None:
    tools = AssistantTools()
    opp = sample_opportunities[0]

    elig_res = EligibilityResult(
        opportunity_id="opp-daad",
        user_id="user-1",
        overall_status=OverallEligibilityStatus.POTENTIALLY_ELIGIBLE,
        explanation="Potentially eligible with gaps",
        match_percentage=75.0,
        requirements=[
            RequirementEvaluation(
                requirement_id="req-1",
                requirement_type="academic",
                requirement_description="Bachelor's degree in related field",
                status=RequirementStatus.MATCH,
                priority=RequirementPriority.MANDATORY,
                explanation="Profile contains relevant Bachelor's degree.",
            ),
            RequirementEvaluation(
                requirement_id="req-2",
                requirement_type="language",
                requirement_description="IELTS 6.0 or equivalent",
                status=RequirementStatus.NO_MATCH,
                priority=RequirementPriority.MANDATORY,
                user_value="None",
                required_value="IELTS 6.0",
                explanation="No English test on record.",
            ),
        ],
        personalized_intelligence=PersonalizedIntelligenceSummary(
            satisfied_requirements=["Bachelor's degree in related field"],
            unsatisfied_requirements=["IELTS 6.0 or equivalent"],
        ),
    )

    gaps = tools.get_profile_gaps(opp, elig_res)
    assert len(gaps["unmet_requirements"]) == 1
    assert gaps["unmet_requirements"][0]["requirement"] == "IELTS 6.0 or equivalent"
    assert len(gaps["recommended_actions"]) >= 1
