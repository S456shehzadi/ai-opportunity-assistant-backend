from typing import Any

from app.ai.query.intent_schemas import SearchIntent
from app.ai.query.query_understanding_service import QueryUnderstandingService
from app.schemas.ai_profile import NormalizedAIProfile
from app.schemas.search_context import (
    ClarificationImportance,
    ClarificationRequirement,
    ConflictResolutionType,
    ConstraintConflict,
    OpportunitySearchContext,
)
from app.services.query_optimizer import QueryOptimizer


class OpportunitySearchContextService:
    """Combines user profile and query intent into an OpportunitySearchContext.

    Adheres strictly to accuracy rules:
    - Never presents user profile facts as explicitly stated query terms.
    - Explicit query constraints override stored user preferences with full auditable traces.
    - Accurately tracks missing information and detects ambiguity.
    """

    def __init__(self, query_service: QueryUnderstandingService | None = None) -> None:
        self.query_service = query_service or QueryUnderstandingService()

    def build_context(
        self,
        query: str | SearchIntent,
        profile: NormalizedAIProfile,
    ) -> OpportunitySearchContext:
        """Constructs an OpportunitySearchContext from query (or intent) and NormalizedAIProfile."""
        if isinstance(query, str):
            intent = self.query_service.understand_query(query)
        else:
            intent = query

        # 1. Explicit constraints (strictly from query)
        explicit = dict(intent.explicit_constraints)

        # 2. Profile constraints (strictly from profile background)
        profile_constraints: dict[str, Any] = {}
        if profile.identity_context.nationality:
            profile_constraints["nationality"] = profile.identity_context.nationality
        if profile.identity_context.country_of_residence:
            profile_constraints["country_of_residence"] = (
                profile.identity_context.country_of_residence
            )
        if profile.academic_performance.highest_degree_level:
            profile_constraints["highest_degree_level"] = (
                profile.academic_performance.highest_degree_level
            )
        if profile.academic_performance.normalized_gpa_4_scale is not None:
            profile_constraints["gpa_4_scale"] = profile.academic_performance.normalized_gpa_4_scale
        if profile.opportunity_preferences.preferred_fields:
            profile_constraints["preferred_fields"] = (
                profile.opportunity_preferences.preferred_fields
            )
        if profile.geographic_preferences.preferred_countries:
            profile_constraints["preferred_countries"] = (
                profile.geographic_preferences.preferred_countries
            )

        # 3. Conflict Detection: Explicit Query vs Stored Profile Preferences
        conflicts: list[ConstraintConflict] = []

        # Country conflict
        query_countries = set(intent.countries)
        profile_pref_countries = set(profile.geographic_preferences.preferred_countries)
        if (
            query_countries
            and profile_pref_countries
            and not (query_countries & profile_pref_countries)
        ):
            conflicts.append(
                ConstraintConflict(
                    field="country",
                    query_value=list(query_countries),
                    profile_value=list(profile_pref_countries),
                    resolution=ConflictResolutionType.QUERY_OVERRIDE,
                    explanation=(
                        f"Explicit query requested country {list(query_countries)} which overrides "
                        f"stored profile preference {list(profile_pref_countries)} for this search."
                    ),
                )
            )

        # Category conflict
        query_cats = set(intent.opportunity_categories)
        profile_pref_cats = set(profile.opportunity_preferences.preferred_categories)
        if query_cats and profile_pref_cats and not (query_cats & profile_pref_cats):
            conflicts.append(
                ConstraintConflict(
                    field="opportunity_category",
                    query_value=list(query_cats),
                    profile_value=list(profile_pref_cats),
                    resolution=ConflictResolutionType.QUERY_OVERRIDE,
                    explanation=(
                        f"Explicit query requested category {list(query_cats)} which overrides "
                        f"stored profile preference {list(profile_pref_cats)}."
                    ),
                )
            )

        # 4. Ambiguity Detection & Clarification Requirements
        clarifications: list[ClarificationRequirement] = []
        unknown_info: list[str] = list(intent.unknown_constraints)

        # Degree level ambiguity
        effective_degree = intent.degree_levels or (
            [profile.academic_performance.highest_degree_level]
            if profile.academic_performance.highest_degree_level
            else []
        )
        if not effective_degree and intent.is_search_intent:
            clarifications.append(
                ClarificationRequirement(
                    field="degree_level",
                    reason="No target degree level was specified in the query or user profile.",
                    importance=ClarificationImportance.CRITICAL,
                    suggested_options=["Bachelor's", "Master's", "Doctorate", "Postdoc"],
                )
            )

        # Location ambiguity
        effective_location = (
            intent.countries or intent.regions or profile.geographic_preferences.preferred_countries
        )
        if not effective_location and intent.is_search_intent:
            clarifications.append(
                ClarificationRequirement(
                    field="target_location",
                    reason="No destination country or region specified.",
                    importance=ClarificationImportance.HELPFUL,
                    suggested_options=[
                        "Europe",
                        "United States",
                        "Germany",
                        "United Kingdom",
                        "Canada",
                        "Global",
                    ],
                )
            )

        # Funding ambiguity
        if not intent.funding_constraints and not profile.funding_preferences.funding_requirement:
            clarifications.append(
                ClarificationRequirement(
                    field="funding_preference",
                    reason="No funding requirement specified.",
                    importance=ClarificationImportance.OPTIONAL,
                    suggested_options=["Fully Funded", "Partial Funding", "Any"],
                )
            )

        # 5. Inferred Context (Safe deductions that assist search)
        inferred_context: dict[str, Any] = {}
        if effective_degree:
            inferred_context["effective_degree_level"] = effective_degree[0]
        if effective_location:
            inferred_context["effective_location"] = effective_location[0]

        # 6. Generate Potential Search Queries
        search_queries = QueryOptimizer.optimize_queries(intent, profile)

        return OpportunitySearchContext(
            candidate_profile=profile,
            search_intent=intent,
            explicit_constraints=explicit,
            profile_constraints=profile_constraints,
            inferred_context=inferred_context,
            conflicts=conflicts,
            clarification_requirements=clarifications,
            unknown_information=unknown_info,
            potential_search_queries=search_queries,
        )
