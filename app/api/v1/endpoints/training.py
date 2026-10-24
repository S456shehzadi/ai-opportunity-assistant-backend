"""REST API endpoints for fine-tuning jobs, training execution, and monitoring."""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_admin_user, get_current_reviewer_user, get_db
from app.learning.models.model_registry import ModelType
from app.learning.models.training_job import TrainingJobStatus
from app.learning.schemas.training import (
    TrainingJobCreate,
    TrainingJobResponse,
)
from app.learning.services.training_service import TrainingService
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["Model Training & Fine-Tuning"])
training_service = TrainingService()


@router.post(
    "/training/jobs",
    response_model=TrainingJobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit and initiate an asynchronous model training job (Admin only)",
)
async def create_training_job(
    payload: TrainingJobCreate,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> TrainingJobResponse:
    """Queues and executes a fine-tuning job with governance enforcement."""
    try:
        job = await training_service.create_and_start_job(
            db=db,
            payload=payload,
            user_id=current_admin.id,
        )
        return TrainingJobResponse.model_validate(job)
    except Exception as exc:
        logger.error("Failed to submit training job: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Training job submission failed: {str(exc)}",
        ) from exc


@router.get(
    "/training/jobs",
    response_model=list[TrainingJobResponse],
    summary="List fine-tuning and training jobs",
)
async def list_training_jobs(
    task: ModelType | None = Query(default=None),
    status_filter: TrainingJobStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_reviewer: User = Depends(get_current_reviewer_user),
    db: AsyncSession = Depends(get_db),
) -> list[TrainingJobResponse]:
    """Retrieves history of training jobs with metrics and execution logs."""
    jobs = await training_service.list_jobs(
        db=db,
        task=task,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    return [TrainingJobResponse.model_validate(j) for j in jobs]


@router.get(
    "/training/jobs/{job_id}",
    response_model=TrainingJobResponse,
    summary="Get details, metrics, and logs for a training job",
)
async def get_training_job(
    job_id: UUID,
    current_reviewer: User = Depends(get_current_reviewer_user),
    db: AsyncSession = Depends(get_db),
) -> TrainingJobResponse:
    """Retrieves full job status, training curves, logs, and emitted artifacts."""
    job = await training_service.get_job(db=db, job_id=job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Training job {job_id} not found",
        )
    return TrainingJobResponse.model_validate(job)


@router.post(
    "/training/jobs/{job_id}/cancel",
    response_model=TrainingJobResponse,
    summary="Cancel an active training job (Admin only)",
)
async def cancel_training_job(
    job_id: UUID,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> TrainingJobResponse:
    """Interrupts execution loop of in-flight training job."""
    job = await training_service.cancel_job(db=db, job_id=job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Training job {job_id} not found",
        )
    return TrainingJobResponse.model_validate(job)
