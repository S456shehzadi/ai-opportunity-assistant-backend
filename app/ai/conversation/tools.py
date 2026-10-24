"""Execution tools for the Grounded AI Opportunity Assistant."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Any

from app.ai.conversation.safety import ToolPermissionGuardrails
from app.ai.conversation.schemas import CitationItem, ComparisonResult, ToolPermission
from app.opportunities.eligibility.engine import EligibilityEngine
from app.opportunities.eligibility.profile_adapter import ProfileAdapter
from app.opportunities.eligibility.schemas import EligibilityResult, RequirementStatus
from app.opportunities.extraction.schemas import ExtractedOpportunity
from app.opportunities.ranking.engine import PersonalizedRankingEngine
from app.opportunities.ranking.schemas import (
    OpportunityRankingContext,
    RankedOpportunityResult,
    UserPreference,
)
from app.opportunities.schemas.opportunity import OpportunityRead
from app.schemas.ai_profile import NormalizedAIProfile


class AssistantTools:
    """Authorized tool execution provider invoked by the assistant orchestrator."""

    def __init__(
        self,
        eligibility_engine: EligibilityEngine | None = None,
        ranking_engine: PersonalizedRankingEngine | None = None,
    ) -> None:
        self.eligibility_engine = eligibility_engine or EligibilityEngine()
        self.ranking_engine = ranking_engine or PersonalizedRankingEngine()

    async def search_opportunities(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
        limit: int = 10,
        candidate_pool: list[Any] | None = None,
    ) -> list[Any]:
        """Searches opportunities matching query and filters within candidate pool."""
        ToolPermissionGuardrails.validate_tool_permission(ToolPermission.SEARCH)
        pool = candidate_pool or []
        filters = filters or {}

        results: list[Any] = []
        tokens = [t.lower() for t in re.findall(r"\w+", query) if len(t) > 2]

        for opp in pool:
            title = str(self._get_val(opp, "title", "")).lower()
            org = str(self._get_val(opp, "organization", "")).lower()
            desc = str(self._get_val(opp, "description", "")).lower()
            country = str(self._get_val(opp, "host_country", "")).lower()
            category = str(self._get_val(opp, "category", "")).lower()
            funding = str(self._get_val(opp, "funding_type", "")).lower()

            # Filter matching
            if filters.get("country"):
                req_country = filters["country"].lower()
                countries_allowed = [
                    str(c).lower() for c in (self._get_val(opp, "countries_allowed", []) or [])
                ]
                if (
                    req_country not in country
                    and "global" not in country
                    and "global" not in countries_allowed
                ):
                    continue
            if filters.get("is_fully_funded"):
                if "fully" not in funding:
                    continue

            # Query token scoring
            score = 0
            if not tokens:
                score = 1
            else:
                for tok in tokens:
                    if tok in title:
                        score += 3
                    elif tok in org or tok in category:
                        score += 2
                    elif tok in desc or tok in country or tok in funding:
                        score += 1

            if score > 0 or not tokens:
                results.append((score, opp))

        results.sort(key=lambda x: x[0], reverse=True)
        if not results and pool:
            return pool[:limit]
        return [item[1] for item in results[:limit]]

    async def retrieve_opportunity(
        self,
        opportunity_id: str,
        candidate_pool: list[Any] | None = None,
    ) -> Any | None:
        """Retrieves a single opportunity by its ID or canonical key."""
        ToolPermissionGuardrails.validate_tool_permission(ToolPermission.RETRIEVE)
        pool = candidate_pool or []
        for opp in pool:
            curr_id = str(self._get_val(opp, "id", "") or self._get_val(opp, "canonical_key", ""))
            if curr_id and curr_id == str(opportunity_id):
                return opp
        return None

    async def check_eligibility(
        self,
        opportunity: Any,
        profile: Any,
    ) -> EligibilityResult:
        """Runs the evidence-driven eligibility engine against user profile."""
        ToolPermissionGuardrails.validate_tool_permission(ToolPermission.CHECK_ELIGIBILITY)
        return await self.eligibility_engine.evaluate(profile=profile, opportunity=opportunity)

    async def rank_opportunities(
        self,
        opportunities: list[Any],
        profile: Any = None,
        search_intent: Any = None,
        user_preferences: list[UserPreference] | None = None,
        eligibility_results: list[EligibilityResult] | dict[str, EligibilityResult] | None = None,
    ) -> RankedOpportunityResult:
        """Runs personalized ranking over candidates with eligibility fit."""
        ToolPermissionGuardrails.validate_tool_permission(ToolPermission.RANK)

        valid_candidates: list[Any] = []
        for opp_item in opportunities:
            if isinstance(opp_item, (ExtractedOpportunity, OpportunityRead)):
                valid_candidates.append(opp_item)
            elif isinstance(opp_item, dict):
                opp_dict = dict(opp_item)
                opp_dict.setdefault("id", opp_dict.get("canonical_key", str(uuid.uuid4())))
                opp_dict.setdefault("created_at", datetime.now(UTC))
                opp_dict.setdefault("updated_at", datetime.now(UTC))
                opp_dict.setdefault("description", opp_dict.get("title", "Opportunity"))
                opp_dict.setdefault(
                    "official_source_url", opp_dict.get("source_url", "https://example.com")
                )
                opp_dict.setdefault("source_domain", "example.com")
                try:
                    valid_candidates.append(OpportunityRead.model_validate(opp_dict))
                except Exception:
                    try:
                        valid_candidates.append(ExtractedOpportunity.model_validate(opp_item))
                    except Exception:
                        pass
            else:
                valid_candidates.append(opp_item)

        elig_map: dict[str, EligibilityResult] = {}
        if isinstance(eligibility_results, dict):
            elig_map = eligibility_results
        elif isinstance(eligibility_results, list):
            for e in eligibility_results:
                if isinstance(e, EligibilityResult):
                    elig_map[e.opportunity_id] = e

        user_facts = None
        norm_profile = None
        if isinstance(profile, NormalizedAIProfile):
            norm_profile = profile
            user_facts = ProfileAdapter.adapt(profile)
        elif profile is not None:
            user_facts = ProfileAdapter.adapt(profile)

        context = OpportunityRankingContext(
            opportunities=valid_candidates,
            eligibility_results=elig_map,
            normalized_profile=norm_profile,
            user_facts=user_facts,
            search_intent=search_intent,
            preferences=user_preferences or [],
        )
        return self.ranking_engine.rank(context)

    def compare_opportunities(
        self,
        opportunities: list[Any],
        fields: list[str] | None = None,
    ) -> ComparisonResult:
        """Constructs an objective side-by-side comparison across opportunities."""
        ToolPermissionGuardrails.validate_tool_permission(ToolPermission.COMPARE)
        if not opportunities:
            return ComparisonResult(
                opportunity_ids=[],
                opportunity_titles=[],
                comparison_fields=[],
            )

        fields = fields or ["organization", "location", "funding", "deadline", "requirements"]
        opp_ids: list[str] = []
        opp_titles: list[str] = []
        table_rows: list[dict[str, Any]] = []
        sources: list[CitationItem] = []

        for opp in opportunities:
            opp_id = str(self._get_val(opp, "id", "") or self._get_val(opp, "canonical_key", ""))
            title = str(self._get_val(opp, "title", "Untitled"))
            opp_ids.append(opp_id)
            opp_titles.append(title)

            source_url = str(
                self._get_val(opp, "official_source_url", "")
                or self._get_val(opp, "source_url", "")
            )
            if source_url:
                sources.append(
                    CitationItem(
                        title=f"{title} Official Page",
                        url=source_url,
                        source_domain=str(self._get_val(opp, "source_domain", "")),
                        trust_tier="HIGH",
                    )
                )

        for field in fields:
            row_data: dict[str, Any] = {"feature": field.replace("_", " ").title()}
            for opp in opportunities:
                opp_id = str(
                    self._get_val(opp, "id", "") or self._get_val(opp, "canonical_key", "")
                )
                val = self._extract_field_value(opp, field)
                row_data[opp_id] = val
            table_rows.append(row_data)

        differences = self._detect_differences(opportunities, fields)
        similarities = self._detect_similarities(opportunities, fields)

        return ComparisonResult(
            opportunity_ids=opp_ids,
            opportunity_titles=opp_titles,
            comparison_fields=fields,
            table_rows=table_rows,
            differences=differences,
            similarities=similarities,
            sources=sources,
        )

    def get_profile_gaps(
        self,
        opportunity: Any,
        eligibility_result: EligibilityResult,
    ) -> dict[str, Any]:
        """Diagnoses unmet or unknown requirements with actionable guidance."""
        ToolPermissionGuardrails.validate_tool_permission(ToolPermission.CHECK_ELIGIBILITY)
        unmet: list[dict[str, Any]] = []
        unknown: list[dict[str, Any]] = []
        satisfied: list[str] = []

        reqs = getattr(eligibility_result, "requirements", None) or getattr(
            eligibility_result, "evaluations", []
        )
        for req in reqs:
            if req.status == RequirementStatus.NO_MATCH:
                unmet.append(
                    {
                        "requirement": req.requirement_description,
                        "required": str(req.required_value),
                        "user_actual": str(req.user_value),
                        "explanation": req.explanation,
                        "blocking": True,
                    }
                )
            elif req.status == RequirementStatus.UNKNOWN or getattr(
                req, "requires_verification", False
            ):
                unknown.append(
                    {
                        "requirement": req.requirement_description,
                        "explanation": req.explanation,
                        "needed_action": "Upload verification document or update profile fact.",
                    }
                )
            elif req.status == RequirementStatus.MATCH:
                satisfied.append(req.requirement_description)

        return {
            "opportunity_id": str(self._get_val(opportunity, "id", "")),
            "opportunity_title": str(self._get_val(opportunity, "title", "")),
            "overall_status": eligibility_result.overall_status.value,
            "unmet_requirements": unmet,
            "unknown_requirements": unknown,
            "satisfied_requirements": satisfied,
            "recommended_actions": [
                (
                    f"Address {u['requirement']}: required {u['required']} "
                    f"(current: {u['user_actual']})"
                )
                for u in unmet
            ]
            + [f"Verify {unk['requirement']}" for unk in unknown],
        }

    def find_similar_opportunities(
        self,
        target: Any,
        candidate_pool: list[Any],
        limit: int = 3,
    ) -> list[Any]:
        """Identifies comparable opportunities based on category, field, and level."""
        ToolPermissionGuardrails.validate_tool_permission(ToolPermission.SEARCH)
        target_id = str(
            self._get_val(target, "id", "") or self._get_val(target, "canonical_key", "")
        )
        target_cat = str(self._get_val(target, "category", "")).lower()
        target_funding = str(self._get_val(target, "funding_type", "")).lower()

        scored: list[tuple[int, Any]] = []
        for opp in candidate_pool:
            opp_id = str(self._get_val(opp, "id", "") or self._get_val(opp, "canonical_key", ""))
            if opp_id == target_id:
                continue

            score = 0
            if str(self._get_val(opp, "category", "")).lower() == target_cat:
                score += 3
            if str(self._get_val(opp, "funding_type", "")).lower() == target_funding:
                score += 2

            scored.append((score, opp))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:limit]]

    def _get_val(self, obj: Any, key: str, default: Any = None) -> Any:
        if isinstance(obj, dict):
            val = obj.get(key)
            if val is not None:
                return val
            if key == "host_country":
                return obj.get("country", default)
            return default
        val = getattr(obj, key, None)
        if val is not None:
            return val
        if key == "host_country":
            return getattr(obj, "country", default)
        return default

    def _extract_field_value(self, opp: Any, field: str) -> str:
        f = field.lower()
        if "org" in f:
            return str(self._get_val(opp, "organization", "Not specified"))
        if "location" in f or "country" in f:
            return str(self._get_val(opp, "host_country", "Global"))
        if "funding" in f or "stipend" in f:
            ftype = str(self._get_val(opp, "funding_type", "Unknown"))
            famt = str(self._get_val(opp, "funding_amount", "") or "")
            return f"{ftype} ({famt})" if famt else ftype
        if "deadline" in f or "date" in f:
            return str(self._get_val(opp, "deadline", "Open / Rolling"))
        if "req" in f or "eligibility" in f:
            elig = self._get_val(opp, "eligibility", {})
            if isinstance(elig, dict):
                degrees = elig.get("degree_levels", [])
                gpa = elig.get("min_gpa")
                parts = []
                if degrees:
                    parts.append(f"Degrees: {', '.join(degrees)}")
                if gpa:
                    parts.append(f"Min GPA: {gpa}")
                return "; ".join(parts) if parts else "See official portal"
            return str(elig)
        return str(self._get_val(opp, field, "N/A"))

    def _detect_differences(self, opportunities: list[Any], fields: list[str]) -> list[str]:
        diffs = []
        for f in fields:
            vals = {self._extract_field_value(opp, f) for opp in opportunities}
            if len(vals) > 1:
                diffs.append(f"Different {f.replace('_', ' ')}: {' vs '.join(vals)}")
        return diffs

    def _detect_similarities(self, opportunities: list[Any], fields: list[str]) -> list[str]:
        sims = []
        for f in fields:
            vals = {self._extract_field_value(opp, f) for opp in opportunities}
            if len(vals) == 1:
                sims.append(f"Same {f.replace('_', ' ')}: {next(iter(vals))}")
        return sims
