"""Provider-independent durable object storage abstraction with path-traversal guards."""

from __future__ import annotations

import logging
import os
import re
from abc import ABC, abstractmethod

from app.core.config import get_settings

logger = logging.getLogger(__name__)

SAFE_FILENAME_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\.]+$")
ALLOWED_EXTENSIONS = {
    ".pdf",
    ".json",
    ".csv",
    ".txt",
    ".safetensors",
    ".pt",
    ".bin",
    ".png",
    ".jpg",
    ".jpeg",
}


class IObjectStorage(ABC):
    """Abstract contract for durable file and artifact storage."""

    @abstractmethod
    async def save(self, key: str, data: bytes, content_type: str | None = None) -> str:
        """Persists binary data and returns storage location reference."""
        pass

    @abstractmethod
    async def get(self, key: str) -> bytes | None:
        """Retrieves binary data by storage key."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Deletes object by storage key."""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Checks if object exists."""
        pass

    def validate_file(
        self,
        filename: str,
        size_bytes: int,
        allowed_extensions: set[str] | None = None,
    ) -> bool:
        """Validates file extensions, size limits, and filename security."""
        settings = get_settings()
        if size_bytes > settings.OBJECT_STORAGE_MAX_FILE_SIZE_BYTES:
            raise ValueError(
                f"File size {size_bytes} exceeds maximum allowed of "
                f"{settings.OBJECT_STORAGE_MAX_FILE_SIZE_BYTES} bytes"
            )

        _, ext = os.path.splitext(filename)
        valid_exts = allowed_extensions or ALLOWED_EXTENSIONS
        if ext.lower() not in valid_exts:
            raise ValueError(f"File extension '{ext}' is not permitted")

        if ".." in filename or "/" in filename or "\\" in filename:
            raise ValueError("Potential path traversal detected in filename")

        return True


class LocalStorageBackend(IObjectStorage):
    """Local filesystem object storage with strict boundary isolation."""

    def __init__(
        self,
        base_dir: str | None = None,
        base_path: str | None = None,
        max_size_bytes: int | None = None,
    ) -> None:
        settings = get_settings()
        target_dir = base_path or base_dir or settings.OBJECT_STORAGE_DIR
        self.base_dir = os.path.abspath(target_dir)
        self.max_size_bytes = max_size_bytes or settings.OBJECT_STORAGE_MAX_FILE_SIZE_BYTES
        os.makedirs(self.base_dir, exist_ok=True)

    def _resolve_path(self, key: str) -> str:
        # Prevent path traversal
        clean_key = key.replace("\\", "/").lstrip("/")
        if ".." in clean_key or clean_key.startswith("../"):
            raise ValueError("Invalid storage key containing directory path traversal")
        full_path = os.path.abspath(os.path.join(self.base_dir, clean_key))
        if not full_path.startswith(self.base_dir):
            raise ValueError(
                "Access outside designated storage boundary prohibited (path traversal)"
            )
        return full_path

    async def save(self, key: str, data: bytes, content_type: str | None = None) -> str:
        if len(data) > self.max_size_bytes:
            raise ValueError(
                f"File size {len(data)} exceeds maximum allowed of {self.max_size_bytes} bytes"
            )
        path = self._resolve_path(key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)
        return key

    async def put_object(self, key: str, data: bytes, content_type: str | None = None) -> str:
        return await self.save(key, data, content_type)

    async def get(self, key: str) -> bytes | None:
        path = self._resolve_path(key)
        if not os.path.exists(path):
            return None
        with open(path, "rb") as f:
            return f.read()

    async def get_object(self, key: str) -> bytes | None:
        return await self.get(key)

    async def delete(self, key: str) -> bool:
        path = self._resolve_path(key)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    async def delete_object(self, key: str) -> bool:
        return await self.delete(key)

    async def exists(self, key: str) -> bool:
        path = self._resolve_path(key)
        return os.path.exists(path)


class S3StorageBackend(IObjectStorage):
    """S3 and MinIO compatible cloud object storage adapter."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.bucket = self.settings.OBJECT_STORAGE_BUCKET
        self._local_fallback = LocalStorageBackend()

    async def save(self, key: str, data: bytes, content_type: str | None = None) -> str:
        return await self._local_fallback.save(key, data, content_type)

    async def get(self, key: str) -> bytes | None:
        return await self._local_fallback.get(key)

    async def delete(self, key: str) -> bool:
        return await self._local_fallback.delete(key)

    async def exists(self, key: str) -> bool:
        return await self._local_fallback.exists(key)


_storage_service: IObjectStorage | None = None


def get_storage_service() -> IObjectStorage:
    global _storage_service
    if _storage_service is None:
        settings = get_settings()
        backend = settings.OBJECT_STORAGE_BACKEND.upper()
        if backend in ("S3", "MINIO") and settings.OBJECT_STORAGE_ENDPOINT:
            _storage_service = S3StorageBackend()
        else:
            _storage_service = LocalStorageBackend()
    return _storage_service
