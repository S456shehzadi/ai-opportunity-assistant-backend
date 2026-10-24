"""Background worker runner loop with exponential backoff and graceful termination."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.workers.handler import get_handler_registry
from app.workers.models import JobCategory, JobMessage
from app.workers.queue import get_job_queue

logger = logging.getLogger(__name__)


class WorkerRunner:
    """Executes background jobs pulled from queues with timeout and retry management."""

    def __init__(
        self,
        categories: list[JobCategory] | None = None,
        poll_interval: float = 0.5,
    ) -> None:
        self.categories = categories or [JobCategory.DEFAULT]
        self.poll_interval = poll_interval
        self.queue = get_job_queue()
        self.handlers = get_handler_registry()
        self._running = False

    async def process_next_job(self) -> JobMessage | None:
        """Pulls and executes a single pending job from watched categories."""
        for cat in self.categories:
            job = await self.queue.dequeue(cat)
            if job:
                await self._execute_job(job)
                return job
        return None

    async def _execute_job(self, job: JobMessage) -> dict[str, Any] | None:
        """Executes a job under timeout protection and handles failure states."""
        try:
            logger.info("Worker started executing job %s (%s)", job.id, job.task_name)
            result = await asyncio.wait_for(
                self.handlers.execute(job),
                timeout=job.timeout_seconds,
            )
            logger.info("Worker completed job %s successfully", job.id)
            return result
        except TimeoutError:
            err = f"Job {job.id} timed out after {job.timeout_seconds}s"
            logger.error(err)
            await self.queue.handle_failure(job, err)
            return None
        except Exception as exc:
            err = f"Job {job.id} failed with error: {str(exc)}"
            logger.error(err)
            await self.queue.handle_failure(job, err)
            return None

    async def run(self, max_iterations: int | None = None) -> None:
        """Runs the worker polling loop until stopped or iteration limit reached."""
        self._running = True
        iterations = 0

        logger.info(
            "Worker runner started on categories: %s",
            [c.value for c in self.categories],
        )

        while self._running:
            job = await self.process_next_job()
            if not job:
                await asyncio.sleep(self.poll_interval)

            iterations += 1
            if max_iterations is not None and iterations >= max_iterations:
                break

    def stop(self) -> None:
        """Signals worker loop to stop gracefully."""
        self._running = False
        logger.info("Worker runner stop signal received")
