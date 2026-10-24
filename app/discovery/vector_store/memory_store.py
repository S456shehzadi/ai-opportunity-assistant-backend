"""In-memory cosine-similarity vector store for tests, development, and resilient fallback."""

from __future__ import annotations

import math
import threading
from typing import Any

from app.discovery.interfaces import VectorStore
from app.discovery.models import VectorSearchResult


def _cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Computes cosine similarity between two float vectors [-1.0, 1.0]."""
    if len(v1) != len(v2) or not v1:
        return 0.0

    dot = sum(a * b for a, b in zip(v1, v2, strict=True))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))

    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0

    score = dot / (norm1 * norm2)
    # Clamp for numerical float precision
    return max(-1.0, min(1.0, score))


class InMemoryVectorStore(VectorStore):
    """Thread-safe in-memory vector store supporting exact nearest-neighbor search."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._vectors: dict[str, list[float]] = {}
        self._metadata: dict[str, dict[str, Any]] = {}

    async def upsert(
        self,
        document_id: str,
        vector: list[float],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        with self._lock:
            self._vectors[document_id] = list(vector)
            self._metadata[document_id] = dict(metadata or {})

    async def upsert_batch(
        self,
        items: list[tuple[str, list[float], dict[str, Any]]],
    ) -> int:
        count = 0
        with self._lock:
            for doc_id, vec, meta in items:
                self._vectors[doc_id] = list(vec)
                self._metadata[doc_id] = dict(meta)
                count += 1
        return count

    async def search(
        self,
        query_vector: list[float],
        limit: int = 100,
        filter_metadata: dict[str, Any] | None = None,
    ) -> list[VectorSearchResult]:
        with self._lock:
            candidates: list[VectorSearchResult] = []
            for doc_id, vec in self._vectors.items():
                meta = self._metadata.get(doc_id, {})

                # Check metadata filters if specified
                if filter_metadata:
                    match = True
                    for k, v in filter_metadata.items():
                        if k in meta and meta[k] != v:
                            match = False
                            break
                    if not match:
                        continue

                sim = _cosine_similarity(query_vector, vec)
                # Normalize cosine similarity from [-1, 1] to [0, 1]
                normalized_score = (sim + 1.0) / 2.0
                candidates.append(
                    VectorSearchResult(
                        document_id=doc_id,
                        score=round(normalized_score, 4),
                        metadata=meta,
                        vector=vec,
                    )
                )

            # Sort descending by similarity
            candidates.sort(key=lambda x: x.score, reverse=True)
            return candidates[:limit]

    async def get(self, document_id: str) -> list[float] | None:
        with self._lock:
            return self._vectors.get(document_id)

    async def delete(self, document_id: str) -> bool:
        with self._lock:
            removed = False
            if document_id in self._vectors:
                del self._vectors[document_id]
                removed = True
            if document_id in self._metadata:
                del self._metadata[document_id]
            return removed

    async def health_check(self) -> bool:
        return True

    def count(self) -> int:
        with self._lock:
            return len(self._vectors)

    def clear(self) -> None:
        with self._lock:
            self._metadata.clear()
            self._vectors.clear()
