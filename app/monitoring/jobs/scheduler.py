"""Job scheduler coordinating periodic runs and checks."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.monitoring.interfaces.monitor import IMonitoringScheduler
from app.monitoring.jobs.queue import TaskQueue
from app.monitoring.models.job import JobType


class MonitoringScheduler(IMonitoringScheduler):
    """Schedules monitoring jobs into the TaskQueue."""

    def __init__(self, task_queue: TaskQueue, db: AsyncSession) -> None:
        self.task_queue = task_queue
        self.db = db

    async def schedule_opportunity_check(
        self,
        subscription_id: UUID,
        run_at: datetime | None = None,
    ) -> UUID:
        """Enqueue an opportunity check."""
        job = await self.task_queue.enqueue(
            db=self.db,
            job_type=JobType.OPPORTUNITY_CHECK,
            target_id=subscription_id,
            scheduled_at=run_at or datetime.now(UTC),
        )
        return job.id

    async def schedule_search_sweep(
        self,
        search_id: UUID,
        run_at: datetime | None = None,
    ) -> UUID:
        """Enqueue a search sweep."""
        job = await self.task_queue.enqueue(
            db=self.db,
            job_type=JobType.SEARCH_SWEEP,
            target_id=search_id,
            scheduled_at=run_at or datetime.now(UTC),
        )
        return job.id

    async def schedule_deadline_sweep(
        self,
        run_at: datetime | None = None,
    ) -> UUID:
        """Enqueue a deadline sweep."""
        job = await self.task_queue.enqueue(
            db=self.db,
            job_type=JobType.DEADLINE_SWEEP,
            scheduled_at=run_at or datetime.now(UTC),
        )
        return job.id
