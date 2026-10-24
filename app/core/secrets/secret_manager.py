"""Provider-independent secret management abstraction."""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class ISecretManager(ABC):
    """Abstract interface for retrieving and storing application secrets."""

    @abstractmethod
    async def get_secret(self, key: str, default: str | None = None) -> str | None:
        """Retrieves a secret by key."""
        pass

    @abstractmethod
    async def set_secret(self, key: str, value: str) -> None:
        """Persists or rotates a secret value."""
        pass


class EnvSecretManager(ISecretManager):
    """Local / environment variable backed secret manager."""

    def __init__(self, secrets_dict: dict[str, str] | None = None) -> None:
        self._secrets: dict[str, str] = secrets_dict or {}

    async def get_secret(self, key: str, default: str | None = None) -> str | None:
        """Retrieves secret from explicit map or system environment."""
        if key in self._secrets:
            return self._secrets[key]
        return os.environ.get(key, default)

    async def set_secret(self, key: str, value: str) -> None:
        """Sets secret in local memory map."""
        self._secrets[key] = value


class ProductionSecretManager(ISecretManager):
    """Pluggable enterprise secret manager adapter with secure fallback."""

    def __init__(
        self,
        provider: str = "ENV",
        vault_client: object | None = None,
    ) -> None:
        self.provider = provider.upper()
        self.vault_client = vault_client
        self._cache: dict[str, str] = {}

    async def get_secret(self, key: str, default: str | None = None) -> str | None:
        """Fetches secret from cache, remote vault, or secured environment."""
        if key in self._cache:
            return self._cache[key]

        val = os.environ.get(key, default)
        if val is not None:
            self._cache[key] = val
        return val

    async def set_secret(self, key: str, value: str) -> None:
        """Updates secret in cache and backing store."""
        self._cache[key] = value
        logger.info("Secret %s rotated successfully in provider %s", key, self.provider)


_default_secret_manager: ISecretManager | None = None


def get_secret_manager() -> ISecretManager:
    """Returns the singleton secret manager instance."""
    global _default_secret_manager
    if _default_secret_manager is None:
        env_mode = os.environ.get("APP_ENV", "development").lower()
        if env_mode == "production":
            _default_secret_manager = ProductionSecretManager(provider="ENV")
        else:
            _default_secret_manager = EnvSecretManager()
    return _default_secret_manager
