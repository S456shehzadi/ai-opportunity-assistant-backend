"""Pydantic schemas for discovery API requests and responses."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.discovery.models import RetrievalFilters, SearchStrategy


class DiscoverySearchRequest(BaseModel):
    """Payload for user-facing opportunity discovery search."""

    query: str = Field(min_length=1, max_length=500)
    filters: RetrievalFilters | None = None
    strategy: SearchStrategy = SearchStrategy.HYBRID_RERANK
    limit: int = Field(default=20, ge=1, le=100)


class DiscoveryOpportunityCard(BaseModel):
    """Clean, user-facing representation of an opportunity discovery result."""

    opportunity_id: str
    title: str
    provider: str
    category: str
    funding_summary: str
    deadline: str | None = None
    status: str
    degree_levels: list[str] = Field(default_factory=list)
    fields: list[str] = Field(default_factory=list)
    country: str = "Global"
    source_url: str | None = None
    source_type: str = "Official Website"
    fit_indicator: str = "High Match"
    alternative_source_urls: list[str] = Field(default_factory=list)


class DiscoverySearchResponse(BaseModel):
    """Clean response for user-facing discovery search."""

    query: str
    strategy: str
    total_found: int
    latency_ms: float
    results: list[DiscoveryOpportunityCard]
    expanded_queries: list[str] = Field(default_factory=list)


class DiscoveryExplainableCandidate(BaseModel):
    """Detailed candidate record for diagnostic and evaluation inspection."""

    opportunity_id: str
    title: str
    provider: str
    category: str
    keyword_score: float
    semantic_score: float
    fusion_score: float
    reranker_score: float
    final_score: float
    retrieval_sources: list[str]
    hard_filter_passed: bool
    rejection_reason: str | None = None
    canonical_url: str | None = None


class DiscoveryRetrieveResponse(BaseModel):
    """Diagnostics response exposing internal candidate scores."""

    query: str
    normalized_query: str
    expanded_queries: list[str]
    strategy: str
    total_candidates: int
    latency_ms: float
    candidates: list[DiscoveryExplainableCandidate]
    metadata: dict[str, Any] = Field(default_factory=dict)


class DiscoveryStatusResponse(BaseModel):
    """Operational health and capacity status of the discovery engine."""

    status: str
    vector_store_healthy: bool
    indexed_documents_count: int
    embedding_version: str
    embedding_dimension: int
    supported_strategies: list[str]


class DiscoveryMetricsResponse(BaseModel):
    """Benchmark evaluation metrics report."""

    evaluated_queries_count: int
    metrics_by_strategy: dict[str, dict[str, float]]
