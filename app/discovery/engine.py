"""Advanced Opportunity Discovery Engine orchestrating hybrid retrieval,
expansion, and reranking.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from app.discovery.embedding.pipeline import OpportunityEmbeddingPipeline
from app.discovery.interfaces import RetrievalEngine, VectorStore
from app.discovery.models import (
    FusionMethod,
    OpportunityCandidate,
    OpportunitySearchDocument,
    RetrievalFilters,
    RetrievalResult,
    SearchStrategy,
)
from app.discovery.query.expansion import QueryExpansionService
from app.discovery.query.rewriter import SemanticQueryRewriter
from app.discovery.retrieval.deduplication import OpportunityIdentityService
from app.discovery.retrieval.diversity import DiversityOptimizer
from app.discovery.retrieval.freshness import FreshnessAndTrustScorer
from app.discovery.retrieval.fusion import CandidateFusionService
from app.discovery.retrieval.keyword_retriever import LexicalKeywordRetriever
from app.discovery.retrieval.metadata_filter import StructuredMetadataFilter
from app.discovery.retrieval.reranker import SemanticReranker
from app.discovery.retrieval.semantic_retriever import VectorSemanticRetriever
from app.discovery.vector_store import get_vector_store

logger = logging.getLogger(__name__)


class AdvancedDiscoveryEngine(RetrievalEngine):
    """Orchestrates multi-stage semantic and keyword opportunity discovery
    with graceful fallbacks.
    """

    def __init__(
        self,
        vector_store: VectorStore | None = None,
        embedding_pipeline: OpportunityEmbeddingPipeline | None = None,
        keyword_retriever: LexicalKeywordRetriever | None = None,
        query_expansion: QueryExpansionService | None = None,
        query_rewriter: SemanticQueryRewriter | None = None,
        metadata_filter: StructuredMetadataFilter | None = None,
        fusion_service: CandidateFusionService | None = None,
        reranker: SemanticReranker | None = None,
        freshness_scorer: FreshnessAndTrustScorer | None = None,
        diversity_optimizer: DiversityOptimizer | None = None,
        identity_service: OpportunityIdentityService | None = None,
    ) -> None:
        self.vector_store = vector_store or get_vector_store()
        self.embedding_pipeline = embedding_pipeline or OpportunityEmbeddingPipeline()
        self.keyword_retriever = keyword_retriever or LexicalKeywordRetriever()
        self.query_expansion = query_expansion or QueryExpansionService()
        self.query_rewriter = query_rewriter or SemanticQueryRewriter()
        self.metadata_filter = metadata_filter or StructuredMetadataFilter()
        self.fusion_service = fusion_service or CandidateFusionService(method=FusionMethod.RRF)
        self.reranker = reranker or SemanticReranker()
        self.freshness_scorer = freshness_scorer or FreshnessAndTrustScorer()
        self.diversity_optimizer = diversity_optimizer or DiversityOptimizer()
        self.identity_service = identity_service or OpportunityIdentityService()

        # In-memory document index cache
        self._documents: dict[str, OpportunitySearchDocument] = {}
        self.semantic_retriever = VectorSemanticRetriever(
            vector_store=self.vector_store,
            documents=self._documents,
        )

    def index_document(self, doc: OpportunitySearchDocument) -> None:
        """Indexes a canonical opportunity document into memory caches and lexical retriever."""
        self._documents[doc.opportunity_id] = doc
        self.keyword_retriever.index_document(doc)
        self.semantic_retriever.set_documents(self._documents)

    def index_documents(self, docs: list[OpportunitySearchDocument]) -> None:
        for d in docs:
            self.index_document(d)

    async def search(
        self,
        query: str,
        filters: RetrievalFilters | None = None,
        user_profile: dict[str, Any] | None = None,
        strategy: SearchStrategy = SearchStrategy.HYBRID_RERANK,
        limit: int = 50,
    ) -> RetrievalResult:
        start_time = time.monotonic()
        clean_query = query.strip()

        # 1. Semantic query rewriting & intent extraction
        semantic_query, effective_filters = self.query_rewriter.rewrite_and_extract_filters(
            clean_query, base_filters=filters
        )

        # 2. Controlled query expansion
        expanded_queries = self.query_expansion.expand(semantic_query)

        keyword_candidates: list[OpportunityCandidate] = []
        semantic_candidates: list[OpportunityCandidate] = []
        retrieval_errors: list[str] = []

        # 3. Keyword candidate retrieval (Lexical)
        if strategy in (
            SearchStrategy.KEYWORD,
            SearchStrategy.HYBRID,
            SearchStrategy.HYBRID_RERANK,
        ):
            try:
                # Search across expanded query variants
                seen_kw_ids: set[str] = set()
                for q_var in expanded_queries:
                    kw_results = await self.keyword_retriever.search(
                        q_var, filters=effective_filters, limit=limit * 2
                    )
                    for c in kw_results:
                        if c.opportunity_id not in seen_kw_ids:
                            seen_kw_ids.add(c.opportunity_id)
                            keyword_candidates.append(c)
            except Exception as exc:
                logger.warning("Keyword retrieval failure: %s", exc)
                retrieval_errors.append(f"Keyword retrieval: {exc}")

        # 4. Semantic vector retrieval (Dense)
        if strategy in (
            SearchStrategy.SEMANTIC,
            SearchStrategy.HYBRID,
            SearchStrategy.HYBRID_RERANK,
        ):
            try:
                query_vector = await self.embedding_pipeline.embed_query(semantic_query)
                semantic_candidates = await self.semantic_retriever.search(
                    query_vector=query_vector,
                    filters=effective_filters,
                    limit=limit * 2,
                )
            except Exception as exc:
                logger.warning(
                    "Semantic vector retrieval failure (falling back to keyword): %s", exc
                )
                retrieval_errors.append(f"Semantic retrieval: {exc}")

        # 5. Candidate Fusion
        if strategy == SearchStrategy.KEYWORD or (not semantic_candidates and keyword_candidates):
            fused_candidates = keyword_candidates
        elif strategy == SearchStrategy.SEMANTIC or (
            not keyword_candidates and semantic_candidates
        ):
            fused_candidates = semantic_candidates
        else:
            fused_candidates = self.fusion_service.fuse(
                keyword_candidates=keyword_candidates,
                semantic_candidates=semantic_candidates,
                top_k=limit * 2,
            )

        # 6. Apply Hard Metadata Filters (deadlines passed, categories, degrees)
        valid_candidates = self.metadata_filter.apply_hard_filters(
            candidates=fused_candidates,
            filters=effective_filters,
        )

        # 7. Cross-Source Deduplication and Clustering
        deduped_candidates = self.identity_service.cluster_and_deduplicate(valid_candidates)

        # 8. Semantic Reranking
        if strategy == SearchStrategy.HYBRID_RERANK and deduped_candidates:
            try:
                reranked_candidates = await self.reranker.rerank(
                    query=clean_query,
                    candidates=deduped_candidates,
                    top_k=limit,
                )
            except Exception as exc:
                logger.warning("Reranking failure (falling back to fusion order): %s", exc)
                reranked_candidates = deduped_candidates[:limit]
        else:
            reranked_candidates = deduped_candidates[:limit]

        # 9. Freshness and Source Authority Trust Weighting
        weighted_candidates = self.freshness_scorer.score(reranked_candidates)

        # 10. Diversity Optimization (cap per provider)
        final_candidates = self.diversity_optimizer.optimize(weighted_candidates, limit=limit)

        latency = (time.monotonic() - start_time) * 1000.0

        return RetrievalResult(
            query=clean_query,
            normalized_query=semantic_query,
            expanded_queries=expanded_queries,
            strategy=strategy,
            candidates=final_candidates,
            total_candidates_found=len(final_candidates),
            latency_ms=round(latency, 2),
            metadata={
                "keyword_candidates_count": len(keyword_candidates),
                "semantic_candidates_count": len(semantic_candidates),
                "errors": retrieval_errors,
                "applied_filters": effective_filters.model_dump(exclude_none=True),
            },
        )
