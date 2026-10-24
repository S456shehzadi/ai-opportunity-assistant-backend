"""REST API endpoints for AI Eligibility Matching & Personalized Opportunity Intelligence."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user_id, get_optional_db
from app.models.opportunity import Opportunity
from app.models.profile import UserProfile
from app.opportunities.eligibility.engine import EligibilityEngine
from app.opportunities.eligibility.schemas import EligibilityResult
from app.opportunities.extraction.schemas import ExtractedOpportunity
from app.schemas.ai_profile import NormalizedAIProfile
from app.services.profile_normalizer import ProfileNormalizer

router = APIRouter(prefix="", tags=["AI Eligibility Intelligence"])
engine = EligibilityEngine()


class EvaluateEligibilityPayload(BaseModel):
    """Payload for evaluating eligibility with either IDs or inline data models."""

    user_id: uuid.UUID | None = None
    opportunity_id: str | None = None
    profile: NormalizedAIProfile | dict[str, Any] | None = None
    opportunity: ExtractedOpportunity | dict[str, Any] | None = None


class BatchEligibilityPayload(BaseModel):
    """Payload for multi-opportunity batch eligibility evaluation."""

    user_id: uuid.UUID | None = None
    profile: NormalizedAIProfile | dict[str, Any] | None = None
    opportunity_ids: list[str] = Field(default_factory=list)
    opportunities: list[ExtractedOpportunity | dict[str, Any]] = Field(default_factory=list)


@router.post(
    "/opportunities/{opportunity_id}/eligibility",
    response_model=EligibilityResult,
    summary="Evaluate eligibility of the authenticated user for a specific opportunity",
)
async def evaluate_opportunity_eligibility(
    opportunity_id: str,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession | None = Depends(get_optional_db),
) -> EligibilityResult:
    """Evaluates the user's normalized profile against the target opportunity."""
    if not db:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database session required to resolve stored entities.",
        )

    # 1. Fetch user profile
    stmt = select(UserProfile).where(UserProfile.user_id == user_id)
    res = await db.execute(stmt)
    user_prof = res.scalar_one_or_none()
    if not user_prof:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User profile not found for user {user_id}",
        )

    normalized_profile = ProfileNormalizer.normalize_ai_profile(
        user_id=user_id,
        email=getattr(user_prof.user, "email", "user@example.com")
        if hasattr(user_prof, "user")
        else "",
        profile=user_prof,
    )

    # 2. Fetch opportunity
    try:
        opp_uuid = uuid.UUID(opportunity_id)
        opp_stmt = select(Opportunity).where(Opportunity.id == opp_uuid)
    except ValueError:
        opp_stmt = select(Opportunity).where(Opportunity.canonical_key == opportunity_id)

    opp_res = await db.execute(opp_stmt)
    opp_record = opp_res.scalar_one_or_none()
    if not opp_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Opportunity {opportunity_id} not found",
        )

    return await engine.evaluate(normalized_profile, opp_record)


@router.post(
    "/eligibility/evaluate",
    response_model=EligibilityResult,
    summary="Direct evaluation of user facts against opportunity criteria",
)
async def direct_evaluate_eligibility(
    payload: EvaluateEligibilityPayload,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession | None = Depends(get_optional_db),
) -> EligibilityResult:
    """Accepts either full inline payloads or entity IDs to compute eligibility."""
    resolved_profile = payload.profile
    resolved_opportunity = payload.opportunity

    if resolved_profile is None:
        target_uid = payload.user_id or user_id
        if db:
            stmt = select(UserProfile).where(UserProfile.user_id == target_uid)
            res = await db.execute(stmt)
            user_prof = res.scalar_one_or_none()
            if user_prof:
                resolved_profile = ProfileNormalizer.normalize_ai_profile(
                    user_id=target_uid,
                    email="user@example.com",
                    profile=user_prof,
                )
        if resolved_profile is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either 'profile' payload or a valid user profile must be available.",
            )

    if resolved_opportunity is None:
        if not payload.opportunity_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either 'opportunity' payload or 'opportunity_id' must be provided.",
            )
        if db:
            try:
                opp_uuid = uuid.UUID(payload.opportunity_id)
                opp_stmt = select(Opportunity).where(Opportunity.id == opp_uuid)
            except ValueError:
                opp_stmt = select(Opportunity).where(
                    Opportunity.canonical_key == payload.opportunity_id
                )
            opp_res = await db.execute(opp_stmt)
            resolved_opportunity = opp_res.scalar_one_or_none()

        if resolved_opportunity is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Opportunity {payload.opportunity_id} could not be resolved.",
            )

    return await engine.evaluate(resolved_profile, resolved_opportunity)


@router.post(
    "/eligibility/batch",
    response_model=list[EligibilityResult],
    summary="Batch evaluate multiple opportunities with controlled concurrency",
)
async def batch_evaluate_eligibility(
    payload: BatchEligibilityPayload,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession | None = Depends(get_optional_db),
) -> list[EligibilityResult]:
    """Evaluates multiple opportunities against one user profile."""
    resolved_profile = payload.profile
    if resolved_profile is None:
        target_uid = payload.user_id or user_id
        if db:
            stmt = select(UserProfile).where(UserProfile.user_id == target_uid)
            res = await db.execute(stmt)
            user_prof = res.scalar_one_or_none()
            if user_prof:
                resolved_profile = ProfileNormalizer.normalize_ai_profile(
                    user_id=target_uid,
                    email="user@example.com",
                    profile=user_prof,
                )
        if resolved_profile is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User profile must be provided or exist in database.",
            )

    targets: list[Any] = list(payload.opportunities)
    if payload.opportunity_ids and db:
        for opp_id in payload.opportunity_ids:
            try:
                opp_uuid = uuid.UUID(opp_id)
                opp_stmt = select(Opportunity).where(Opportunity.id == opp_uuid)
            except ValueError:
                opp_stmt = select(Opportunity).where(Opportunity.canonical_key == opp_id)
            opp_res = await db.execute(opp_stmt)
            rec = opp_res.scalar_one_or_none()
            if rec:
                targets.append(rec)

    if not targets:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one opportunity or opportunity_id must be provided.",
        )

    return await engine.evaluate_batch(resolved_profile, targets)
