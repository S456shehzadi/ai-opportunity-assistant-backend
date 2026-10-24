"""REST API endpoints for Personalized Opportunity Ranking & Recommendations."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.query.intent_schemas import SearchIntent
from app.api.dependencies import get_current_user, get_optional_db
from app.models.opportunity import Opportunity
from app.models.ranking import RecommendationSnapshot
from app.models.user import User
from app.opportunities.eligibility.engine import EligibilityEngine
from app.opportunities.eligibility.profile_adapter import ProfileAdapter, UnifiedUserFacts
from app.opportunities.eligibility.schemas import EligibilityResult
from app.opportunities.extraction.schemas import ExtractedOpportunity
from app.opportunities.ranking.engine import PersonalizedRankingEngine
from app.opportunities.ranking.schemas import (
    OpportunityRankingContext,
    RankedOpportunityResult,
    SortMode,
    UserPreference,
)
from app.opportunities.schemas.opportunity import OpportunityRead
from app.schemas.ai_profile import NormalizedAIProfile
from app.services.profile_normalizer import ProfileNormalizer

router = APIRouter(prefix="", tags=["Personalized Opportunity Discovery & Ranking"])
ranking_engine = PersonalizedRankingEngine()
eligibility_engine = EligibilityEngine()


class RankOpportunitiesPayload(BaseModel):
    """Request payload for ranking opportunity candidates."""

    user_id: uuid.UUID | None = None
    profile: NormalizedAIProfile | dict[str, Any] | None = None
    opportunity_ids: list[str] = Field(default_factory=list)
    opportunities: list[ExtractedOpportunity | OpportunityRead | dict[str, Any]] = Field(
        default_factory=list
    )
    preferences: list[UserPreference] = Field(default_factory=list)
    search_intent: SearchIntent | None = None
    sort_mode: SortMode = SortMode.RELEVANCE
    include_ineligible: bool = False
    session_id: str | None = None


@router.post(
    "/opportunities/rank",
    response_model=RankedOpportunityResult,
    summary="Rank opportunities transparently for a personalized user context",
)
async def rank_opportunities(
    payload: RankOpportunitiesPayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession | None = Depends(get_optional_db),
) -> RankedOpportunityResult:
    """Produces an explainable ordering of opportunities based on preferences and fit."""
    # 1. Resolve Profile & User Facts
    normalized_profile: NormalizedAIProfile | None = None
    user_facts: UnifiedUserFacts | None = None
    effective_user_id = payload.user_id or (current_user.id if current_user else None)

    if payload.profile is not None:
        if isinstance(payload.profile, NormalizedAIProfile):
            normalized_profile = payload.profile
            user_facts = ProfileAdapter.adapt(normalized_profile)
        elif isinstance(payload.profile, dict):
            try:
                normalized_profile = NormalizedAIProfile.model_validate(payload.profile)
                user_facts = ProfileAdapter.adapt(normalized_profile)
            except Exception:
                user_facts = ProfileAdapter.adapt(payload.profile)
    elif effective_user_id is not None and db is not None:
        from app.repositories.profile_repository import ProfileRepository

        repo = ProfileRepository(db)
        full_user = await repo.get_full_user_profile(effective_user_id)
        if full_user:
            normalized_profile = ProfileNormalizer.normalize_ai_profile(full_user)
            user_facts = ProfileAdapter.adapt(normalized_profile)

    # 2. Resolve Candidate Opportunities
    candidates: list[Any] = []
    for opp_item in payload.opportunities:
        if isinstance(opp_item, (ExtractedOpportunity, OpportunityRead)):
            candidates.append(opp_item)
        elif isinstance(opp_item, dict):
            try:
                candidates.append(ExtractedOpportunity.model_validate(opp_item))
            except Exception:
                try:
                    candidates.append(OpportunityRead.model_validate(opp_item))
                except Exception:
                    pass

    # Resolve from DB if IDs provided
    if payload.opportunity_ids and db is not None:
        valid_uuids: list[uuid.UUID] = []
        for oid in payload.opportunity_ids:
            try:
                valid_uuids.append(uuid.UUID(oid))
            except ValueError:
                pass
        if valid_uuids:
            stmt = select(Opportunity).where(Opportunity.id.in_(valid_uuids))
            res = await db.execute(stmt)
            db_opps = res.scalars().all()
            for opp_entity in db_opps:
                candidates.append(opp_entity)

    if not candidates:
        return RankedOpportunityResult(
            opportunities=[],
            total_evaluated=0,
            filtered_out_count=0,
            sort_mode=payload.sort_mode,
            engine_version=ranking_engine.ENGINE_VERSION,
            config_version=ranking_engine.weights_config.version_hash(),
            cache_key="",
            created_at=datetime.now(UTC),
        )

    # 3. Compute or resolve eligibility for candidates
    eligibility_map: dict[str, EligibilityResult] = {}
    profile_for_elig = normalized_profile if normalized_profile is not None else payload.profile
    if profile_for_elig is not None:
        for c in candidates:
            c_id = getattr(c, "id", None) or getattr(c, "canonical_key", None)
            if c_id:
                try:
                    elig_res = await eligibility_engine.evaluate(profile_for_elig, c)
                    eligibility_map[str(c_id)] = elig_res
                except Exception:
                    pass

    # 4. Execute Ranking
    ranking_context = OpportunityRankingContext(
        normalized_profile=normalized_profile,
        user_facts=user_facts,
        preferences=payload.preferences,
        search_intent=payload.search_intent,
        opportunities=candidates,
        eligibility_results=eligibility_map,
        sort_mode=payload.sort_mode,
        include_ineligible=payload.include_ineligible,
        session_id=payload.session_id,
    )

    result = ranking_engine.rank(ranking_context)

    # 5. Optional DB Persistence
    if db is not None and payload.session_id:
        try:
            snapshot = RecommendationSnapshot(
                user_id=payload.user_id,
                search_session_id=payload.session_id,
                sort_mode=payload.sort_mode.value,
                query_text=payload.search_intent.original_query if payload.search_intent else None,
                ranked_opportunity_ids=[r.opportunity_id for r in result.opportunities],
                cache_key=result.cache_key,
                total_count=len(result.opportunities),
                snapshot_data=result.model_dump(mode="json"),
            )
            db.add(snapshot)
            await db.commit()
        except Exception:
            await db.rollback()

    return result
