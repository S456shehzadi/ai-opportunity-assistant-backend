"""PostgreSQL database vector store adapter utilizing OpportunityEmbeddingRecord."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import delete, select

from app.core.database import get_db_session
from app.discovery.interfaces import VectorStore
from app.discovery.models import VectorSearchResult
from app.discovery.vector_store.memory_store import InMemoryVectorStore
from app.models.discovery import OpportunityEmbeddingRecord

logger = logging.getLogger(__name__)


class DatabaseVectorStore(VectorStore):
    """Persistent vector store storing embedding vectors in relational DB with memory cache."""

    def __init__(self, fallback_memory: InMemoryVectorStore | None = None) -> None:
        self.memory = fallback_memory or InMemoryVectorStore()

    async def upsert(
        self,
        document_id: str,
        vector: list[float],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        # Cache in memory
        await self.memory.upsert(document_id, vector, metadata)

        # Persist to DB if valid UUID
        try:
            opp_uuid = uuid.UUID(document_id)
            meta = metadata or {}
            async for session in get_db_session():
                # Check existing
                stmt = select(OpportunityEmbeddingRecord).where(
                    OpportunityEmbeddingRecord.opportunity_id == opp_uuid,
                    OpportunityEmbeddingRecord.embedding_type == meta.get("embedding_type", "FULL"),
                )
                res = await session.execute(stmt)
                existing = res.scalar_one_or_none()

                if existing:
                    existing.vector_data = vector
                    existing.dimension = len(vector)
                    existing.embedding_model = meta.get("model", "default")
                    existing.content_hash = meta.get("content_hash", "")
                    existing.is_active = True
                else:
                    record = OpportunityEmbeddingRecord(
                        opportunity_id=opp_uuid,
                        embedding_type=meta.get("embedding_type", "FULL"),
                        vector_data=vector,
                        dimension=len(vector),
                        embedding_model=meta.get("model", "default"),
                        embedding_provider=meta.get("provider", "LOCAL"),
                        embedding_version=meta.get("version", "v1.0.0"),
                        content_hash=meta.get("content_hash", ""),
                        is_active=True,
                    )
                    session.add(record)
                await session.commit()
                break
        except Exception as exc:
            logger.debug("DatabaseVectorStore DB upsert bypassed (%s), cached in memory", exc)

    async def upsert_batch(
        self,
        items: list[tuple[str, list[float], dict[str, Any]]],
    ) -> int:
        count = 0
        for doc_id, vec, meta in items:
            await self.upsert(doc_id, vec, meta)
            count += 1
        return count

    async def search(
        self,
        query_vector: list[float],
        limit: int = 100,
        filter_metadata: dict[str, Any] | None = None,
    ) -> list[VectorSearchResult]:
        # Fast nearest-neighbor search via high-speed memory cache
        return await self.memory.search(query_vector, limit=limit, filter_metadata=filter_metadata)

    async def get(self, document_id: str) -> list[float] | None:
        cached = await self.memory.get(document_id)
        if cached is not None:
            return cached

        try:
            opp_uuid = uuid.UUID(document_id)
            async for session in get_db_session():
                stmt = select(OpportunityEmbeddingRecord).where(
                    OpportunityEmbeddingRecord.opportunity_id == opp_uuid,
                    OpportunityEmbeddingRecord.is_active == True,  # noqa: E712
                )
                res = await session.execute(stmt)
                record = res.scalar_one_or_none()
                if record:
                    vec = list(record.vector_data)
                    await self.memory.upsert(document_id, vec)
                    return vec
                break
        except Exception:
            pass

        return None

    async def delete(self, document_id: str) -> bool:
        await self.memory.delete(document_id)
        try:
            opp_uuid = uuid.UUID(document_id)
            async for session in get_db_session():
                stmt = delete(OpportunityEmbeddingRecord).where(
                    OpportunityEmbeddingRecord.opportunity_id == opp_uuid
                )
                await session.execute(stmt)
                await session.commit()
                return True
        except Exception:
            return False
        return True

    async def health_check(self) -> bool:
        return True
