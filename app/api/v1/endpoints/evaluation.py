"""REST API endpoints for benchmark datasets and reproducible evaluation runs."""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_admin_user, get_current_reviewer_user, get_db
from app.evaluation.schemas.evaluation import (
    DatasetCreate,
    DatasetResponse,
    DatasetVersionCreate,
    DatasetVersionResponse,
    EvaluationRunCreate,
    EvaluationRunResponse,
)
from app.evaluation.services.evaluation_service import EvaluationService
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["Model Evaluation & Benchmarking"])
evaluation_service = EvaluationService()


@router.post(
    "/evaluation/datasets",
    response_model=DatasetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new benchmark dataset definition (Admin only)",
)
async def create_dataset(
    payload: DatasetCreate,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> DatasetResponse:
    """Creates a new logical benchmark dataset. Requires admin role."""
    dataset = await evaluation_service.create_dataset(db=db, payload=payload)
    return DatasetResponse.model_validate(dataset)


@router.get(
    "/evaluation/datasets",
    response_model=list[DatasetResponse],
    summary="List benchmark datasets with versions (Reviewer/Admin)",
)
async def list_datasets(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_reviewer: User = Depends(get_current_reviewer_user),
    db: AsyncSession = Depends(get_db),
) -> list[DatasetResponse]:
    """Lists registered evaluation datasets. Requires reviewer or admin role."""
    datasets = await evaluation_service.list_datasets(db=db, limit=limit, offset=offset)
    return [DatasetResponse.model_validate(d) for d in datasets]


@router.post(
    "/evaluation/datasets/{id}/versions",
    response_model=DatasetVersionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Release a new version of a benchmark dataset (Admin only)",
)
async def create_dataset_version(
    id: UUID,
    payload: DatasetVersionCreate,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> DatasetVersionResponse:
    """Publishes a new immutable dataset version with examples. Requires admin role."""
    try:
        version = await evaluation_service.create_dataset_version(
            db=db,
            dataset_id=id,
            payload=payload,
        )
        return DatasetVersionResponse.model_validate(version)
    except Exception as e:
        logger.exception("Failed to create dataset version for %s", id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.post(
    "/evaluation/runs",
    response_model=EvaluationRunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Execute a benchmark evaluation run against a dataset version (Admin only)",
)
async def execute_evaluation_run(
    payload: EvaluationRunCreate,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> EvaluationRunResponse:
    """Runs automated evaluation and computes auditable metrics. Requires admin role."""
    try:
        run = await evaluation_service.execute_evaluation_run(db=db, payload=payload)
        return EvaluationRunResponse.model_validate(run)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.exception("Failed to execute evaluation run")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e


@router.get(
    "/evaluation/runs",
    response_model=list[EvaluationRunResponse],
    summary="List benchmark evaluation runs (Reviewer/Admin)",
)
async def list_evaluation_runs(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_reviewer: User = Depends(get_current_reviewer_user),
    db: AsyncSession = Depends(get_db),
) -> list[EvaluationRunResponse]:
    """Lists completed and running evaluation runs. Requires reviewer or admin role."""
    runs = await evaluation_service.list_evaluation_runs(db=db, limit=limit, offset=offset)
    return [EvaluationRunResponse.model_validate(r) for r in runs]
