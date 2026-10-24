"""Model and prompt registry interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod

from sqlalchemy.ext.asyncio import AsyncSession

from app.learning.models.model_registry import ModelDefinition
from app.learning.models.prompt_version import PromptVersionRecord
from app.learning.schemas.learning import ModelDefinitionCreate, PromptVersionCreate


class IModelRegistry(ABC):
    """Abstract registry for tracking models across local and cloud providers."""

    @abstractmethod
    async def register_model(
        self,
        db: AsyncSession,
        payload: ModelDefinitionCreate,
    ) -> ModelDefinition:
        pass

    @abstractmethod
    async def get_active_model(
        self,
        db: AsyncSession,
        model_id: str,
    ) -> ModelDefinition | None:
        pass


class IPromptRegistry(ABC):
    """Abstract registry for prompt versions and templates."""

    @abstractmethod
    async def register_prompt_version(
        self,
        db: AsyncSession,
        payload: PromptVersionCreate,
    ) -> PromptVersionRecord:
        pass

    @abstractmethod
    async def get_prompt_version(
        self,
        db: AsyncSession,
        prompt_name: str,
        version: str,
    ) -> PromptVersionRecord | None:
        pass
