"""Conversation context modeling and privacy-preserving profile context extraction."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from app.ai.query.intent_schemas import SearchIntent
from app.opportunities.eligibility.profile_adapter import ProfileAdapter, UnifiedUserFacts
from app.opportunities.ranking.schemas import RankedOpportunityResult, UserPreference
from app.schemas.ai_profile import NormalizedAIProfile


class ProfileContextBuilder:
    """Builds task-specific, privacy-preserving user profile context."""

    @classmethod
    def build_minimal_context(
        cls,
        profile: NormalizedAIProfile | UnifiedUserFacts | dict[str, Any] | None,
        task_intent: str = "search",
    ) -> dict[str, Any]:
        """Extracts only strictly necessary profile facts, stripping private identifiers."""
        if profile is None:
            return {}

        facts: UnifiedUserFacts
        if isinstance(profile, UnifiedUserFacts):
            facts = profile
        elif isinstance(profile, NormalizedAIProfile):
            facts = ProfileAdapter.adapt(profile)
        elif isinstance(profile, dict):
            facts = ProfileAdapter.adapt(profile)
        else:
            return {}

        fields_of_study = [
            str(r.get("field_of_study")) for r in facts.academic_records if r.get("field_of_study")
        ]

        context = {
            "highest_degree_level": facts.highest_degree_level,
            "fields_of_study": fields_of_study,
            "cgpa_4_scale": facts.normalized_gpa_4_scale or facts.highest_cgpa,
            "nationality": facts.nationality,
            "has_english_medium_degree": facts.has_english_medium_degree,
            "tests": facts.tests,
            "skills": facts.skills[:5],
            "work_experience_years": facts.work_experience_years,
        }

        # Filter out None values
        return {k: v for k, v in context.items() if v is not None}


class ConversationContext(BaseModel):
    """Tracks active conversational discovery session state across multi-turn interactions."""

    conversation_id: str
    user_id: str | None = None
    recent_messages: list[dict[str, str]] = Field(default_factory=list)
    active_search_query: str | None = None
    active_search_intent: SearchIntent | None = None
    active_opportunities: list[Any] = Field(default_factory=list)
    active_eligibility_map: dict[str, Any] = Field(default_factory=dict)
    active_ranking_result: RankedOpportunityResult | None = None
    active_filters: dict[str, Any] = Field(default_factory=dict)
    active_comparison_ids: list[str] = Field(default_factory=list)
    user_preferences: list[UserPreference] = Field(default_factory=list)
    profile_context: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def add_message(self, role: str, content: str) -> None:
        """Appends a turn to message history, maintaining a rolling window."""
        self.recent_messages.append({"role": role, "content": content})
        if len(self.recent_messages) > 10:
            self.recent_messages = self.recent_messages[-10:]
        self.updated_at = datetime.now(UTC)

    def get_opportunity_by_id(self, opp_id: str) -> Any | None:
        """Finds a loaded candidate opportunity by ID or canonical key."""
        for opp in self.active_opportunities:
            curr_id = getattr(opp, "id", None) or getattr(opp, "canonical_key", None)
            if curr_id and str(curr_id) == str(opp_id):
                return opp
        return None
