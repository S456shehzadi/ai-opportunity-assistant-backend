"""REST API endpoints for opportunity and search monitoring."""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db
from app.models.opportunity import Opportunity
from app.models.user import User
from app.monitoring.models.subscription import (
    MonitoringFrequency,
    MonitoringStatus,
    OpportunitySubscription,
    SearchSubscription,
)
from app.monitoring.policies.frequency_policy import MonitoringFrequencyPolicy
from app.monitoring.schemas.monitoring import MonitoringRunSummary
from app.monitoring.schemas.subscription import (
    OpportunitySubscriptionCreate,
    OpportunitySubscriptionResponse,
    SearchSubscriptionCreate,
    SearchSubscriptionResponse,
)
from app.monitoring.services.monitoring_engine import OpportunityMonitoringEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["Opportunity Monitoring"])
monitoring_engine = OpportunityMonitoringEngine()


@router.post(
    "/opportunities/{id}/monitor",
    response_model=OpportunitySubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Subscribe to continuous monitoring of an opportunity",
)
async def monitor_opportunity(
    id: UUID,
    payload: OpportunitySubscriptionCreate | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OpportunitySubscriptionResponse:
    """Subscribes the current user to automated change and deadline monitoring."""
    # Verify opportunity exists
    opp_query = select(Opportunity).where(Opportunity.id == id)
    opp_res = await db.execute(opp_query)
    opp = opp_res.scalar_one_or_none()
    if not opp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Opportunity {id} not found",
        )

    # Check for existing subscription
    sub_query = select(OpportunitySubscription).where(
        OpportunitySubscription.user_id == current_user.id,
        OpportunitySubscription.opportunity_id == id,
    )
    sub_res = await db.execute(sub_query)
    sub = sub_res.scalar_one_or_none()

    freq = payload.monitoring_frequency if payload else MonitoringFrequency.DAILY
    freq_calc = MonitoringFrequencyPolicy.calculate_next_check(
        current_deadline=opp.deadline,
        last_changed_at=None,
        user_preference=freq,
    )

    if sub:
        sub.monitoring_status = MonitoringStatus.ACTIVE
        sub.monitoring_frequency = freq
        sub.next_check_at = freq_calc.next_check_at
        if payload:
            sub.important_only = payload.important_only
            sub.deadline_alerts_enabled = payload.deadline_alerts_enabled
            sub.funding_change_alerts_enabled = payload.funding_change_alerts_enabled
            sub.requirement_change_alerts_enabled = payload.requirement_change_alerts_enabled
            sub.status_change_alerts_enabled = payload.status_change_alerts_enabled
            sub.notification_channels = payload.notification_channels
    else:
        sub = OpportunitySubscription(
            user_id=current_user.id,
            opportunity_id=id,
            monitoring_frequency=freq,
            monitoring_status=MonitoringStatus.ACTIVE,
            next_check_at=freq_calc.next_check_at,
            notification_channels=(payload.notification_channels if payload else ["IN_APP"]),
            important_only=payload.important_only if payload else False,
            deadline_alerts_enabled=(payload.deadline_alerts_enabled if payload else True),
            funding_change_alerts_enabled=(
                payload.funding_change_alerts_enabled if payload else True
            ),
            requirement_change_alerts_enabled=(
                payload.requirement_change_alerts_enabled if payload else True
            ),
            status_change_alerts_enabled=(
                payload.status_change_alerts_enabled if payload else True
            ),
        )
        db.add(sub)

    await db.commit()
    await db.refresh(sub)
    return OpportunitySubscriptionResponse.model_validate(sub)


@router.delete(
    "/opportunities/{id}/monitor",
    status_code=status.HTTP_200_OK,
    summary="Unsubscribe from monitoring an opportunity",
)
async def unmonitor_opportunity(
    id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Cancels continuous monitoring of an opportunity for the current user."""
    sub_query = select(OpportunitySubscription).where(
        OpportunitySubscription.user_id == current_user.id,
        OpportunitySubscription.opportunity_id == id,
    )
    sub_res = await db.execute(sub_query)
    sub = sub_res.scalar_one_or_none()
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitoring subscription not found for this opportunity",
        )

    await db.delete(sub)
    await db.commit()
    return {"status": "unsubscribed", "opportunity_id": str(id)}


@router.get(
    "/opportunities/monitored",
    response_model=list[OpportunitySubscriptionResponse],
    summary="List all monitored opportunities for the current user",
)
async def list_monitored_opportunities(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[OpportunitySubscriptionResponse]:
    """Returns all opportunities currently being actively monitored by the user."""
    query = (
        select(OpportunitySubscription)
        .where(
            OpportunitySubscription.user_id == current_user.id,
            OpportunitySubscription.monitoring_status == MonitoringStatus.ACTIVE,
        )
        .order_by(OpportunitySubscription.created_at.desc())
    )
    result = await db.execute(query)
    subs = result.scalars().all()
    return [OpportunitySubscriptionResponse.model_validate(s) for s in subs]


@router.post(
    "/searches/monitor",
    response_model=SearchSubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Subscribe to continuous monitoring of a search query",
)
async def monitor_search(
    payload: SearchSubscriptionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SearchSubscriptionResponse:
    """Saves a search query to be monitored for newly discovered opportunities."""
    clean_query = payload.query.strip()
    sub = SearchSubscription(
        user_id=current_user.id,
        query=clean_query,
        filters=payload.filters or {},
        monitoring_frequency=payload.monitoring_frequency,
        monitoring_status=MonitoringStatus.ACTIVE,
        known_opportunity_ids=[],
    )
    db.add(sub)
    await db.commit()
    await db.refresh(sub)
    return SearchSubscriptionResponse.model_validate(sub)


@router.delete(
    "/searches/monitor/{id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a monitored search subscription",
)
async def unmonitor_search(
    id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Deletes a monitored search query subscription, enforcing user ownership."""
    sub_query = select(SearchSubscription).where(
        SearchSubscription.id == id,
        SearchSubscription.user_id == current_user.id,
    )
    sub_res = await db.execute(sub_query)
    sub = sub_res.scalar_one_or_none()
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitored search not found",
        )

    await db.delete(sub)
    await db.commit()
    return {"status": "unsubscribed", "search_subscription_id": str(id)}


@router.get(
    "/searches/monitored",
    response_model=list[SearchSubscriptionResponse],
    summary="List all monitored searches for the current user",
)
async def list_monitored_searches(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SearchSubscriptionResponse]:
    """Returns all searches currently being monitored for the user."""
    query = (
        select(SearchSubscription)
        .where(
            SearchSubscription.user_id == current_user.id,
            SearchSubscription.monitoring_status == MonitoringStatus.ACTIVE,
        )
        .order_by(SearchSubscription.created_at.desc())
    )
    result = await db.execute(query)
    subs = result.scalars().all()
    return [SearchSubscriptionResponse.model_validate(s) for s in subs]


@router.post(
    "/monitoring/run-cycle",
    response_model=MonitoringRunSummary,
    summary="Trigger an on-demand monitoring cycle",
)
async def run_monitoring_cycle_endpoint(
    db: AsyncSession = Depends(get_db),
) -> MonitoringRunSummary:
    """Executes a cycle of opportunity checks, deadline sweeps, and search sweeps."""
    return await monitoring_engine.run_monitoring_cycle(db)
