"""Incremental indexing service managing opportunity search documents and vector embeddings."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.discovery.embedding.pipeline import OpportunityEmbeddingPipeline
from app.discovery.engine import AdvancedDiscoveryEngine
from app.discovery.interfaces import VectorStore
from app.discovery.models import OpportunitySearchDocument
from app.models.opportunity import Opportunity

logger = logging.getLogger(__name__)


class DiscoveryIndexer:
    """Synchronizes relational opportunities with dense vector and lexical indices."""

    def __init__(
        self,
        engine: AdvancedDiscoveryEngine,
        vector_store: VectorStore,
        pipeline: OpportunityEmbeddingPipeline | None = None,
    ) -> None:
        self.engine = engine
        self.vector_store = vector_store
        self.pipeline = pipeline or OpportunityEmbeddingPipeline()
        self._seen_hashes: dict[str, str] = {}

    async def index_opportunity(self, opportunity: Opportunity) -> OpportunitySearchDocument:
        """Transforms, embeds, and indexes a single opportunity record incrementally."""
        doc = self.pipeline.build_search_document(opportunity)

        # Check if content has changed
        prior_hash = self._seen_hashes.get(doc.opportunity_id)
        if prior_hash == doc.content_hash:
            logger.debug("Skipping unchanged opportunity %s", doc.opportunity_id)
            return doc

        # Generate dense vector
        vector = await self.pipeline.embed_document(doc)

        # Store in vector store
        metadata = {
            "title": doc.title,
            "provider": doc.provider,
            "category": doc.category,
            "status": doc.status,
            "content_hash": doc.content_hash,
            "version": self.pipeline.version,
        }
        await self.vector_store.upsert(doc.opportunity_id, vector, metadata=metadata)

        # Store document in engine
        self.engine.index_document(doc)
        self._seen_hashes[doc.opportunity_id] = doc.content_hash
        return doc

    async def reindex_all(self, db: AsyncSession) -> dict[str, int]:
        """Scans database and updates all active opportunities in search index."""
        from sqlalchemy.orm import selectinload

        stmt = select(Opportunity).options(
            selectinload(Opportunity.sources),
            selectinload(Opportunity.requirements),
            selectinload(Opportunity.evidences),
        )
        res = await db.execute(stmt)
        opportunities = res.scalars().all()

        indexed = 0
        skipped = 0
        errors = 0

        for opp in opportunities:
            try:
                doc = self.pipeline.build_search_document(opp)
                if self._seen_hashes.get(doc.opportunity_id) == doc.content_hash:
                    skipped += 1
                else:
                    await self.index_opportunity(opp)
                    indexed += 1
            except Exception as exc:
                logger.warning("Error indexing opportunity %s: %s", opp.id, exc)
                errors += 1

        return {
            "total_found": len(opportunities),
            "indexed": indexed,
            "skipped_unchanged": skipped,
            "errors": errors,
        }
