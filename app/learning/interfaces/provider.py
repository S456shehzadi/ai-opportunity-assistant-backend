"""Provider abstraction for heterogeneous AI runtime engines."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum

from app.learning.interfaces.model import AIModel
from app.learning.models.model_registry import ModelDefinition


class ModelProviderType(StrEnum):
    """Categorized model runtime providers."""

    LOCAL = "LOCAL"
    SELF_HOSTED = "SELF_HOSTED"
    CLOUD = "CLOUD"
    HUGGING_FACE = "HUGGING_FACE"
    VLLM = "VLLM"
    OLLAMA = "OLLAMA"
    TRANSFORMERS = "TRANSFORMERS"
    CUSTOM = "CUSTOM"


class IModelProvider(ABC):
    """Abstract provider that instantiates and monitors AI model runtimes."""

    provider_type: ModelProviderType

    @abstractmethod
    async def load_model(self, model_definition: ModelDefinition) -> AIModel:
        """Instantiates an operational AIModel client according to configuration."""
        pass

    @abstractmethod
    async def health_check(self, model_definition: ModelDefinition) -> bool:
        """Determines if the backend engine serving the model is accessible."""
        pass

    @abstractmethod
    async def unload_model(self, model_id: str) -> bool:
        """Gracefully frees memory or disconnects model resources."""
        pass
