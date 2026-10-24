"""Advanced Opportunity Discovery and Semantic Retrieval package."""

from __future__ import annotations

from app.discovery.engine import AdvancedDiscoveryEngine
from app.discovery.indexing.indexer import DiscoveryIndexer
from app.discovery.interfaces import (
    KeywordRetriever,
    MetadataFilterService,
    Reranker,
    RetrievalEngine,
    SemanticRetriever,
    VectorStore,
)
from app.discovery.models import (
    FusionMethod,
    OpportunityCandidate,
    OpportunitySearchDocument,
    RetrievalFilters,
    RetrievalResult,
    SearchStrategy,
    VectorSearchResult,
)
from app.discovery.vector_store import get_vector_store

_discovery_engine: AdvancedDiscoveryEngine | None = None
_discovery_indexer: DiscoveryIndexer | None = None


def get_discovery_engine() -> AdvancedDiscoveryEngine:
    """Returns singleton AdvancedDiscoveryEngine instance."""
    global _discovery_engine
    if _discovery_engine is None:
        _discovery_engine = AdvancedDiscoveryEngine(vector_store=get_vector_store())
    return _discovery_engine


def get_discovery_indexer() -> DiscoveryIndexer:
    """Returns singleton DiscoveryIndexer instance."""
    global _discovery_indexer
    if _discovery_indexer is None:
        engine = get_discovery_engine()
        _discovery_indexer = DiscoveryIndexer(engine=engine, vector_store=engine.vector_store)
    return _discovery_indexer


__all__ = [
    "AdvancedDiscoveryEngine",
    "DiscoveryIndexer",
    "FusionMethod",
    "KeywordRetriever",
    "MetadataFilterService",
    "OpportunityCandidate",
    "OpportunitySearchDocument",
    "Reranker",
    "RetrievalEngine",
    "RetrievalFilters",
    "RetrievalResult",
    "SearchStrategy",
    "SemanticRetriever",
    "VectorSearchResult",
    "VectorStore",
    "get_discovery_engine",
    "get_discovery_indexer",
]
