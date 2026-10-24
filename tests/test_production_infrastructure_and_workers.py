import pytest

from app.core.locks.distributed_lock import DistributedLock
from app.workers.handler import task_handlers
from app.workers.models import JobCategory, JobMessage
from app.workers.queue import BackgroundJobQueue


@pytest.mark.asyncio
async def test_distributed_lock_lifecycle() -> None:
    lock_name = "test_resource_lock"

    lock1 = DistributedLock(lock_name, ttl_seconds=5, acquire_timeout=0.2)
    acquired = await lock1.acquire()
    assert acquired is True

    # Second lock on same resource should fail
    lock2 = DistributedLock(lock_name, ttl_seconds=5, acquire_timeout=0.2)
    acquired_second = await lock2.acquire()
    assert acquired_second is False

    # Release first lock
    released = await lock1.release()
    assert released is True

    # Now second lock can acquire
    acquired_now = await lock2.acquire()
    assert acquired_now is True
    await lock2.release()


@pytest.mark.asyncio
async def test_distributed_lock_context_manager() -> None:
    lock = DistributedLock("test_ctx_lock", ttl_seconds=5, acquire_timeout=0.2)

    executed = False
    async with lock:
        executed = True
        # While locked, another acquisition fails
        nested = DistributedLock("test_ctx_lock", ttl_seconds=5, acquire_timeout=0.2)
        assert await nested.acquire() is False

    assert executed is True
    # After exiting context manager, lock is released
    free_check = DistributedLock("test_ctx_lock", ttl_seconds=5, acquire_timeout=0.2)
    assert await free_check.acquire() is True
    await free_check.release()


@pytest.mark.asyncio
async def test_job_queue_idempotency_and_enqueue() -> None:
    queue = BackgroundJobQueue()

    # First enqueue succeeds
    job1 = await queue.enqueue(
        task_name="crawl_page",
        category=JobCategory.CRAWL,
        payload={"url": "https://example.com/scholarship"},
        idempotency_key="crawl:example.com/scholarship-unique-1",
    )
    assert job1 is not None

    # Second enqueue with identical idempotency key is skipped
    job2 = await queue.enqueue(
        task_name="crawl_page",
        category=JobCategory.CRAWL,
        payload={"url": "https://example.com/scholarship"},
        idempotency_key="crawl:example.com/scholarship-unique-1",
    )
    assert job2 is None

    # Dequeue retrieves the job
    dequeued = await queue.dequeue(category=JobCategory.CRAWL)
    assert dequeued is not None
    assert dequeued.idempotency_key == "crawl:example.com/scholarship-unique-1"


@pytest.mark.asyncio
async def test_job_retry_and_dead_letter_queue() -> None:
    queue = BackgroundJobQueue()

    job = JobMessage(
        task_name="failing_task",
        category=JobCategory.SEARCH,
        payload={"query": "test query"},
        max_retries=1,
    )

    # First failure -> retried
    retried = await queue.handle_failure(job, error_message="Temporary network timeout")
    assert retried is True
    assert job.retry_count == 1

    # Second failure (exceeds max retries of 1) -> sent to DLQ
    retried_again = await queue.handle_failure(job, error_message="Fatal API exhaustion")
    assert retried_again is False
    assert job.retry_count == 2


@pytest.mark.asyncio
async def test_task_handler_execution() -> None:
    task_ran = False

    async def custom_task_handler(job: JobMessage) -> dict:
        nonlocal task_ran
        task_ran = True
        return {"status": "success", "echo": job.payload.get("val")}

    task_handlers.register("custom_test_task", custom_task_handler)

    job = JobMessage(
        task_name="custom_test_task",
        category=JobCategory.ANALYTICS,
        payload={"val": 42},
    )

    result = await task_handlers.execute(job)
    assert task_ran is True
    assert result == {"status": "success", "echo": 42}
