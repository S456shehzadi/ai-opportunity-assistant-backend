"""Intent classifier and reference extraction for conversational opportunity discovery."""

from __future__ import annotations

import re
from typing import Any

from app.ai.conversation.context import ConversationContext
from app.ai.conversation.memory import ConversationMemory
from app.ai.conversation.schemas import AssistantIntent, AssistantIntentType
from app.ai.query.intent_schemas import SearchIntent
from app.ai.query.query_understanding_service import QueryUnderstandingService


class ConversationalIntentClassifier:
    """Classifies user messages into structured AssistantIntent with context awareness."""

    def __init__(self, query_service: QueryUnderstandingService | None = None) -> None:
        self.query_service = query_service or QueryUnderstandingService()

    def classify(
        self,
        message: str,
        context: ConversationContext | None = None,
    ) -> AssistantIntent:
        """Determines the specific AssistantIntentType and relevant parameters."""
        raw_query = message.strip()
        lower_query = raw_query.lower()

        # 1. Out of domain / UNKNOWN detection
        if self._is_out_of_domain(lower_query):
            return AssistantIntent(
                intent_type=AssistantIntentType.UNKNOWN,
                raw_query=raw_query,
                confidence=0.95,
            )

        # 2. Ambiguity / Clarification check
        if self._is_too_vague(lower_query, context):
            return AssistantIntent(
                intent_type=AssistantIntentType.CLARIFICATION_REQUIRED,
                raw_query=raw_query,
                confidence=0.90,
            )

        # 3. Preference updates
        if self._is_preference_update(lower_query):
            return AssistantIntent(
                intent_type=AssistantIntentType.UPDATE_PREFERENCES,
                raw_query=raw_query,
                requires_profile=True,
                confidence=0.90,
            )

        # 4. Show saved
        if self._is_show_saved(lower_query):
            return AssistantIntent(
                intent_type=AssistantIntentType.SHOW_SAVED,
                raw_query=raw_query,
                requires_profile=True,
                confidence=0.95,
            )

        # 5. Extract referenced opportunity IDs from context
        target_ids = []
        if context:
            target_ids = ConversationMemory.resolve_references(raw_query, context)

        # 6. Specific follow-ups or queries on active/referenced opportunities
        if self._is_profile_gap(lower_query):
            return AssistantIntent(
                intent_type=AssistantIntentType.PROFILE_GAP,
                opportunity_ids=target_ids,
                requires_profile=True,
                requires_eligibility=True,
                raw_query=raw_query,
                confidence=0.95,
            )

        if self._is_compare(lower_query):
            comp_fields = self._extract_comparison_fields(lower_query)
            return AssistantIntent(
                intent_type=AssistantIntentType.COMPARE_OPPORTUNITIES,
                opportunity_ids=target_ids,
                comparison_fields=comp_fields,
                raw_query=raw_query,
                confidence=0.95,
            )

        if self._is_find_similar(lower_query):
            return AssistantIntent(
                intent_type=AssistantIntentType.FIND_SIMILAR,
                opportunity_ids=target_ids,
                requires_ranking=True,
                raw_query=raw_query,
                confidence=0.90,
            )

        if self._is_eligibility(lower_query):
            return AssistantIntent(
                intent_type=AssistantIntentType.CHECK_ELIGIBILITY,
                opportunity_ids=target_ids,
                requires_profile=True,
                requires_eligibility=True,
                raw_query=raw_query,
                confidence=0.95,
            )

        if self._is_deadline(lower_query):
            return AssistantIntent(
                intent_type=AssistantIntentType.CHECK_DEADLINE,
                opportunity_ids=target_ids,
                requested_fields=["deadline", "application_period"],
                raw_query=raw_query,
                confidence=0.95,
            )

        if self._is_requirement(lower_query):
            return AssistantIntent(
                intent_type=AssistantIntentType.CHECK_REQUIREMENT,
                opportunity_ids=target_ids,
                requested_fields=["requirements", "language_tests", "academic"],
                raw_query=raw_query,
                confidence=0.95,
            )

        if self._is_funding(lower_query):
            return AssistantIntent(
                intent_type=AssistantIntentType.CHECK_FUNDING,
                opportunity_ids=target_ids,
                requested_fields=["funding", "stipend", "tuition_coverage"],
                raw_query=raw_query,
                confidence=0.95,
            )

        if self._is_application(lower_query):
            return AssistantIntent(
                intent_type=AssistantIntentType.CHECK_APPLICATION,
                opportunity_ids=target_ids,
                requested_fields=["application_url", "how_to_apply"],
                raw_query=raw_query,
                confidence=0.95,
            )

        # 7. Refinement of existing search
        if context and context.active_opportunities and self._is_refinement(lower_query):
            filters = self._extract_filters(lower_query)
            return AssistantIntent(
                intent_type=AssistantIntentType.REFINE_SEARCH,
                filters=filters,
                opportunity_ids=target_ids,
                requires_ranking=True,
                raw_query=raw_query,
                confidence=0.90,
            )

        # 8. Explain opportunity
        if self._is_explain(lower_query):
            # Check if this is general educational question vs specific opportunity
            if not target_ids and not self._mentions_specific_name(lower_query):
                return AssistantIntent(
                    intent_type=AssistantIntentType.GENERAL_OPPORTUNITY_QUESTION,
                    raw_query=raw_query,
                    confidence=0.85,
                )
            return AssistantIntent(
                intent_type=AssistantIntentType.EXPLAIN_OPPORTUNITY,
                opportunity_ids=target_ids,
                requested_fields=["description", "benefits", "eligibility", "deadline"],
                raw_query=raw_query,
                confidence=0.90,
            )

        # 9. General Search Intent Parsing via QueryUnderstandingService
        parsed_search = self.query_service.understand_query(raw_query)

        # Check if the query is a general knowledge question
        if not parsed_search.is_search_intent:
            return AssistantIntent(
                intent_type=AssistantIntentType.GENERAL_OPPORTUNITY_QUESTION,
                search_intent=parsed_search,
                raw_query=raw_query,
                confidence=0.85,
            )

        filters = self._extract_filters_from_search_intent(parsed_search)
        return AssistantIntent(
            intent_type=AssistantIntentType.SEARCH_OPPORTUNITIES,
            search_intent=parsed_search,
            filters=filters,
            requires_live_search=True,
            requires_ranking=True,
            requires_profile=True,
            requires_eligibility=True,
            raw_query=raw_query,
            confidence=0.90,
        )

    def _is_out_of_domain(self, q: str) -> bool:
        """Identifies messages with zero relevance to opportunities, grants, or education."""
        out_patterns = [
            r"^(hi|hello|hey|good morning|good evening)$",
            r"\b(weather|sports|football|basketball|recipe|bake|cake|poem|joke|sing)\b",
            r"\b(who won|president of|capital of|movie|celebrity|bitcoin|crypto)\b",
        ]
        return any(re.search(pat, q) for pat in out_patterns)

    def _is_too_vague(self, q: str, ctx: ConversationContext | None) -> bool:
        """Identifies underspecified queries when there is no active context."""
        vague_single_words = {"scholarship", "scholarships", "opportunity", "opportunities", "help"}
        if q.strip() in vague_single_words:
            if not ctx or not ctx.active_opportunities:
                return True
        return False

    def _is_preference_update(self, q: str) -> bool:
        patterns = [
            r"\b(i\s+prefer|my\s+preference|save\s+preference|i\s+only\s+want|change\s+my\s+preferences)\b",
            r"\b(interested\s+in\s+studying\s+in|prefer\s+studying\s+in)\b",
        ]
        return any(re.search(pat, q) for pat in patterns)

    def _is_show_saved(self, q: str) -> bool:
        patterns = [
            r"\b(show|view|list|get)\s+(my\s+)?(saved|bookmarked|favorite)\b",
            r"\b(saved\s+opportunities|my\s+bookmarks)\b",
        ]
        return any(re.search(pat, q) for pat in patterns)

    def _is_profile_gap(self, q: str) -> bool:
        patterns = [
            r"\b(what\s+am\s+i\s+missing|why\s+am\s+i\s+not\s+eligible|missing\s+requirements?)\b",
            r"\b(how\s+to\s+improve\s+eligibility|profile\s+gap|gaps\s+in\s+my\s+profile)\b",
        ]
        return any(re.search(pat, q) for pat in patterns)

    def _is_compare(self, q: str) -> bool:
        patterns = [
            r"\b(compare|difference\s+between|vs\.?|versus)\b",
            r"\b(which\s+(one\s+)?is\s+better|how\s+do\s+they\s+compare)\b",
        ]
        return any(re.search(pat, q) for pat in patterns)

    def _is_find_similar(self, q: str) -> bool:
        patterns = [
            r"\b(similar\s+to|more\s+like|alternatives\s+to|comparable\s+to)\b",
        ]
        return any(re.search(pat, q) for pat in patterns)

    def _is_eligibility(self, q: str) -> bool:
        patterns = [
            r"\b(am\s+i\s+eligible|can\s+i\s+apply|do\s+i\s+qualify|is\s+my\s+profile\s+eligible)\b",
            r"\b(eligibility\s+check|check\s+my\s+eligibility)\b",
        ]
        return any(re.search(pat, q) for pat in patterns)

    def _is_deadline(self, q: str) -> bool:
        patterns = [
            r"\b(when\s+is\s+the\s+deadline|closing\s+date|last\s+date|due\s+date|deadline)\b",
            r"\b(which\s+ones?\s+close|closing\s+soon|due\s+this\s+month)\b",
        ]
        return any(re.search(pat, q) for pat in patterns)

    def _is_requirement(self, q: str) -> bool:
        if any(q.startswith(w) for w in ["find", "search", "show me", "look for", "discover"]):
            return False
        patterns = [
            r"\b(requirement|requirements|what\s+are\s+the\s+requirements)\b",
            r"\b(does\s+it\s+require|do\s+i\s+need|without\s+ielts|no\s+ielts|no\s+gre|exempt)\b",
            r"\b(which\s+(?:of\s+these\s+)?(?:don't|do\s+not)\s+require)\b",
        ]
        return any(re.search(pat, q) for pat in patterns)

    def _is_funding(self, q: str) -> bool:
        if any(q.startswith(w) for w in ["find", "search", "show me", "look for", "discover"]):
            return False
        patterns = [
            r"\b(how\s+much\s+(do\s+they\s+pay|is\s+the\s+stipend))\b",
            r"\b(which\s+(?:one\s+)?has\s+a\s+higher\s+stipend)\b",
            r"\b(what\s+does\s+(?:it|the\s+scholarship)\s+cover)\b",
            r"\b(stipend\s+amount|living\s+allowance|coverage\s+details)\b",
        ]
        return any(re.search(pat, q) for pat in patterns)

    def _is_application(self, q: str) -> bool:
        patterns = [
            r"\b(how\s+do\s+i\s+apply|application\s+link|application\s+process|where\s+to\s+apply)\b",
            r"\b(apply\s+online|how\s+to\s+submit)\b",
        ]
        return any(re.search(pat, q) for pat in patterns)

    def _is_refinement(self, q: str) -> bool:
        patterns = [
            r"\b(only\s+show|filter\s+by|in\s+munich|in\s+berlin|only\s+fully\s+funded)\b",
            r"\b(exclude|just\s+the\s+ones|restrict\s+to)\b",
        ]
        return any(re.search(pat, q) for pat in patterns)

    def _is_explain(self, q: str) -> bool:
        patterns = [
            r"\b(tell\s+me\s+more|explain|describe|details\s+on|overview\s+of)\b",
            r"^what\s+is\s+",
        ]
        return any(re.search(pat, q) for pat in patterns)

    def _mentions_specific_name(self, q: str) -> bool:
        tokens = ["daad", "erasmus", "fulbright", "chevening", "gates", "rhodes", "mext"]
        return any(t in q for t in tokens)

    def _extract_comparison_fields(self, q: str) -> list[str]:
        fields = []
        if "stipend" in q or "funding" in q or "money" in q:
            fields.append("funding")
        if "deadline" in q or "date" in q:
            fields.append("deadline")
        if "requirement" in q or "ielts" in q or "gre" in q:
            fields.append("requirements")
        if "location" in q or "country" in q or "city" in q:
            fields.append("location")
        if not fields:
            fields = ["funding", "requirements", "deadline", "location"]
        return fields

    def _extract_filters(self, q: str) -> dict[str, Any]:
        filters: dict[str, Any] = {}
        if "fully funded" in q:
            filters["is_fully_funded"] = True
        if "without ielts" in q or "no ielts" in q:
            filters["no_ielts"] = True
        for country in ["germany", "usa", "uk", "canada", "japan", "france", "australia"]:
            if country in q:
                filters["country"] = country.title()
        for city in ["munich", "berlin", "oxford", "cambridge", "tokyo", "paris"]:
            if city in q:
                filters["city"] = city.title()
        return filters

    def _extract_filters_from_search_intent(self, intent: SearchIntent) -> dict[str, Any]:
        filters: dict[str, Any] = {}
        if intent.countries:
            filters["country"] = intent.countries[0].title()
        elif intent.regions:
            filters["country"] = intent.regions[0].title()
        if intent.degree_levels:
            filters["degree_level"] = intent.degree_levels[0]
        if intent.fields:
            filters["field_of_study"] = intent.fields[0]
        if intent.funding_constraints:
            for fc in intent.funding_constraints:
                if fc.is_fully_funded:
                    filters["is_fully_funded"] = True
        return filters
