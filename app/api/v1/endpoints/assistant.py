"""REST API endpoint for Grounded AI Opportunity Assistant."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.conversation.assistant import OpportunityAssistant
from app.ai.conversation.schemas import AssistantResponse, ChatRequestPayload
from app.api.dependencies import get_current_user, get_optional_db
from app.models.opportunity import Opportunity
from app.models.user import User
from app.services.profile_normalizer import ProfileNormalizer

router = APIRouter(prefix="", tags=["Grounded AI Opportunity Assistant"])
assistant_service = OpportunityAssistant()


@router.post(
    "/assistant/chat",
    response_model=AssistantResponse,
    summary="Engage with the grounded AI opportunity discovery assistant",
)
async def chat_with_assistant(
    payload: ChatRequestPayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession | None = Depends(get_optional_db),
) -> AssistantResponse:
    """Processes a conversational turn with zero hallucination and evidence citations."""
    profile_data = None
    opportunities_pool = []
    effective_user_id = payload.user_id or (current_user.id if current_user else None)

    if db is not None:
        # Load profile if user is authenticated or user_id is provided
        if effective_user_id:
            from app.repositories.profile_repository import ProfileRepository

            repo = ProfileRepository(db)
            full_user = await repo.get_full_user_profile(effective_user_id)
            if full_user:
                profile_data = ProfileNormalizer.normalize(full_user)

        # Load active catalog opportunities to enrich candidate pool
        from sqlalchemy.orm import selectinload
        from app.schemas.opportunity import OpportunityRead

        opp_res = await db.execute(
            select(Opportunity)
            .options(
                selectinload(Opportunity.requirements),
                selectinload(Opportunity.sources),
                selectinload(Opportunity.evidences),
            )
            .limit(50)
        )
        opportunities_pool = [OpportunityRead.model_validate(opp) for opp in opp_res.scalars().all()]

    if opportunities_pool:
        assistant_service.orchestrator.candidate_catalog = opportunities_pool

    return await assistant_service.chat(payload, profile=profile_data)
