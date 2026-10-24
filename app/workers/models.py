"""Data models for background jobs, queues, and execution lifecycles."""

from __future__ import annotations

import time
import uuid
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class JobStatus(StrEnum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    DEAD_LETTER = "DEAD_LETTER"


class JobCategory(StrEnum):
    DEFAULT = "default"
    SEARCH = "search"
    RETRIEVAL = "retrieval"
    MONITORING = "monitoring"
    NOTIFICATION = "notification"
    AI = "ai"
    TRAINING = "training"
    EVALUATION = "evaluation"
    CRAWL = "crawl"
    ANALYTICS = "analytics"


class JobMessage(BaseModel):
    """Reliable, idempotent background job message payload."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    category: JobCategory = JobCategory.DEFAULT
    task_name: str
    payload: dict[str, Any] = Field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: float = 60.0
    idempotency_key: str | None = None
    created_at: float = Field(default_factory=time.time)
    error_message: str | None = None
