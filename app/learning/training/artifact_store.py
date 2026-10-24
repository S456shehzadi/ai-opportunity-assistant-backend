"""Local disk implementation of model artifact store."""

from __future__ import annotations

import hashlib
import os
from typing import Any

from app.learning.interfaces.training import IModelArtifactStore


class LocalModelArtifactStore(IModelArtifactStore):
    """Stores and retrieves serialized weights and checkpoints from local storage."""

    def __init__(self, base_directory: str = "app/data/model_artifacts") -> None:
        self.base_directory = base_directory
        os.makedirs(self.base_directory, exist_ok=True)

    async def compute_checksum(self, data: bytes) -> str:
        """Computes SHA-256 hash digest."""
        return hashlib.sha256(data).hexdigest()

    async def save_artifact(
        self,
        job_id: str,
        content: bytes,
        filename: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Persists artifact binary to target path."""
        target_dir = os.path.join(self.base_directory, str(job_id))
        os.makedirs(target_dir, exist_ok=True)
        file_path = os.path.join(target_dir, filename)
        with open(file_path, "wb") as f:
            f.write(content)
        return file_path

    async def load_artifact(self, artifact_path: str) -> bytes | None:
        """Loads artifact binary from file."""
        if not os.path.exists(artifact_path):
            return None
        with open(artifact_path, "rb") as f:
            return f.read()
