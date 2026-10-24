"""Conversational orchestrator executing the 8-stage grounded discovery pipeline."""

from __future__ import annotations

from typing import Any

from app.ai.conversation.context import ConversationContext, ProfileContextBuilder
from app.ai.conversation.intent import ConversationalIntentClassifier
from app.ai.conversation.planner import AssistantPlanner
from app.ai.conversation.response_generator import GroundedResponseGenerator
from app.ai.conversation.safety import PromptInjectionDefense
from app.ai.conversation.schemas import (
    AssistantIntentType,
    AssistantResponse,
    AssistantResponseType,
)
from app.ai.conversation.tools import AssistantTools
from app.ai.conversation.validators import ResponseGroundingValidator


class ConversationalOrchestrator:
    """Orchestrates multi-stage conversational discovery with strict verification."""

    def __init__(
        self,
        classifier: ConversationalIntentClassifier | None = None,
        planner: AssistantPlanner | None = None,
        tools: AssistantTools | None = None,
        response_generator: GroundedResponseGenerator | None = None,
        candidate_catalog: list[Any] | None = None,
    ) -> None:
        self.classifier = classifier or ConversationalIntentClassifier()
        self.planner = planner or AssistantPlanner()
        self.tools = tools or AssistantTools()
        self.generator = response_generator or GroundedResponseGenerator()
        self.candidate_catalog = candidate_catalog or []

    async def handle_turn(
        self,
        message: str,
        context: ConversationContext,
        profile: Any | None = None,
        page: int = 1,
        page_size: int = 5,
    ) -> AssistantResponse:
        """Executes the 8-stage grounded conversational pipeline."""
        # STAGE 1: Input Normalization & Injection Defense
        if PromptInjectionDefense.is_potential_injection(message):
            return AssistantResponse(
                conversation_id=context.conversation_id,
                response_type=AssistantResponseType.TEXT,
                message=(
                    "Your request contains instructions or patterns that violate safety policies. "
                    "Please ask questions related to scholarships and opportunities."
                ),
            )

        context.add_message("user", message)

        # STAGE 2: Intent Classification & Reference Resolution
        intent = self.classifier.classify(message, context)

        # STAGE 3: Plan Formulation (Existing Results First)
        plan = self.planner.plan(intent, context)

        # STAGE 4: Authorized Tool Execution
        execution_data: dict[str, Any] = {
            "page": page,
            "page_size": page_size,
        }

        # Handle candidate pool
        active_pool = list(context.active_opportunities)
        combined_pool = active_pool if active_pool else list(self.candidate_catalog)

        # Execute planned steps
        for step in plan.steps:
            if step.tool_name == "search_opportunities":
                filters = step.parameters.get("filters", {})
                query = step.parameters.get("query", message)
                opps = await self.tools.search_opportunities(
                    query=query,
                    filters=filters,
                    limit=10,
                    candidate_pool=combined_pool
                    if not plan.requires_live_search
                    else self.candidate_catalog or combined_pool,
                )
                execution_data["opportunities"] = opps

            elif step.tool_name == "retrieve_opportunity":
                target_ids = step.parameters.get("opportunity_ids", [])
                target_opps = []
                for opp_id in target_ids:
                    found = await self.tools.retrieve_opportunity(
                        opp_id, candidate_pool=combined_pool
                    )
                    if found:
                        target_opps.append(found)
                execution_data["target_opportunities"] = target_opps
                if target_opps:
                    execution_data["target_opportunity"] = target_opps[0]

            elif step.tool_name == "check_eligibility":
                target_ids = step.parameters.get("opportunity_ids", [])
                target_opp = None
                if target_ids:
                    target_opp = await self.tools.retrieve_opportunity(
                        target_ids[0], candidate_pool=combined_pool
                    )
                elif combined_pool:
                    target_opp = combined_pool[0]

                if target_opp and profile:
                    minimal_profile = ProfileContextBuilder.build_minimal_context(profile)
                    elig = await self.tools.check_eligibility(
                        opportunity=target_opp,
                        profile=minimal_profile,
                    )
                    execution_data["eligibility_result"] = elig
                    execution_data["target_opportunity"] = target_opp
                    context.active_eligibility_map[
                        str(
                            getattr(target_opp, "id", None)
                            or getattr(target_opp, "canonical_key", "")
                        )
                    ] = elig

            elif step.tool_name == "rank_opportunities":
                opps_to_rank = execution_data.get("opportunities", combined_pool)
                if opps_to_rank:
                    ranked_result = await self.tools.rank_opportunities(
                        opportunities=opps_to_rank,
                        profile=profile,
                        search_intent=intent.search_intent,
                        user_preferences=context.user_preferences,
                        eligibility_results=list(context.active_eligibility_map.values()),
                    )
                    execution_data["ranked_result"] = ranked_result
                    execution_data["ranked_opportunities"] = ranked_result.opportunities
                    context.active_ranking_result = ranked_result

            elif step.tool_name == "compare_opportunities":
                target_ids = step.parameters.get("opportunity_ids", [])
                opps_to_comp: list[Any] = []
                pool_to_search = list(context.active_opportunities) + [
                    o for o in self.candidate_catalog if o not in context.active_opportunities
                ]
                for tid in target_ids:
                    opp = await self.tools.retrieve_opportunity(tid, candidate_pool=pool_to_search)
                    if opp and opp not in opps_to_comp:
                        opps_to_comp.append(opp)
                if len(opps_to_comp) < 2:
                    for cand in pool_to_search:
                        if cand not in opps_to_comp:
                            opps_to_comp.append(cand)
                        if len(opps_to_comp) >= 2:
                            break

                comp_result = self.tools.compare_opportunities(
                    opportunities=opps_to_comp,
                    fields=step.parameters.get("fields"),
                )
                execution_data["comparison_result"] = comp_result

        # STAGE 5: Context & Memory State Update
        if "ranked_opportunities" in execution_data:
            context.active_opportunities = execution_data["ranked_opportunities"]
        elif "opportunities" in execution_data and execution_data["opportunities"]:
            context.active_opportunities = execution_data["opportunities"]

        if intent.intent_type == AssistantIntentType.SEARCH_OPPORTUNITIES:
            context.active_search_query = message
            context.active_search_intent = intent.search_intent

        # STAGE 6 & 7: Evidence Assembly & Grounded Response Generation
        raw_response = self.generator.generate_response(
            intent=intent,
            context=context,
            execution_data=execution_data,
        )

        # STAGE 8: Post-Generation Grounding Validation
        verified_opps = (
            execution_data.get("target_opportunities")
            or execution_data.get("ranked_opportunities")
            or execution_data.get("opportunities")
            or context.active_opportunities
        )
        validated_response = ResponseGroundingValidator.validate_and_filter(
            response=raw_response,
            verified_opportunities=verified_opps,
        )

        context.add_message("assistant", validated_response.message)
        return validated_response
