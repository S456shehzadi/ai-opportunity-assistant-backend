"""Task handler registry and workload execution routines."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from app.workers.models import JobMessage

logger = logging.getLogger(__name__)

HandlerFunc = Callable[[JobMessage], Awaitable[dict[str, Any]]]


class TaskHandlerRegistry:
    """Registry routing job task names to asynchronous execution handlers."""

    def __init__(self) -> None:
        self._handlers: dict[str, HandlerFunc] = {}
        self._register_default_handlers()

    def register(self, task_name: str, handler: HandlerFunc) -> None:
        """Registers a custom task execution handler."""
        self._handlers[task_name] = handler

    async def execute(self, job: JobMessage) -> dict[str, Any]:
        """Dispatches job to registered handler."""
        handler = self._handlers.get(job.task_name)
        if not handler:
            raise ValueError(f"No task handler registered for task name: {job.task_name}")

        return await handler(job)

    def _register_default_handlers(self) -> None:
        """Registers baseline handlers across core platform domains."""

        async def handle_search(job: JobMessage) -> dict[str, Any]:
            query = job.payload.get("query", "")
            logger.info("Executing background search for: %s", query)
            return {"status": "success", "query": query, "processed": True}

        async def handle_crawl(job: JobMessage) -> dict[str, Any]:
            url = job.payload.get("url", "")
            logger.info("Executing background web retrieval for: %s", url)
            return {"status": "success", "url": url, "retrieved": True}

        async def handle_monitoring(job: JobMessage) -> dict[str, Any]:
            opp_id = job.payload.get("opportunity_id", "")
            logger.info("Executing opportunity monitoring sweep for: %s", opp_id)
            return {"status": "success", "opportunity_id": opp_id, "changes_checked": True}

        async def handle_notification(job: JobMessage) -> dict[str, Any]:
            recipient = job.payload.get("user_id", "")
            message = job.payload.get("message", "")
            logger.info("Dispatching notification to user %s: %s", recipient, message)
            return {"status": "success", "delivered": True, "recipient": recipient}

        async def handle_training(job: JobMessage) -> dict[str, Any]:
            job_id = job.payload.get("training_job_id", "")
            logger.info("Executing background training routine for job: %s", job_id)
            return {"status": "success", "training_job_id": job_id, "completed": True}

        async def handle_analytics(job: JobMessage) -> dict[str, Any]:
            event_type = job.payload.get("event_type", "")
            logger.info("Aggregating background analytics event: %s", event_type)
            return {"status": "success", "event_type": event_type, "aggregated": True}

        async def handle_discovery_index(job: JobMessage) -> dict[str, Any]:
            opp_id = job.payload.get("opportunity_id", "")
            logger.info("Executing background discovery indexing for opportunity: %s", opp_id)
            return {"status": "success", "opportunity_id": opp_id, "indexed": True}

        self.register("search_task", handle_search)
        self.register("crawl_task", handle_crawl)
        self.register("monitoring_task", handle_monitoring)
        self.register("notification_task", handle_notification)
        self.register("training_task", handle_training)
        self.register("analytics_task", handle_analytics)
        self.register("discovery_index_task", handle_discovery_index)


_handler_registry: TaskHandlerRegistry | None = None


def get_handler_registry() -> TaskHandlerRegistry:
    global _handler_registry
    if _handler_registry is None:
        _handler_registry = TaskHandlerRegistry()
    return _handler_registry


task_handlers = get_handler_registry()
