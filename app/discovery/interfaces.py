"""Provider-independent interfaces for vector storage, retrieval, and reranking."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.discovery.models import (
    OpportunityCandidate,
    RetrievalFilters,
    RetrievalResult,
    SearchStrategy,
    VectorSearchResult,
)


class VectorStore(ABC):
    """Abstract provider-independent vector storage contract."""

    @abstractmethod
    async def upsert(
        self,
        document_id: str,
        vector: list[float],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Stores or updates a vector embedding by document identifier."""
        pass

    @abstractmethod
    async def upsert_batch(
        self,
        items: list[tuple[str, list[float], dict[str, Any]]],
    ) -> int:
        """Stores or updates a batch of vector embeddings."""
        pass

    @abstractmethod
    async def search(
        self,
        query_vector: list[float],
        limit: int = 100,
        filter_metadata: dict[str, Any] | None = None,
    ) -> list[VectorSearchResult]:
        """Performs nearest-neighbor vector similarity search."""
        pass

    @abstractmethod
    async def get(self, document_id: str) -> list[float] | None:
        """Retrieves raw vector by document identifier."""
        pass

    @abstractmethod
    async def delete(self, document_id: str) -> bool:
        """Removes vector by document identifier."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Verifies vector storage service connectivity and operational readiness."""
        pass


class KeywordRetriever(ABC):
    """Abstract interface for BM25/inverted-index text retrieval."""

    @abstractmethod
    async def search(
        self,
        query: str,
        filters: RetrievalFilters | None = None,
        limit: int = 100,
    ) -> list[OpportunityCandidate]:
        """Retrieves candidate opportunities using lexical matching."""
        pass


class SemanticRetriever(ABC):
    """Abstract interface for dense vector semantic retrieval."""

    @abstractmethod
    async def search(
        self,
        query_vector: list[float],
        filters: RetrievalFilters | None = None,
        limit: int = 100,
    ) -> list[OpportunityCandidate]:
        """Retrieves candidate opportunities using vector semantic similarity."""
        pass


class MetadataFilterService(ABC):
    """Abstract interface for evaluating hard and soft metadata constraints."""

    @abstractmethod
    def apply_hard_filters(
        self,
        candidates: list[OpportunityCandidate],
        filters: RetrievalFilters,
    ) -> list[OpportunityCandidate]:
        """Strictly eliminates candidates violating non-negotiable criteria."""
        pass


class Reranker(ABC):
    """Abstract interface for cross-encoder or neural semantic reranking."""

    @abstractmethod
    async def rerank(
        self,
        query: str,
        candidates: list[OpportunityCandidate],
        top_k: int = 50,
    ) -> list[OpportunityCandidate]:
        """Scores and re-orders candidates using deep cross-attention or semantic evaluation."""
        pass


class RetrievalEngine(ABC):
    """High-level facade orchestrating multi-stage discovery."""

    @abstractmethod
    async def search(
        self,
        query: str,
        filters: RetrievalFilters | None = None,
        user_profile: dict[str, Any] | None = None,
        strategy: SearchStrategy = SearchStrategy.HYBRID_RERANK,
        limit: int = 50,
    ) -> RetrievalResult:
        """Executes full discovery pipeline across lexical, semantic, and filtering stages."""
        pass
