"""Grounded natural-language and structured response generator."""

from __future__ import annotations

from typing import Any

from app.ai.conversation.citations import CitationService
from app.ai.conversation.context import ConversationContext
from app.ai.conversation.evidence_selector import EvidenceSelector
from app.ai.conversation.prompts import (
    CLARIFICATION_TEMPLATE,
    OUT_OF_DOMAIN_TEMPLATE,
    PROMPT_VERSION,
)
from app.ai.conversation.schemas import (
    AssistantIntent,
    AssistantIntentType,
    AssistantResponse,
    AssistantResponseType,
    CitationItem,
    ComparisonResult,
    OpportunitySearchPage,
    OpportunitySummary,
)
from app.opportunities.eligibility.schemas import EligibilityResult, OverallEligibilityStatus


class GroundedResponseGenerator:
    """Synthesizes structured, zero-hallucination conversational responses."""

    def __init__(self, prompt_version: str = PROMPT_VERSION) -> None:
        self.prompt_version = prompt_version

    def generate_response(
        self,
        intent: AssistantIntent,
        context: ConversationContext,
        execution_data: dict[str, Any],
    ) -> AssistantResponse:
        """Synthesizes an AssistantResponse strictly from verified execution data."""
        conv_id = context.conversation_id

        # 1. Clarification Required
        if intent.intent_type == AssistantIntentType.CLARIFICATION_REQUIRED:
            return AssistantResponse(
                conversation_id=conv_id,
                response_type=AssistantResponseType.CLARIFICATION,
                message=CLARIFICATION_TEMPLATE,
                clarification_prompt=CLARIFICATION_TEMPLATE,
                follow_up_options=[
                    "Master's in Computer Science in Germany",
                    "Fully funded PhD in USA",
                    "Undergraduate scholarships for international students",
                ],
                prompt_version=self.prompt_version,
            )

        # 2. Unknown / Out of Domain / Greetings
        if intent.intent_type == AssistantIntentType.UNKNOWN:
            import re
            cleaned = intent.raw_query.strip().lower()
            if re.search(r"^(hi|hello|hey|good\s+morning|good\s+evening|greetings|salam|assalam.*|hey\s+there)$", cleaned):
                return AssistantResponse(
                    conversation_id=conv_id,
                    response_type=AssistantResponseType.TEXT,
                    message=(
                        "Hello! I am your AI Opportunity Assistant. "
                        "I specialize in finding fully funded scholarships, grants, fellowships, and internships tailored to your profile.\n\n"
                        "Tell me about your desired degree, target country, or field of study, and I'll find matching opportunities for you!"
                    ),
                    follow_up_options=[
                        "Fully funded Master's scholarships",
                        "PhD fellowships in Europe",
                        "Undergraduate summer research internships",
                    ],
                    prompt_version=self.prompt_version,
                )
            return AssistantResponse(
                conversation_id=conv_id,
                response_type=AssistantResponseType.TEXT,
                message=OUT_OF_DOMAIN_TEMPLATE,
                prompt_version=self.prompt_version,
            )

        # 3. Preference Updates
        if intent.intent_type == AssistantIntentType.UPDATE_PREFERENCES:
            return AssistantResponse(
                conversation_id=conv_id,
                response_type=AssistantResponseType.TEXT,
                message=(
                    "Got it! I have updated your preferences. "
                    "Future recommendations will prioritize them."
                ),
                follow_up_options=["Search opportunities matching my preferences"],
                prompt_version=self.prompt_version,
            )

        # 4. Show Saved
        if intent.intent_type == AssistantIntentType.SHOW_SAVED:
            saved_opps = execution_data.get("saved_opportunities", [])
            summaries = [self._build_summary(o) for o in saved_opps]
            msg = (
                f"You have {len(summaries)} saved opportunities."
                if summaries
                else (
                    "You have no saved opportunities yet. "
                    "When you find an opportunity you like, you can bookmark it."
                )
            )
            return AssistantResponse(
                conversation_id=conv_id,
                response_type=AssistantResponseType.OPPORTUNITY_LIST,
                message=msg,
                opportunities=summaries,
                search_page=OpportunitySearchPage(
                    items=summaries, page=1, page_size=len(summaries) or 5, total=len(summaries)
                ),
                prompt_version=self.prompt_version,
            )

        # 5. Comparison
        if intent.intent_type == AssistantIntentType.COMPARE_OPPORTUNITIES:
            comp_result: ComparisonResult = execution_data.get(
                "comparison_result",
                ComparisonResult(opportunity_ids=[], opportunity_titles=[], comparison_fields=[]),
            )
            titles_str = " and ".join(comp_result.opportunity_titles)
            msg_lines = [f"Here is a side-by-side comparison between **{titles_str}**:\n"]
            if comp_result.differences:
                msg_lines.append("**Key Differences:**")
                for diff in comp_result.differences:
                    msg_lines.append(f"- {diff}")
                msg_lines.append("")
            if comp_result.similarities:
                msg_lines.append("**Similarities:**")
                for sim in comp_result.similarities:
                    msg_lines.append(f"- {sim}")

            return AssistantResponse(
                conversation_id=conv_id,
                response_type=AssistantResponseType.COMPARISON,
                message="\n".join(msg_lines),
                comparison=comp_result,
                citations=comp_result.sources,
                follow_up_options=[
                    "Check my eligibility for both",
                    "Which has an earlier deadline?",
                    "How do I apply for the first one?",
                ],
                prompt_version=self.prompt_version,
            )

        # 6. Eligibility Check / Profile Gap
        if intent.intent_type in (
            AssistantIntentType.CHECK_ELIGIBILITY,
            AssistantIntentType.PROFILE_GAP,
        ):
            elig_result: EligibilityResult | None = execution_data.get("eligibility_result")
            opp = execution_data.get("target_opportunity")
            opp_title = (
                self._get_val(opp, "title", "this opportunity") if opp else "this opportunity"
            )

            if not elig_result:
                msg = f"I could not retrieve eligibility criteria for {opp_title}."
                return AssistantResponse(
                    conversation_id=conv_id,
                    response_type=AssistantResponseType.TEXT,
                    message=msg,
                    prompt_version=self.prompt_version,
                )

            status_str = elig_result.overall_status.value.replace("_", " ").title()
            msg_parts = [
                f"### Eligibility Assessment for **{opp_title}**",
                f"**Overall Status:** {status_str}",
                "",
            ]

            summary = getattr(elig_result, "personalized_intelligence", None) or getattr(
                elig_result, "personalized_summary", None
            )
            if summary:
                if summary.satisfied_requirements:
                    msg_parts.append("**Requirements You Satisfy:**")
                    for s in summary.satisfied_requirements:
                        msg_parts.append(f"- [x] {s}")
                    msg_parts.append("")

                blocking = getattr(summary, "unsatisfied_requirements", None) or getattr(
                    summary, "blocking_requirements", []
                )
                if blocking:
                    msg_parts.append("**Unmet / Blocking Criteria:**")
                    for b in blocking:
                        msg_parts.append(f"- [ ] {b}")
                    msg_parts.append("")

                if summary.unknown_requirements:
                    msg_parts.append("**Criteria Needing Verification or More Info:**")
                    for u in summary.unknown_requirements:
                        msg_parts.append(f"- [?] {u}")
                    msg_parts.append("")

            citations = EvidenceSelector.select_evidence_for_opportunity(opp) if opp else []
            return AssistantResponse(
                conversation_id=conv_id,
                response_type=AssistantResponseType.ELIGIBILITY_EXPLANATION,
                message="\n".join(msg_parts),
                citations=citations,
                follow_up_options=[
                    "What am I missing to qualify?",
                    "Find similar opportunities",
                    "How do I apply?",
                ],
                prompt_version=self.prompt_version,
            )

        # 7. Opportunity Specific Field Question (Deadline, Requirement, Funding, Application)
        if intent.intent_type in (
            AssistantIntentType.CHECK_DEADLINE,
            AssistantIntentType.CHECK_REQUIREMENT,
            AssistantIntentType.CHECK_FUNDING,
            AssistantIntentType.CHECK_APPLICATION,
            AssistantIntentType.EXPLAIN_OPPORTUNITY,
        ):
            target_opps = execution_data.get("target_opportunities", [])
            if not target_opps and execution_data.get("target_opportunity"):
                target_opps = [execution_data["target_opportunity"]]

            if not target_opps:
                return AssistantResponse(
                    conversation_id=conv_id,
                    response_type=AssistantResponseType.TEXT,
                    message=(
                        "I couldn't identify which opportunity you're referring to. "
                        "Please specify the name or number."
                    ),
                    prompt_version=self.prompt_version,
                )

            opp = target_opps[0]
            citations = EvidenceSelector.select_evidence_for_opportunity(opp)

            msg = self._format_field_answer(intent.intent_type, opp)
            return AssistantResponse(
                conversation_id=conv_id,
                response_type=AssistantResponseType.OPPORTUNITY_DETAIL,
                message=msg,
                opportunities=[self._build_summary(opp)],
                citations=citations,
                follow_up_options=[
                    "Check my eligibility",
                    "Compare with other opportunities",
                    "When does application open?",
                ],
                prompt_version=self.prompt_version,
            )

        # 8. Search / Refine Search / Similar Opportunities
        opps = execution_data.get("ranked_opportunities") or execution_data.get("opportunities", [])
        summaries = [self._build_summary(o) for o in opps]
        citations: list[CitationItem] = []
        for o in opps[:3]:
            citations.extend(EvidenceSelector.select_evidence_for_opportunity(o))
        citations = CitationService.rank_citations(citations)[:5]

        page_num = execution_data.get("page", 1)
        page_size = execution_data.get("page_size", 5)
        total = len(summaries)
        start_idx = (page_num - 1) * page_size
        end_idx = start_idx + page_size
        paged_items = summaries[start_idx:end_idx]

        if not paged_items:
            msg = (
                "I couldn't find any opportunities matching your exact criteria. "
                "You can try broadening your search or adjusting your filters."
            )
        else:
            msg = (
                f"I found **{total}** opportunities matching your request. "
                "Here are the top results:"
            )

        return AssistantResponse(
            conversation_id=conv_id,
            response_type=AssistantResponseType.OPPORTUNITY_LIST,
            message=msg,
            opportunities=paged_items,
            citations=citations,
            search_page=OpportunitySearchPage(
                items=paged_items,
                page=page_num,
                page_size=page_size,
                total=total,
                has_more=end_idx < total,
            ),
            follow_up_options=[
                "Am I eligible for the top match?",
                "Which ones don't require IELTS?",
                "Compare the first two",
            ],
            prompt_version=self.prompt_version,
        )

    def _build_summary(self, opp: Any) -> OpportunitySummary:
        """Constructs a clean UI-ready OpportunitySummary."""
        nested = getattr(opp, "opportunity", None)
        opp_id = str(
            self._get_val(opp, "opportunity_id", "")
            or self._get_val(opp, "id", "")
            or self._get_val(opp, "canonical_key", "")
            or (self._get_val(nested, "id", "") if nested else "")
        )
        title = str(self._get_val(opp, "title", "Untitled"))
        org = str(
            self._get_val(opp, "organization", "")
            or (self._get_val(nested, "organization", "") if nested else "Unknown Organization")
        )
        cat = str(
            self._get_val(opp, "category", "")
            or (self._get_val(nested, "category", "") if nested else "Scholarship")
        )
        loc = str(
            self._get_val(opp, "host_country", "")
            or (self._get_val(nested, "host_country", "") if nested else "Global")
        )

        funding_type = str(
            self._get_val(opp, "funding_type", "")
            or (self._get_val(nested, "funding_type", "") if nested else "Unknown")
        )
        funding_amt = self._get_val(opp, "funding_amount", "") or (
            self._get_val(nested, "funding_amount", "") if nested else ""
        )
        funding_summary = f"{funding_type} ({funding_amt})" if funding_amt else funding_type

        deadline_val = self._get_val(opp, "deadline") or (
            self._get_val(nested, "deadline") if nested else None
        )
        deadline_str = str(deadline_val) if deadline_val else "Rolling / Not Specified"

        official_url = (
            self._get_val(opp, "official_source_url")
            or self._get_val(opp, "source_url")
            or (self._get_val(nested, "official_source_url") if nested else None)
        )
        elig_status = self._get_val(
            opp, "eligibility_status", OverallEligibilityStatus.POTENTIALLY_ELIGIBLE
        )

        return OpportunitySummary(
            id=opp_id,
            title=title,
            organization=org,
            category=cat,
            location=loc,
            funding_summary=funding_summary,
            deadline=deadline_str,
            eligibility_status=elig_status,
            relevance_summary=f"Matches your criteria for {loc} and {cat}.",
            verification_status="VERIFIED",
            official_url=str(official_url) if official_url else None,
            source=str(self._get_val(opp, "source_domain", "")),
        )

    def _format_field_answer(self, intent_type: AssistantIntentType, opp: Any) -> str:
        title = self._get_val(opp, "title", "Opportunity")
        if intent_type == AssistantIntentType.CHECK_DEADLINE:
            dl = self._get_val(opp, "deadline", "Rolling / Not Specified")
            return f"The official deadline for **{title}** is **{dl}**."
        if intent_type == AssistantIntentType.CHECK_FUNDING:
            ftype = self._get_val(opp, "funding_type", "Not specified")
            famt = self._get_val(opp, "funding_amount", "")
            cov = f"{ftype} ({famt})" if famt else str(ftype)
            return f"**{title}** funding details: **{cov}**."
        if intent_type == AssistantIntentType.CHECK_REQUIREMENT:
            elig = self._get_val(opp, "eligibility", {})
            deg = elig.get("degree_levels", ["Any"])
            gpa = elig.get("min_gpa", "Not specified")
            lang = elig.get("language_requirements", ["See portal"])
            return (
                f"**Requirements for {title}:**\n"
                f"- Degree Levels: {deg}\n"
                f"- Minimum GPA: {gpa}\n"
                f"- Language/Tests: {lang}"
            )
        if intent_type == AssistantIntentType.CHECK_APPLICATION:
            app_url = self._get_val(opp, "application_url") or self._get_val(
                opp, "official_source_url"
            )
            if app_url:
                return f"You can apply for **{title}** via the official portal at: {app_url}"
            return (
                f"Application instructions for **{title}** are available on the official website."
            )

        desc = self._get_val(opp, "description", "No description available.")
        return f"### Overview of {title}\n{desc}"

    def _get_val(self, obj: Any, key: str, default: Any = None) -> Any:
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)
