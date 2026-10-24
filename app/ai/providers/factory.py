from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any, TypeVar

from pydantic import BaseModel

from app.ai.interfaces.base import AIModel
from app.core.exceptions import AIProviderException

T = TypeVar("T", bound=BaseModel)


class ProviderType(StrEnum):
    LOCAL = "local"
    OPEN_SOURCE = "open_source"
    EXTERNAL = "external"
    MOCK = "mock"


class AIModelProvider(ABC):
    """Abstract base class for all AI provider backends."""

    def __init__(self, provider_name: str, config: dict[str, Any] | None = None) -> None:
        self.provider_name = provider_name
        self.config = config or {}

    @abstractmethod
    def get_model(self, model_name: str) -> AIModel:
        """Retrieve or instantiate an AIModel instance for this provider."""
        pass


class LocalModelProvider(AIModelProvider):
    """Provider for locally hosted inference engines (Ollama, llama.cpp, vLLM)."""

    def get_model(self, model_name: str) -> AIModel:
        # Stub for future local engine connection
        raise NotImplementedError(
            "Local model inference engine will be configured in future phase."
        )


class OpenSourceModelProvider(AIModelProvider):
    """Provider for self-hosted open-weights models (HuggingFace TGI, vLLM cluster)."""

    def get_model(self, model_name: str) -> AIModel:
        # Stub for future self-hosted cluster connection
        raise NotImplementedError(
            "Open-source cluster model provider will be configured in future phase."
        )


class ExternalModelProvider(AIModelProvider):
    """Provider for optional third-party commercial APIs."""

    def get_model(self, model_name: str) -> AIModel:
        # Stub for optional external APIs
        raise NotImplementedError("External model provider will be configured in future phase.")


class MockAIModel(AIModel):
    """Mock model implementation used for tests and offline architectural validation."""

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        return f"Mock response for prompt: {prompt[:30]}..."

    async def generate_structured(self, prompt: str, response_model: type[T], **kwargs: Any) -> T:
        # Returns an empty/default instantiated model for test verification
        return response_model.model_validate(response_model.model_construct())

    async def embed(self, texts: list[str], **kwargs: Any) -> list[list[float]]:
        return [[0.0] * 384 for _ in texts]


class MockModelProvider(AIModelProvider):
    """Mock provider for unit testing and offline development."""

    def get_model(self, model_name: str) -> AIModel:
        return MockAIModel()


def get_ai_provider(provider_type: str | ProviderType) -> AIModelProvider:
    """Factory to retrieve an AIModelProvider by type."""
    ptype = str(provider_type).lower()
    if ptype == ProviderType.MOCK:
        return MockModelProvider("mock")
    if ptype == ProviderType.LOCAL:
        return LocalModelProvider("local")
    if ptype == ProviderType.OPEN_SOURCE:
        return OpenSourceModelProvider("open_source")
    if ptype == ProviderType.EXTERNAL:
        return ExternalModelProvider("external")

    raise AIProviderException(
        message=f"Unsupported AI model provider type: '{provider_type}'",
        provider=str(provider_type),
    )
