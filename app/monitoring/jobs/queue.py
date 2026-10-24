"""Provider-independent task queue and job worker implementation."""

from __future__ import annotations

import logging
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.monitoring.models.job import (
    JobStatus,
    JobType,
    MonitoringExecution,
    MonitoringJob,
)

logger = logging.getLogger(__name__)

JobHandler = Callable[[MonitoringJob, AsyncSession], Coroutine[Any, Any, dict[str, Any]]]


class TaskQueue:
    """Async task queue interface supporting database-backed durable jobs."""

    def __init__(self) -> None:
        self._handlers: dict[JobType, JobHandler] = {}

    def register_handler(self, job_type: JobType, handler: JobHandler) -> None:
        """Register an execution handler for a specific JobType."""
        self._handlers[job_type] = handler

    async def enqueue(
        self,
        db: AsyncSession,
        job_type: JobType,
        target_id: UUID | None = None,
        payload: dict[str, Any] | None = None,
        scheduled_at: datetime | None = None,
        max_retries: int = 3,
    ) -> MonitoringJob:
        """Create and persist a new job in PENDING state."""
        job = MonitoringJob(
            job_type=job_type,
            target_id=target_id,
            payload=payload or {},
            scheduled_at=scheduled_at or datetime.now(UTC),
            max_retries=max_retries,
            status=JobStatus.PENDING,
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        return job

    async def execute_job(
        self,
        db: AsyncSession,
        job: MonitoringJob,
    ) -> MonitoringExecution:
        """Execute a single job with audit logging, error capture, and retries."""
        handler = self._handlers.get(job.job_type)
        if not handler:
            err = f"No handler registered for job type {job.job_type}"
            job.status = JobStatus.FAILED
            job.error_message = err
            execution = MonitoringExecution(
                job_id=job.id,
                started_at=datetime.now(UTC),
                completed_at=datetime.now(UTC),
                status=JobStatus.FAILED,
                error_message=err,
            )
            db.add(execution)
            await db.commit()
            return execution

        job.status = JobStatus.RUNNING
        execution = MonitoringExecution(
            job_id=job.id,
            started_at=datetime.now(UTC),
            status=JobStatus.RUNNING,
        )
        db.add(execution)
        await db.commit()

        try:
            result = await handler(job, db)
            execution.completed_at = datetime.now(UTC)
            execution.status = JobStatus.COMPLETED
            execution.result_summary = result
            job.status = JobStatus.COMPLETED
            job.error_message = None
        except Exception as exc:
            logger.exception("Error executing monitoring job %s", job.id)
            execution.completed_at = datetime.now(UTC)
            execution.status = JobStatus.FAILED
            execution.error_message = str(exc)

            job.retry_count += 1
            if job.retry_count <= job.max_retries:
                job.status = JobStatus.RETRYING
                job.error_message = f"Attempt {job.retry_count} failed: {exc}"
            else:
                job.status = JobStatus.FAILED
                job.error_message = f"Exceeded max retries ({job.max_retries}): {exc}"

        await db.commit()
        await db.refresh(execution)
        return execution

    async def process_due_jobs(
        self, db: AsyncSession, limit: int = 10
    ) -> list[MonitoringExecution]:
        """Fetch and execute due pending or retrying jobs."""
        now = datetime.now(UTC)
        query = (
            select(MonitoringJob)
            .where(
                MonitoringJob.status.in_([JobStatus.PENDING, JobStatus.RETRYING]),
                MonitoringJob.scheduled_at <= now,
            )
            .order_by(MonitoringJob.scheduled_at.asc())
            .limit(limit)
        )
        result = await db.execute(query)
        jobs = result.scalars().all()

        executions: list[MonitoringExecution] = []
        for job in jobs:
            execution = await self.execute_job(db, job)
            executions.append(execution)

        return executions
