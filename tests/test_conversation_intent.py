"""Unit tests for conversational intent classification and reference resolution."""

from __future__ import annotations

import pytest

from app.ai.conversation.context import ConversationContext
from app.ai.conversation.intent import ConversationalIntentClassifier
from app.ai.conversation.schemas import AssistantIntentType


@pytest.fixture
def classifier() -> ConversationalIntentClassifier:
    return ConversationalIntentClassifier()


@pytest.fixture
def active_context() -> ConversationContext:
    ctx = ConversationContext(conversation_id="conv-123")
    ctx.active_opportunities = [
        {
            "id": "opp-daad",
            "title": "DAAD Development-Related Postgraduate Courses",
            "organization": "DAAD",
            "host_country": "Germany",
            "funding_type": "fully_funded",
        },
        {
            "id": "opp-erasmus",
            "title": "Erasmus Mundus Joint Master in AI",
            "organization": "European Commission",
            "host_country": "Global",
            "funding_type": "fully_funded",
        },
    ]
    return ctx


def test_classify_out_of_domain(classifier: ConversationalIntentClassifier) -> None:
    res = classifier.classify("What is the weather in Tokyo today?")
    assert res.intent_type == AssistantIntentType.UNKNOWN


def test_classify_vague_clarification(classifier: ConversationalIntentClassifier) -> None:
    # Single vague word without context requires clarification
    res = classifier.classify("scholarship")
    assert res.intent_type == AssistantIntentType.CLARIFICATION_REQUIRED


def test_classify_search_opportunities(classifier: ConversationalIntentClassifier) -> None:
    res = classifier.classify(
        "Find fully funded master scholarships in Germany for Computer Science"
    )
    assert res.intent_type == AssistantIntentType.SEARCH_OPPORTUNITIES
    assert res.requires_live_search is True
    assert res.filters.get("country") == "Germany"
    assert res.filters.get("is_fully_funded") is True


def test_classify_refine_search(
    classifier: ConversationalIntentClassifier,
    active_context: ConversationContext,
) -> None:
    res = classifier.classify("Only show the ones in Munich", context=active_context)
    assert res.intent_type == AssistantIntentType.REFINE_SEARCH
    assert res.filters.get("city") == "Munich"


def test_classify_check_eligibility(classifier: ConversationalIntentClassifier) -> None:
    res = classifier.classify("Am I eligible for this scholarship?")
    assert res.intent_type == AssistantIntentType.CHECK_ELIGIBILITY
    assert res.requires_profile is True
    assert res.requires_eligibility is True


def test_classify_compare_opportunities(
    classifier: ConversationalIntentClassifier,
    active_context: ConversationContext,
) -> None:
    res = classifier.classify("Compare the two opportunities", context=active_context)
    assert res.intent_type == AssistantIntentType.COMPARE_OPPORTUNITIES
    assert "funding" in res.comparison_fields or "requirements" in res.comparison_fields


def test_classify_profile_gap(classifier: ConversationalIntentClassifier) -> None:
    res = classifier.classify("What am I missing to qualify for DAAD?")
    assert res.intent_type == AssistantIntentType.PROFILE_GAP
    assert res.requires_profile is True


def test_classify_check_deadline(
    classifier: ConversationalIntentClassifier,
    active_context: ConversationContext,
) -> None:
    res = classifier.classify("When is the deadline for the first one?", context=active_context)
    assert res.intent_type == AssistantIntentType.CHECK_DEADLINE
    assert "opp-daad" in res.opportunity_ids


def test_classify_check_funding(
    classifier: ConversationalIntentClassifier,
    active_context: ConversationContext,
) -> None:
    res = classifier.classify("Which one has a higher stipend?", context=active_context)
    assert res.intent_type == AssistantIntentType.CHECK_FUNDING


def test_classify_check_requirement(
    classifier: ConversationalIntentClassifier,
    active_context: ConversationContext,
) -> None:
    res = classifier.classify("Which of these don't require IELTS?", context=active_context)
    assert res.intent_type == AssistantIntentType.CHECK_REQUIREMENT


def test_classify_update_preferences(classifier: ConversationalIntentClassifier) -> None:
    res = classifier.classify("I prefer fully funded opportunities in Europe")
    assert res.intent_type == AssistantIntentType.UPDATE_PREFERENCES
    assert res.requires_profile is True


def test_classify_show_saved(classifier: ConversationalIntentClassifier) -> None:
    res = classifier.classify("Show my saved opportunities")
    assert res.intent_type == AssistantIntentType.SHOW_SAVED
