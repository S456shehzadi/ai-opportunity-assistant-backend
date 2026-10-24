"""Beta testing endpoints for feature flags, in-app triage feedback,
dashboard, and cost telemetry.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.schemas.beta_dashboard import BetaDashboardMetrics
from app.analytics.services.beta_dashboard_service import (
    BetaDashboardService,
    get_beta_dashboard_service,
)
from app.api.dependencies import (
    get_current_reviewer_user,
    get_current_user,
    get_optional_db,
)
from app.core.cost_tracker import CostSummary, get_cost_tracker
from app.core.feature_flags import (
    FeatureFlagsService,
    FeatureFlagState,
    get_feature_flags,
)
from app.feedback.schemas.triage import (
    BetaFeedbackSubmission,
    BetaTriageCategory,
    TriagedFeedbackItem,
    TriagePriority,
)
from app.feedback.services.triage_service import (
    BetaFeedbackTriageService,
    get_triage_service,
)
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/beta", tags=["Beta Launch & Feedback Operations"])


# ------------------------------------------------------------------------------
# Feature Flags & Remote Configuration
# ------------------------------------------------------------------------------


@router.get(
    "/features",
    summary="Get active feature flags for mobile client configuration",
)
async def get_client_feature_flags(
    feature_flags: FeatureFlagsService = Depends(get_feature_flags),
) -> dict[str, bool]:
    """Returns boolean dictionary of features active in current environment."""
    return feature_flags.get_client_flags()


@router.get(
    "/features/states",
    response_model=list[FeatureFlagState],
    summary="Inspect all feature flag details (Admin/Reviewer)",
)
async def get_all_feature_flag_states(
    current_reviewer: User = Depends(get_current_reviewer_user),
    feature_flags: FeatureFlagsService = Depends(get_feature_flags),
) -> list[FeatureFlagState]:
    """Returns detailed states and rollout percentages for internal management."""
    return feature_flags.get_all_states()


@router.put(
    "/features/{feature_key}",
    response_model=FeatureFlagState,
    summary="Toggle or update a feature flag (Admin/Reviewer)",
)
async def update_feature_flag(
    feature_key: str,
    enabled: bool = Query(...),
    rollout_percentage: int | None = Query(default=None, ge=0, le=100),
    current_reviewer: User = Depends(get_current_reviewer_user),
    feature_flags: FeatureFlagsService = Depends(get_feature_flags),
) -> FeatureFlagState:
    """Updates runtime feature flag state without rebuilding or redeploying."""
    try:
        return feature_flags.set_flag(
            flag_key=feature_key,
            enabled=enabled,
            rollout_percentage=rollout_percentage,
        )
    except KeyError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature flag '{feature_key}' not found",
        ) from err


# ------------------------------------------------------------------------------
# In-App Beta Feedback & Prioritized Defect Triage
# ------------------------------------------------------------------------------


@router.post(
    "/feedback",
    response_model=TriagedFeedbackItem,
    status_code=status.HTTP_201_CREATED,
    summary="Submit categorized beta issue or feedback",
)
async def submit_beta_feedback(
    payload: BetaFeedbackSubmission,
    current_user: User = Depends(get_current_user),
    db: AsyncSession | None = Depends(get_optional_db),
    triage_service: BetaFeedbackTriageService = Depends(get_triage_service),
) -> TriagedFeedbackItem:
    """Classifies user report, computes priority score, and routes to review queue."""
    return await triage_service.triage_submission(
        user_id=current_user.id,
        payload=payload,
        db=db,
    )


@router.get(
    "/feedback",
    response_model=list[TriagedFeedbackItem],
    summary="List prioritized beta feedback items (Admin/Reviewer)",
)
async def list_triaged_feedback(
    category: BetaTriageCategory | None = Query(default=None),
    priority: TriagePriority | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    current_reviewer: User = Depends(get_current_reviewer_user),
    triage_service: BetaFeedbackTriageService = Depends(get_triage_service),
) -> list[TriagedFeedbackItem]:
    """Retrieves triaged items sorted by priority score."""
    return triage_service.get_triaged_items(
        category=category,
        priority=priority,
        limit=limit,
    )


# ------------------------------------------------------------------------------
# Beta Telemetry & Observability Dashboard
# ------------------------------------------------------------------------------


@router.get(
    "/dashboard",
    response_model=BetaDashboardMetrics,
    summary="Get privacy-preserving beta health & quality metrics (Admin/Reviewer)",
)
async def get_beta_dashboard(
    current_reviewer: User = Depends(get_current_reviewer_user),
    db: AsyncSession | None = Depends(get_optional_db),
    dashboard_service: BetaDashboardService = Depends(get_beta_dashboard_service),
) -> BetaDashboardMetrics:
    """Returns aggregated performance, search quality, and user satisfaction metrics."""
    return await dashboard_service.get_dashboard_metrics(db=db)


@router.get(
    "/costs",
    response_model=CostSummary,
    summary="Inspect external AI and search API spend vs daily budget (Admin/Reviewer)",
)
async def get_cost_telemetry(
    current_reviewer: User = Depends(get_current_reviewer_user),
) -> CostSummary:
    """Returns daily cost breakdown preventing runaway beta expenses."""
    return get_cost_tracker().get_summary()
