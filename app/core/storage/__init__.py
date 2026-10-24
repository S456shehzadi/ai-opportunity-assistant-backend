"""Storage module."""

from app.core.storage.storage_service import (
    IObjectStorage,
    LocalStorageBackend,
    S3StorageBackend,
    get_storage_service,
)

__all__ = [
    "IObjectStorage",
    "LocalStorageBackend",
    "S3StorageBackend",
    "get_storage_service",
]
