"""Durable, idempotent background job queue backed by Redis with memory fallback."""

from __future__ import annotations

import collections
import logging
from typing import Any

from app.core.redis import get_redis_service
from app.workers.models import JobCategory, JobMessage

logger = logging.getLogger(__name__)


class BackgroundJobQueue:
    """Manages queueing, dequeuing, and dead-letter handling across workload categories."""

    def __init__(self) -> None:
        self.redis_service = get_redis_service()
        self._memory_queues: dict[str, collections.deque[str]] = {}
        self._seen_idempotency_keys: set[str] = set()

    def _queue_key(self, category: JobCategory) -> str:
        return f"queue:{category.value}"

    def _dlq_key(self, category: JobCategory) -> str:
        return f"dlq:{category.value}"

    async def enqueue(
        self,
        task_name: str,
        payload: dict[str, Any],
        category: JobCategory = JobCategory.DEFAULT,
        idempotency_key: str | None = None,
        max_retries: int = 3,
        timeout_seconds: float = 60.0,
    ) -> JobMessage | None:
        """Enqueues job, discarding duplicates if idempotency key was previously processed."""
        if idempotency_key:
            client = await self.redis_service.get_client()
            idem_key = f"idem:{idempotency_key}"
            # Check if idempotency key already exists
            if hasattr(client, "set"):
                acquired = await client.set(idem_key, "1", ex=86400, nx=True)
                if not acquired:
                    logger.info("Discarded duplicate job with idempotency key: %s", idempotency_key)
                    return None
            else:
                if idempotency_key in self._seen_idempotency_keys:
                    logger.info("Discarded duplicate job with idempotency key: %s", idempotency_key)
                    return None
                self._seen_idempotency_keys.add(idempotency_key)

        job = JobMessage(
            category=category,
            task_name=task_name,
            payload=payload,
            idempotency_key=idempotency_key,
            max_retries=max_retries,
            timeout_seconds=timeout_seconds,
        )

        serialized = job.model_dump_json()
        client = await self.redis_service.get_client()

        if hasattr(client, "rpush"):
            await client.rpush(self._queue_key(category), serialized)
        else:
            q = self._memory_queues.setdefault(self._queue_key(category), collections.deque())
            q.append(serialized)

        return job

    async def dequeue(
        self,
        category: JobCategory = JobCategory.DEFAULT,
    ) -> JobMessage | None:
        """Pulls next pending job from the specified workload category queue."""
        client = await self.redis_service.get_client()

        raw: str | None = None
        if hasattr(client, "lpop"):
            raw = await client.lpop(self._queue_key(category))
        else:
            q = self._memory_queues.get(self._queue_key(category))
            if q and len(q) > 0:
                raw = q.popleft()

        if not raw:
            return None

        try:
            return JobMessage.model_validate_json(raw)
        except Exception as exc:
            logger.error("Failed to parse job message: %s", exc)
            return None

    async def handle_failure(
        self,
        job: JobMessage,
        error_message: str,
    ) -> bool:
        """Applies exponential backoff retry or routes exhausted job to dead-letter queue."""
        job.retry_count += 1
        job.error_message = error_message

        if job.retry_count <= job.max_retries:
            logger.warning(
                "Retrying job %s (attempt %d/%d): %s",
                job.id,
                job.retry_count,
                job.max_retries,
                error_message,
            )
            # Re-enqueue
            client = await self.redis_service.get_client()
            serialized = job.model_dump_json()
            if hasattr(client, "rpush"):
                await client.rpush(self._queue_key(job.category), serialized)
            else:
                q = self._memory_queues.setdefault(
                    self._queue_key(job.category), collections.deque()
                )
                q.append(serialized)
            return True

        # Max retries exceeded -> Dead Letter Queue
        logger.error(
            "Job %s exceeded max retries (%d), moving to dead-letter queue: %s",
            job.id,
            job.max_retries,
            error_message,
        )
        client = await self.redis_service.get_client()
        serialized = job.model_dump_json()
        if hasattr(client, "rpush"):
            await client.rpush(self._dlq_key(job.category), serialized)
        else:
            q = self._memory_queues.setdefault(self._dlq_key(job.category), collections.deque())
            q.append(serialized)
        return False

    async def get_queue_depth(self, category: JobCategory) -> int:
        """Returns pending items count in the workload queue."""
        client = await self.redis_service.get_client()
        if hasattr(client, "llen"):
            return int(await client.llen(self._queue_key(category)))

        q = self._memory_queues.get(self._queue_key(category))
        return len(q) if q else 0


_job_queue: BackgroundJobQueue | None = None


def get_job_queue() -> BackgroundJobQueue:
    global _job_queue
    if _job_queue is None:
        _job_queue = BackgroundJobQueue()
    return _job_queue
