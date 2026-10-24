"""REST API endpoints for specialized model catalog, promotion gates, rollback, and health."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_admin_user, get_current_reviewer_user, get_db
from app.learning.models.model_registry import (
    ModelStatus,
    ModelType,
)
from app.learning.schemas.learning import ModelDefinitionCreate
from app.learning.schemas.training import (
    CanaryTrafficUpdate,
    ModelCardCreate,
    ModelCardResponse,
    ModelDetailResponse,
    ModelHealthResponse,
    ModelPromotionRequest,
    ModelRollbackRequest,
)
from app.learning.services.model_registry_service import ModelRegistryService
from app.learning.services.model_serving_service import ModelServingService
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["Specialized Model Registry & Governance"])
registry_service = ModelRegistryService()
serving_service = ModelServingService()


@router.get(
    "/models",
    response_model=list[ModelDetailResponse],
    summary="List registered models in catalog",
)
async def list_models(
    task: ModelType | None = Query(default=None),
    status_filter: ModelStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_reviewer: User = Depends(get_current_reviewer_user),
    db: AsyncSession = Depends(get_db),
) -> list[ModelDetailResponse]:
    """Retrieves models across tasks and lifecycle stages."""
    models = await registry_service.list_models(
        db=db,
        task=task,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    return [ModelDetailResponse.model_validate(m) for m in models]


@router.get(
    "/models/{model_id}",
    response_model=ModelDetailResponse,
    summary="Get full details and model card for a model",
)
async def get_model(
    model_id: str,
    current_reviewer: User = Depends(get_current_reviewer_user),
    db: AsyncSession = Depends(get_db),
) -> ModelDetailResponse:
    """Inspects model governance metadata, performance metrics, and configuration."""
    model = await registry_service.get_model(db=db, model_id=model_id)
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model {model_id} not found",
        )
    return ModelDetailResponse.model_validate(model)


@router.post(
    "/models",
    response_model=ModelDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new model in catalog (Admin only)",
)
async def register_model(
    payload: ModelDefinitionCreate,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> ModelDetailResponse:
    """Registers an available local, fine-tuned, or remote model."""
    try:
        model = await registry_service.register_model(db=db, payload=payload)
        return ModelDetailResponse.model_validate(model)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model registration failed: {str(exc)}",
        ) from exc


@router.post(
    "/models/{model_id}/promote",
    response_model=ModelDetailResponse,
    summary="Promote model through lifecycle gate (Admin only)",
)
async def promote_model(
    model_id: str,
    request: ModelPromotionRequest,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> ModelDetailResponse:
    """Transitions model through lifecycle gate after verifying quality thresholds."""
    try:
        promoted = await registry_service.promote_model(
            db=db,
            model_id=model_id,
            request=request,
        )
        return ModelDetailResponse.model_validate(promoted)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/models/{model_id}/rollback",
    response_model=ModelDetailResponse,
    summary="Rollback model to previous stable version (Admin only)",
)
async def rollback_model(
    model_id: str,
    request: ModelRollbackRequest,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> ModelDetailResponse:
    """Atomically rollbacks production model to previous stable release."""
    try:
        restored = await registry_service.rollback_model(
            db=db,
            model_id=model_id,
            request=request,
        )
        return ModelDetailResponse.model_validate(restored)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/models/{model_id}/canary",
    response_model=ModelDetailResponse,
    summary="Update canary traffic percentage (Admin only)",
)
async def update_canary(
    model_id: str,
    payload: CanaryTrafficUpdate,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> ModelDetailResponse:
    """Updates the portion of live evaluation traffic routed to this model."""
    try:
        model = await registry_service.update_canary(
            db=db,
            model_id=model_id,
            canary_percentage=payload.canary_percentage,
        )
        return ModelDetailResponse.model_validate(model)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.put(
    "/models/{model_id}/card",
    response_model=ModelCardResponse,
    summary="Upsert auditable model card (Admin only)",
)
async def upsert_model_card(
    model_id: str,
    payload: ModelCardCreate,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> ModelCardResponse:
    """Documents intended use, benchmark metrics, provenance, and limitations."""
    try:
        card = await registry_service.upsert_model_card(
            db=db,
            model_id=model_id,
            payload=payload,
        )
        return ModelCardResponse.model_validate(card)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/models/{model_id}/health",
    response_model=ModelHealthResponse,
    summary="Probe operational health of model endpoint",
)
async def check_model_health(
    model_id: str,
    db: AsyncSession = Depends(get_db),
) -> ModelHealthResponse:
    """Verifies that model endpoint is online and responsive."""
    return await serving_service.check_health(db=db, model_id=model_id)
