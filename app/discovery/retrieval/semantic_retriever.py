"""Vector semantic retriever querying dense representations."""

from __future__ import annotations

from app.discovery.interfaces import SemanticRetriever, VectorStore
from app.discovery.models import (
    OpportunityCandidate,
    OpportunitySearchDocument,
    RetrievalFilters,
    VectorSearchResult,
)


class VectorSemanticRetriever(SemanticRetriever):
    """Retrieves candidates using vector similarity search against VectorStore."""

    def __init__(
        self,
        vector_store: VectorStore,
        documents: dict[str, OpportunitySearchDocument] | None = None,
    ) -> None:
        self.vector_store = vector_store
        self.documents = documents if documents is not None else {}

    def set_documents(self, documents: dict[str, OpportunitySearchDocument]) -> None:
        self.documents = documents

    async def search(
        self,
        query_vector: list[float],
        filters: RetrievalFilters | None = None,
        limit: int = 100,
    ) -> list[OpportunityCandidate]:
        results: list[VectorSearchResult] = await self.vector_store.search(
            query_vector,
            limit=limit,
        )

        candidates: list[OpportunityCandidate] = []
        for res in results:
            doc = self.documents.get(res.document_id)
            if not doc:
                # Fallback placeholder if full document not in memory
                doc = OpportunitySearchDocument(
                    opportunity_id=res.document_id,
                    title=res.metadata.get("title", f"Opportunity {res.document_id}"),
                    provider=res.metadata.get("provider", "Unknown Provider"),
                    category=res.metadata.get("category", "Scholarship"),
                    description=res.metadata.get("description", ""),
                )

            candidate = OpportunityCandidate(
                opportunity_id=res.document_id,
                title=doc.title,
                provider=doc.provider,
                category=doc.category,
                document=doc,
                semantic_score=round(res.score, 4),
                retrieval_sources=["SEMANTIC"],
                canonical_source_url=doc.source_url,
                cluster_source_urls=[doc.source_url] if doc.source_url else [],
            )
            candidates.append(candidate)

        return candidates
