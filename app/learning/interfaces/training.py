"""Training backend and artifact storage interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.learning.models.training_job import TrainingJob


@dataclass
class TrainingExecutionResult:
    """Outcome payload generated upon training run completion or failure."""

    success: bool
    metrics: dict[str, Any] = field(default_factory=dict)
    logs: list[dict[str, Any]] = field(default_factory=list)
    artifact_path: str | None = None
    checksum: str | None = None
    file_size_bytes: int = 0
    error_message: str | None = None


class ITrainingBackend(ABC):
    """Abstract interface for local or remote fine-tuning/training engines."""

    backend_name: str

    @abstractmethod
    async def run_job(
        self,
        job: TrainingJob,
        config: dict[str, Any],
        train_examples: list[dict[str, Any]],
        val_examples: list[dict[str, Any]],
    ) -> TrainingExecutionResult:
        """Executes a training or fine-tuning run asynchronously."""
        pass

    @abstractmethod
    async def cancel_job(self, job_id: str) -> bool:
        """Cancels an in-flight training job execution."""
        pass


class IModelArtifactStore(ABC):
    """Abstract persistence layer for model artifacts, checkpoints, and weights."""

    @abstractmethod
    async def save_artifact(
        self,
        job_id: str,
        content: bytes,
        filename: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Persists artifact bytes and returns canonical storage URI."""
        pass

    @abstractmethod
    async def load_artifact(self, artifact_path: str) -> bytes | None:
        """Retrieves raw artifact bytes from storage URI."""
        pass

    @abstractmethod
    async def compute_checksum(self, data: bytes) -> str:
        """Computes cryptographic digest of artifact content."""
        pass
