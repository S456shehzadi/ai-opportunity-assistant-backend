"""Assistant Planner determining execution steps under strict guardrails."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.ai.conversation.context import ConversationContext
from app.ai.conversation.safety import ToolPermissionGuardrails
from app.ai.conversation.schemas import AssistantIntent, AssistantIntentType, ToolPermission


class PlanStep(BaseModel):
    """An individual atomic tool execution step within a conversational plan."""

    tool_name: str
    permission: ToolPermission
    parameters: dict[str, Any] = Field(default_factory=dict)
    description: str = ""


class ExecutionPlan(BaseModel):
    """Sequence of authorized operations to fulfill the user request."""

    intent: AssistantIntent
    steps: list[PlanStep] = Field(default_factory=list)
    requires_live_search: bool = False
    requires_profile: bool = False
    target_opportunity_ids: list[str] = Field(default_factory=list)
    explanation: str = ""


class AssistantPlanner:
    """Plans assistant actions prioritizing existing context before expensive external retrieval."""

    def plan(
        self,
        intent: AssistantIntent,
        context: ConversationContext,
    ) -> ExecutionPlan:
        """Formulates an execution plan upholding the Existing Results First principle."""
        steps: list[PlanStep] = []
        requires_search = False
        requires_profile = intent.requires_profile
        target_ids = list(intent.opportunity_ids)

        # 1. Ambiguity / Clarification or Unknown
        if intent.intent_type in (
            AssistantIntentType.CLARIFICATION_REQUIRED,
            AssistantIntentType.UNKNOWN,
            AssistantIntentType.GENERAL_OPPORTUNITY_QUESTION,
        ):
            return ExecutionPlan(
                intent=intent,
                steps=[],
                requires_live_search=False,
                requires_profile=False,
                target_opportunity_ids=[],
                explanation="Handled directly by conversational response generator.",
            )

        # 2. Preference Updates
        if intent.intent_type == AssistantIntentType.UPDATE_PREFERENCES:
            return ExecutionPlan(
                intent=intent,
                steps=[],
                requires_live_search=False,
                requires_profile=True,
                target_opportunity_ids=[],
                explanation="Update user preferences in context.",
            )

        # 3. Show Saved
        if intent.intent_type == AssistantIntentType.SHOW_SAVED:
            steps.append(
                PlanStep(
                    tool_name="read_saved",
                    permission=ToolPermission.READ_SAVED,
                    description="Retrieve user bookmarked opportunities.",
                )
            )
            return ExecutionPlan(
                intent=intent,
                steps=steps,
                requires_live_search=False,
                requires_profile=True,
                target_opportunity_ids=[],
                explanation="Fetch saved opportunities from user storage.",
            )

        # 4. Compare Opportunities
        if intent.intent_type == AssistantIntentType.COMPARE_OPPORTUNITIES:
            # If target_ids empty, check if we have active opportunities to compare (e.g. first 2)
            if not target_ids and len(context.active_opportunities) >= 2:
                target_ids = [
                    str(getattr(opp, "id", None) or getattr(opp, "canonical_key", f"opp_{idx}"))
                    for idx, opp in enumerate(context.active_opportunities[:2])
                ]
            steps.append(
                PlanStep(
                    tool_name="compare_opportunities",
                    permission=ToolPermission.COMPARE,
                    parameters={
                        "opportunity_ids": target_ids,
                        "fields": intent.comparison_fields,
                    },
                    description="Perform side-by-side comparison across selected opportunities.",
                )
            )
            return ExecutionPlan(
                intent=intent,
                steps=steps,
                requires_live_search=False,
                target_opportunity_ids=target_ids,
                explanation="Compare specified active opportunities.",
            )

        # 5. Existing Results First check for Opportunity Attributes / Eligibility
        has_active = bool(context.active_opportunities)
        is_attribute_query = intent.intent_type in (
            AssistantIntentType.CHECK_REQUIREMENT,
            AssistantIntentType.CHECK_DEADLINE,
            AssistantIntentType.CHECK_FUNDING,
            AssistantIntentType.CHECK_APPLICATION,
            AssistantIntentType.EXPLAIN_OPPORTUNITY,
            AssistantIntentType.CHECK_ELIGIBILITY,
            AssistantIntentType.PROFILE_GAP,
        )

        if is_attribute_query:
            # If target_ids not specified, default to all or first active opportunity
            if not target_ids and has_active:
                target_ids = [
                    str(
                        getattr(context.active_opportunities[0], "id", None)
                        or getattr(context.active_opportunities[0], "canonical_key", "opp_0")
                    )
                ]

            if intent.intent_type in (
                AssistantIntentType.CHECK_ELIGIBILITY,
                AssistantIntentType.PROFILE_GAP,
            ):
                steps.append(
                    PlanStep(
                        tool_name="check_eligibility",
                        permission=ToolPermission.CHECK_ELIGIBILITY,
                        parameters={"opportunity_ids": target_ids},
                        description="Evaluate eligibility against user profile.",
                    )
                )
                requires_profile = True
            else:
                steps.append(
                    PlanStep(
                        tool_name="retrieve_opportunity",
                        permission=ToolPermission.RETRIEVE,
                        parameters={"opportunity_ids": target_ids},
                        description="Retrieve opportunity details from active memory.",
                    )
                )

            return ExecutionPlan(
                intent=intent,
                steps=steps,
                requires_live_search=False,
                requires_profile=requires_profile,
                target_opportunity_ids=target_ids,
                explanation="Satisfy query using existing memory and active opportunities.",
            )

        # 6. Refine Search
        if intent.intent_type == AssistantIntentType.REFINE_SEARCH:
            steps.append(
                PlanStep(
                    tool_name="search_opportunities",
                    permission=ToolPermission.SEARCH,
                    parameters={"filters": intent.filters, "query": intent.raw_query},
                    description="Filter active opportunities locally.",
                )
            )
            if intent.requires_ranking:
                steps.append(
                    PlanStep(
                        tool_name="rank_opportunities",
                        permission=ToolPermission.RANK,
                        description="Re-rank filtered opportunities.",
                    )
                )
            return ExecutionPlan(
                intent=intent,
                steps=steps,
                requires_live_search=False,
                target_opportunity_ids=[],
                explanation="Refining existing active opportunities without new external search.",
            )

        # 7. Find Similar
        if intent.intent_type == AssistantIntentType.FIND_SIMILAR:
            if not target_ids and has_active:
                target_ids = [
                    str(
                        getattr(context.active_opportunities[0], "id", None)
                        or getattr(context.active_opportunities[0], "canonical_key", "opp_0")
                    )
                ]
            steps.append(
                PlanStep(
                    tool_name="search_opportunities",
                    permission=ToolPermission.SEARCH,
                    parameters={"similar_to": target_ids[0] if target_ids else None},
                    description="Find similar opportunities in database or web.",
                )
            )
            return ExecutionPlan(
                intent=intent,
                steps=steps,
                requires_live_search=True,
                target_opportunity_ids=target_ids,
                explanation="Search for opportunities similar to the selected target.",
            )

        # 8. New Search Opportunities
        requires_search = True
        steps.append(
            PlanStep(
                tool_name="search_opportunities",
                permission=ToolPermission.SEARCH,
                parameters={"query": intent.raw_query, "filters": intent.filters},
                description="Search candidate opportunities.",
            )
        )
        if intent.requires_eligibility:
            steps.append(
                PlanStep(
                    tool_name="check_eligibility",
                    permission=ToolPermission.CHECK_ELIGIBILITY,
                    description="Evaluate user eligibility for candidates.",
                )
            )
        if intent.requires_ranking:
            steps.append(
                PlanStep(
                    tool_name="rank_opportunities",
                    permission=ToolPermission.RANK,
                    description="Rank candidates personalized to user profile and preferences.",
                )
            )

        # Validate all planned permissions with guardrails
        for step in steps:
            ToolPermissionGuardrails.validate_tool_permission(step.permission)

        return ExecutionPlan(
            intent=intent,
            steps=steps,
            requires_live_search=requires_search,
            requires_profile=intent.requires_profile,
            target_opportunity_ids=target_ids,
            explanation="Execute new search, eligibility evaluation, and ranking pipeline.",
        )
