"""Training orchestration service managing lifecycle, jobs, and artifacts."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.evaluation.models.dataset import DatasetExample, SplitType
from app.learning.interfaces.training import ITrainingBackend
from app.learning.models.model_artifact import ModelArtifactRecord
from app.learning.models.model_registry import ModelType
from app.learning.models.training_job import TrainingJob, TrainingJobStatus
from app.learning.schemas.training import TrainingJobCreate
from app.learning.training.mock_backend import MockLocalTrainingBackend

logger = logging.getLogger(__name__)


class TrainingService:
    """Coordinates fine-tuning jobs, execution backends, and artifact storage."""

    def __init__(self, backend: ITrainingBackend | None = None) -> None:
        self.backend = backend or MockLocalTrainingBackend()

    async def create_and_start_job(
        self,
        db: AsyncSession,
        payload: TrainingJobCreate,
        user_id: UUID | None = None,
    ) -> TrainingJob:
        """Schedules and initiates an asynchronous training job."""
        job = TrainingJob(
            job_name=payload.job_name,
            task=payload.task,
            dataset_version_id=payload.dataset_version_id,
            base_model=payload.base_model,
            training_backend=payload.training_backend,
            hyperparameters=payload.hyperparameters.model_dump(),
            resource_limits=payload.resource_limits.model_dump(),
            status=TrainingJobStatus.PREPARING,
            created_by_user_id=user_id,
            started_at=datetime.now(UTC),
            logs=[
                {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "level": "INFO",
                    "message": f"Job {payload.job_name} queued and preparing",
                }
            ],
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)

        # 1. Fetch training & validation examples if dataset version specified
        train_examples: list[dict] = []
        val_examples: list[dict] = []

        if payload.dataset_version_id:
            query = select(DatasetExample).where(
                DatasetExample.dataset_version_id == payload.dataset_version_id
            )
            result = await db.execute(query)
            examples = result.scalars().all()
            for ex in examples:
                ex_dict = {
                    "input_data": ex.input_data,
                    "expected_output": ex.expected_output,
                    "metadata": ex.metadata_json,
                }
                if ex.split == SplitType.TRAIN:
                    train_examples.append(ex_dict)
                elif ex.split == SplitType.VALIDATION:
                    val_examples.append(ex_dict)

        # Fallback to simulated minimal examples if none available
        if not train_examples:
            train_examples = [
                {
                    "input_data": {"query": f"test example {i}"},
                    "expected_output": {"label": "match"},
                }
                for i in range(10)
            ]
        if not val_examples:
            val_examples = [
                {
                    "input_data": {"query": f"val example {i}"},
                    "expected_output": {"label": "match"},
                }
                for i in range(4)
            ]

        # 2. Run training backend
        job.status = TrainingJobStatus.RUNNING
        await db.commit()

        config = {
            **payload.hyperparameters.model_dump(),
            **payload.resource_limits.model_dump(),
        }

        exec_res = await self.backend.run_job(
            job=job,
            config=config,
            train_examples=train_examples,
            val_examples=val_examples,
        )

        job.finished_at = datetime.now(UTC)
        job.logs.extend(exec_res.logs)
        job.metrics = exec_res.metrics

        if exec_res.success and exec_res.artifact_path:
            job.status = TrainingJobStatus.COMPLETED
            artifact = ModelArtifactRecord(
                training_job_id=job.id,
                artifact_path=exec_res.artifact_path,
                checksum=exec_res.checksum or "",
                file_size_bytes=exec_res.file_size_bytes,
                framework="safetensors",
                artifact_metadata={"backend": payload.training_backend},
            )
            db.add(artifact)
        elif exec_res.error_message and "cancel" in exec_res.error_message.lower():
            job.status = TrainingJobStatus.CANCELLED
            job.error_message = exec_res.error_message
        else:
            job.status = TrainingJobStatus.FAILED
            job.error_message = exec_res.error_message or "Training execution failed"

        await db.commit()
        await db.refresh(job)
        return job

    async def get_job(self, db: AsyncSession, job_id: UUID) -> TrainingJob | None:
        """Retrieves single training job by ID."""
        query = select(TrainingJob).where(TrainingJob.id == job_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def list_jobs(
        self,
        db: AsyncSession,
        task: ModelType | None = None,
        status: TrainingJobStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[TrainingJob]:
        """Lists training jobs with optional task and status filtering."""
        query = select(TrainingJob)
        if task:
            query = query.where(TrainingJob.task == task)
        if status:
            query = query.where(TrainingJob.status == status)
        query = query.order_by(TrainingJob.created_at.desc()).offset(offset).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def cancel_job(self, db: AsyncSession, job_id: UUID) -> TrainingJob | None:
        """Requests cancellation of an ongoing training job."""
        job = await self.get_job(db, job_id)
        if not job:
            return None

        if job.status in (
            TrainingJobStatus.QUEUED,
            TrainingJobStatus.PREPARING,
            TrainingJobStatus.RUNNING,
        ):
            await self.backend.cancel_job(str(job.id))
            job.status = TrainingJobStatus.CANCELLED
            job.error_message = "Cancelled by user"
            job.finished_at = datetime.now(UTC)
            await db.commit()
            await db.refresh(job)

        return job
