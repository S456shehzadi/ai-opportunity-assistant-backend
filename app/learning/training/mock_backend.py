"""Deterministic local mock training backend for testing and CPU execution."""

from __future__ import annotations

import asyncio
import hashlib
import os
import time
from datetime import UTC, datetime
from typing import Any

from app.learning.interfaces.training import ITrainingBackend, TrainingExecutionResult
from app.learning.models.training_job import TrainingJob


class MockLocalTrainingBackend(ITrainingBackend):
    """Safe local training backend simulating loss, epochs, metrics, and artifact output."""

    backend_name = "LOCAL_MOCK"

    def __init__(self, artifact_dir: str = "app/data/model_artifacts") -> None:
        self.artifact_dir = artifact_dir
        self.cancelled_jobs: set[str] = set()
        os.makedirs(self.artifact_dir, exist_ok=True)

    async def cancel_job(self, job_id: str) -> bool:
        """Flags job as cancelled to interrupt execution loop."""
        self.cancelled_jobs.add(job_id)
        return True

    async def run_job(
        self,
        job: TrainingJob,
        config: dict[str, Any],
        train_examples: list[dict[str, Any]],
        val_examples: list[dict[str, Any]],
    ) -> TrainingExecutionResult:
        """Executes simulated training loop with metric computation and artifact emission."""
        job_id_str = str(job.id)
        epochs = int(config.get("epochs", 3))
        max_duration = int(config.get("max_duration_seconds", 3600))
        start_time = time.time()

        logs: list[dict[str, Any]] = [
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "level": "INFO",
                "message": f"Initialized training backend {self.backend_name} for task {job.task}",
            },
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "level": "INFO",
                "message": (
                    f"Train set size: {len(train_examples)}, Val set size: {len(val_examples)}"
                ),
            },
        ]

        loss = 2.0
        val_loss = 2.2
        accuracy = 0.65
        f1 = 0.60

        for epoch in range(1, epochs + 1):
            if job_id_str in self.cancelled_jobs:
                logs.append(
                    {
                        "timestamp": datetime.now(UTC).isoformat(),
                        "level": "WARNING",
                        "message": f"Job {job_id_str} was cancelled at epoch {epoch}",
                    }
                )
                return TrainingExecutionResult(
                    success=False,
                    metrics={"final_epoch": epoch - 1},
                    logs=logs,
                    error_message="Job cancelled by operator",
                )

            if time.time() - start_time > max_duration:
                logs.append(
                    {
                        "timestamp": datetime.now(UTC).isoformat(),
                        "level": "ERROR",
                        "message": f"Exceeded max duration limit of {max_duration}s",
                    }
                )
                return TrainingExecutionResult(
                    success=False,
                    metrics={"final_epoch": epoch - 1},
                    logs=logs,
                    error_message="Job exceeded timeout limit",
                )

            await asyncio.sleep(0.01)

            loss = max(0.08, 1.8 / (1.0 + epoch * 0.45))
            val_loss = max(0.12, 1.9 / (1.0 + epoch * 0.40))
            accuracy = min(0.96, 0.65 + epoch * 0.09)
            f1 = min(0.95, 0.62 + epoch * 0.09)

            logs.append(
                {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "level": "INFO",
                    "epoch": epoch,
                    "train_loss": round(loss, 4),
                    "val_loss": round(val_loss, 4),
                    "val_accuracy": round(accuracy, 4),
                    "val_f1": round(f1, 4),
                }
            )

        # Generate simulated model artifact
        filename = f"model_{job.task.lower()}_{job_id_str[:8]}.safetensors"
        file_path = os.path.join(self.artifact_dir, filename)
        artifact_bytes = f"WEIGHTS_DATA_{job.base_model}_{job.task}_{job_id_str}".encode()

        with open(file_path, "wb") as f:
            f.write(artifact_bytes)

        checksum = hashlib.sha256(artifact_bytes).hexdigest()
        file_size = len(artifact_bytes)

        metrics = {
            "epochs_completed": epochs,
            "final_train_loss": round(loss, 4),
            "final_val_loss": round(val_loss, 4),
            "val_accuracy": round(accuracy, 4),
            "val_f1": round(f1, 4),
            "duration_seconds": round(time.time() - start_time, 2),
        }

        logs.append(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "level": "INFO",
                "message": f"Training completed successfully. Checksum: {checksum}",
            }
        )

        return TrainingExecutionResult(
            success=True,
            metrics=metrics,
            logs=logs,
            artifact_path=file_path,
            checksum=checksum,
            file_size_bytes=file_size,
        )
