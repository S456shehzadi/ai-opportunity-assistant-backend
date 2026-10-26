"""API endpoints for advanced semantic opportunity discovery, vector retrieval, and indexing."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_reviewer_user, get_current_user, get_db
from app.discovery import get_discovery_engine, get_discovery_indexer
from app.discovery.evaluation.benchmark import get_default_retrieval_benchmark
from app.discovery.evaluation.evaluator import RetrievalEvaluator
from app.discovery.models import SearchStrategy
from app.models.user import User
from app.schemas.discovery import (
    DiscoveryExplainableCandidate,
    DiscoveryMetricsResponse,
    DiscoveryOpportunityCard,
    DiscoveryRetrieveResponse,
    DiscoverySearchRequest,
    DiscoverySearchResponse,
    DiscoveryStatusResponse,
)

router = APIRouter(prefix="/discovery", tags=["Discovery"])


@router.post(
    "/search",
    response_model=DiscoverySearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Search opportunities using advanced hybrid semantic retrieval",
)
async def discovery_search(
    request: DiscoverySearchRequest,
    current_user: User = Depends(get_current_user),
) -> DiscoverySearchResponse:
    """Executes multi-stage discovery combining keyword, vector semantic search,
    metadata filters, and reranking.
    """
    engine = get_discovery_engine()
    retrieval_res = await engine.search(
        query=request.query,
        filters=request.filters,
        strategy=request.strategy,
        limit=request.limit,
    )

    cards: list[DiscoveryOpportunityCard] = []
    for c in retrieval_res.candidates:
        doc = c.document
        fit_indicator = "High Match"
        if c.final_discovery_score >= 0.8:
            fit_indicator = "Top Match"
        elif c.final_discovery_score < 0.5:
            fit_indicator = "Potential Fit"

        cards.append(
            DiscoveryOpportunityCard(
                opportunity_id=c.opportunity_id,
                title=c.title,
                provider=c.provider,
                category=c.category,
                funding_summary=doc.funding_summary,
                deadline=doc.deadline.isoformat() if doc.deadline else None,
                status=doc.status,
                degree_levels=doc.degree_levels,
                fields=doc.fields,
                country=doc.countries[0] if doc.countries else "Global",
                source_url=c.canonical_source_url,
                source_type=doc.source_type,
                fit_indicator=fit_indicator,
                alternative_source_urls=c.cluster_source_urls,
            )
        )

    # Resilient relational database fallback
    if not cards and request.query.strip():
        try:
            from sqlalchemy import or_, select
            from app.core.database import async_session_factory
            from app.models.opportunity import Opportunity

            async with async_session_factory() as session:
                q_clean = request.query.strip()
                pattern = f"%{q_clean}%"
                stmt = (
                    select(Opportunity)
                    .where(
                        or_(
                            Opportunity.title.ilike(pattern),
                            Opportunity.organization.ilike(pattern),
                            Opportunity.description.ilike(pattern),
                            Opportunity.country.ilike(pattern),
                        )
                    )
                    .limit(request.limit)
                )
                res = await session.execute(stmt)
                sql_opps = res.scalars().all()
                for opp in sql_opps:
                    cards.append(
                        DiscoveryOpportunityCard(
                            opportunity_id=str(opp.id),
                            title=opp.title,
                            provider=opp.organization,
                            category=opp.category.value if hasattr(opp.category, "value") else str(opp.category),
                            funding_summary=opp.funding_amount or opp.funding_type,
                            deadline=opp.deadline.isoformat() if opp.deadline else None,
                            status=opp.status.value if hasattr(opp.status, "value") else str(opp.status),
                            degree_levels=opp.degree_levels or [],
                            fields=opp.fields or [],
                            country=opp.country,
                            source_url=opp.official_source_url,
                            source_type="Official Website",
                            fit_indicator="Top Match",
                            alternative_source_urls=[],
                        )
                    )
        except Exception:
            pass

    return DiscoverySearchResponse(
        query=retrieval_res.query,
        strategy=retrieval_res.strategy.value,
        total_found=len(cards),
        latency_ms=retrieval_res.latency_ms,
        results=cards,
        expanded_queries=retrieval_res.expanded_queries,
    )


@router.post(
    "/retrieve",
    response_model=DiscoveryRetrieveResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve raw candidates with diagnostic scores (Evaluation / Diagnostics)",
)
async def discovery_retrieve(
    request: DiscoverySearchRequest,
    current_user: User = Depends(get_current_reviewer_user),
) -> DiscoveryRetrieveResponse:
    """Diagnostics endpoint returning explainable candidate scores across pipeline stages."""
    engine = get_discovery_engine()
    res = await engine.search(
        query=request.query,
        filters=request.filters,
        strategy=request.strategy,
        limit=request.limit,
    )

    candidates: list[DiscoveryExplainableCandidate] = [
        DiscoveryExplainableCandidate(
            opportunity_id=c.opportunity_id,
            title=c.title,
            provider=c.provider,
            category=c.category,
            keyword_score=c.keyword_score,
            semantic_score=c.semantic_score,
            fusion_score=c.fusion_score,
            reranker_score=c.reranker_score,
            final_score=c.final_discovery_score,
            retrieval_sources=c.retrieval_sources,
            hard_filter_passed=c.hard_filter_passed,
            rejection_reason=c.filter_rejection_reason,
            canonical_url=c.canonical_source_url,
        )
        for c in res.candidates
    ]

    return DiscoveryRetrieveResponse(
        query=res.query,
        normalized_query=res.normalized_query,
        expanded_queries=res.expanded_queries,
        strategy=res.strategy.value,
        total_candidates=res.total_candidates_found,
        latency_ms=res.latency_ms,
        candidates=candidates,
        metadata=res.metadata,
    )


@router.post(
    "/reindex",
    status_code=status.HTTP_200_OK,
    summary="Trigger incremental or full reindexing of opportunities",
)
async def discovery_reindex(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_reviewer_user),
) -> dict[str, Any]:
    """Scans all opportunities in database and updates vector embeddings and search index."""
    indexer = get_discovery_indexer()
    stats = await indexer.reindex_all(db)
    return {"status": "success", "indexing_stats": stats}


@router.get(
    "/status",
    response_model=DiscoveryStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get operational status of discovery engine",
)
async def discovery_status() -> DiscoveryStatusResponse:
    """Returns vector store health, document index count, and active embedding version."""
    engine = get_discovery_engine()
    healthy = await engine.vector_store.health_check()

    return DiscoveryStatusResponse(
        status="healthy" if healthy else "degraded",
        vector_store_healthy=healthy,
        indexed_documents_count=len(engine._documents),
        embedding_version=engine.embedding_pipeline.version,
        embedding_dimension=engine.embedding_pipeline.dimension,
        supported_strategies=[s.value for s in SearchStrategy],
    )


@router.get(
    "/metrics",
    response_model=DiscoveryMetricsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get retrieval benchmark evaluation metrics",
)
async def discovery_metrics(
    current_user: User = Depends(get_current_reviewer_user),
) -> DiscoveryMetricsResponse:
    """Evaluates search quality across KEYWORD, SEMANTIC, and HYBRID strategies
    using benchmark queries.
    """
    engine = get_discovery_engine()
    evaluator = RetrievalEvaluator(engine=engine, k=5)
    benchmark_items = get_default_retrieval_benchmark()

    kw_report = await evaluator.evaluate_strategy(SearchStrategy.KEYWORD, benchmark_items)
    sem_report = await evaluator.evaluate_strategy(SearchStrategy.SEMANTIC, benchmark_items)
    hybrid_report = await evaluator.evaluate_strategy(SearchStrategy.HYBRID_RERANK, benchmark_items)

    metrics_map = {
        "KEYWORD": {
            "precision_at_k": kw_report.precision_at_k,
            "recall_at_k": kw_report.recall_at_k,
            "mrr": kw_report.mrr,
            "ndcg_at_k": kw_report.ndcg_at_k,
            "hit_rate": kw_report.hit_rate,
            "avg_latency_ms": kw_report.avg_latency_ms,
        },
        "SEMANTIC": {
            "precision_at_k": sem_report.precision_at_k,
            "recall_at_k": sem_report.recall_at_k,
            "mrr": sem_report.mrr,
            "ndcg_at_k": sem_report.ndcg_at_k,
            "hit_rate": sem_report.hit_rate,
            "avg_latency_ms": sem_report.avg_latency_ms,
        },
        "HYBRID_RERANK": {
            "precision_at_k": hybrid_report.precision_at_k,
            "recall_at_k": hybrid_report.recall_at_k,
            "mrr": hybrid_report.mrr,
            "ndcg_at_k": hybrid_report.ndcg_at_k,
            "hit_rate": hybrid_report.hit_rate,
            "avg_latency_ms": hybrid_report.avg_latency_ms,
        },
    }

    return DiscoveryMetricsResponse(
        evaluated_queries_count=len(benchmark_items),
        metrics_by_strategy=metrics_map,
    )
