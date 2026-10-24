from abc import ABC, abstractmethod
from typing import Any, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class AIModel(ABC):
    """Abstract base class defining provider-independent AI model capabilities.

    Implementations can be local (e.g. Ollama, llama.cpp, vLLM),
    open-source self-hosted, or external model providers.
    """

    @abstractmethod
    async def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate unstructured text response."""
        pass

    @abstractmethod
    async def generate_structured(self, prompt: str, response_model: type[T], **kwargs: Any) -> T:
        """Generate structured response conforming to a Pydantic schema."""
        pass

    @abstractmethod
    async def embed(self, texts: list[str], **kwargs: Any) -> list[list[float]]:
        """Generate vector embeddings for input texts."""
        pass
