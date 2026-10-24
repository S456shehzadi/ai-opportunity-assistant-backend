"""Capability-based specialized AI model abstractions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from app.learning.models.model_registry import ModelType


class ModelCapability(StrEnum):
    """Specific functional capabilities provided by a model."""

    TEXT_GENERATION = "TEXT_GENERATION"
    EMBEDDING = "EMBEDDING"
    CLASSIFICATION = "CLASSIFICATION"
    RERANKING = "RERANKING"


@dataclass
class GeneratedTextResponse:
    """Standardized response from text generation execution."""

    text: str
    finish_reason: str = "stop"
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ClassificationResult:
    """Classification prediction with confidence breakdown."""

    top_label: str
    confidence: float
    all_scores: dict[str, float] = field(default_factory=dict)
    latency_ms: float = 0.0


@dataclass
class RerankResult:
    """Document reranking result with assigned relevance score."""

    index: int
    score: float
    document: str


class AIModel(ABC):
    """Base interface for all registered specialized or generalist models."""

    def __init__(
        self,
        model_id: str,
        task: ModelType,
        provider_name: str,
        capabilities: list[ModelCapability],
    ) -> None:
        self.model_id = model_id
        self.task = task
        self.provider_name = provider_name
        self.capabilities = capabilities

    @abstractmethod
    async def is_available(self) -> bool:
        """Determines whether the model is healthy and receptive to requests."""
        pass


class TextGenerationModel(AIModel):
    """Model abstraction for text generation and structured extraction."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        context: dict[str, Any] | None = None,
        max_tokens: int = 512,
        temperature: float = 0.0,
    ) -> GeneratedTextResponse:
        """Generates textual response given prompt and optional context."""
        pass


class EmbeddingModel(AIModel):
    """Model abstraction for dense vector representation."""

    @abstractmethod
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embeds multiple documents into vector representations."""
        pass

    @abstractmethod
    async def embed_query(self, text: str) -> list[float]:
        """Embeds single query string into vector representation."""
        pass


class ClassificationModel(AIModel):
    """Model abstraction for discrete intent or domain categorization."""

    @abstractmethod
    async def classify(
        self,
        text: str,
        candidate_labels: list[str] | None = None,
    ) -> ClassificationResult:
        """Categorizes input text against candidate classes."""
        pass


class RerankingModel(AIModel):
    """Model abstraction for cross-encoder or neural reranking."""

    @abstractmethod
    async def rerank(
        self,
        query: str,
        documents: list[str],
        top_k: int | None = None,
    ) -> list[RerankResult]:
        """Scores and reorders candidate documents relative to query."""
        pass
