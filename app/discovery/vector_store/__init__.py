"""Vector storage exports and factory."""

from __future__ import annotations

from app.discovery.interfaces import VectorStore
from app.discovery.vector_store.memory_store import InMemoryVectorStore
from app.discovery.vector_store.pg_store import DatabaseVectorStore

_default_vector_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    """Returns singleton vector store instance."""
    global _default_vector_store
    if _default_vector_store is None:
        _default_vector_store = DatabaseVectorStore()
    return _default_vector_store


__all__ = [
    "DatabaseVectorStore",
    "InMemoryVectorStore",
    "VectorStore",
    "get_vector_store",
]
