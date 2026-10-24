"""Domain and data models for advanced opportunity discovery, vector retrieval, and search."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class SearchStrategy(StrEnum):
    KEYWORD = "KEYWORD"
    SEMANTIC = "SEMANTIC"
    HYBRID = "HYBRID"
    HYBRID_RERANK = "HYBRID_RERANK"


class FusionMethod(StrEnum):
    RRF = "RRF"  # Reciprocal Rank Fusion
    WEIGHTED = "WEIGHTED"  # Linear weighted score fusion


class EmbeddingType(StrEnum):
    FULL = "FULL"
    SUMMARY = "SUMMARY"
    ELIGIBILITY = "ELIGIBILITY"
    FUNDING = "FUNDING"


@dataclass
class VectorSearchResult:
    """Represents a matched vector search hit."""

    document_id: str
    score: float  # Cosine similarity score [-1.0, 1.0] or normalized [0.0, 1.0]
    metadata: dict[str, Any] = field(default_factory=dict)
    vector: list[float] | None = None


class RetrievalFilters(BaseModel):
    """Structured filters separating hard constraints from soft ranking signals."""

    category: str | None = None
    degree_levels: list[str] = Field(default_factory=list)
    countries: list[str] = Field(default_factory=list)
    eligible_nationalities: list[str] = Field(default_factory=list)
    fields: list[str] = Field(default_factory=list)
    funding_type: str | None = None
    fully_funded_only: bool = False
    no_application_fee: bool = False
    no_ielts_required: bool = False
    min_funding_amount: float | None = None
    status: str | None = "active"
    exclude_expired: bool = True
    current_date: date | None = None
    languages: list[str] = Field(default_factory=list)
    organization: str | None = None


class OpportunitySearchDocument(BaseModel):
    """Canonical, cleaned searchable representation of an opportunity."""

    opportunity_id: str
    title: str
    provider: str
    category: str
    description: str
    fields: list[str] = Field(default_factory=list)
    degree_levels: list[str] = Field(default_factory=list)
    funding_summary: str = "Unknown"
    funding_amount: str | None = None
    currency: str | None = None
    eligibility_summary: str = ""
    countries: list[str] = Field(default_factory=list)
    nationalities: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    tests_required: list[str] = Field(default_factory=list)
    application_fee_required: bool = False
    deadline: date | None = None
    status: str = "active"
    source_quality_score: float = 1.0  # 1.0 official, 0.7 secondary, 0.4 directory
    source_type: str = "Official Website"
    source_url: str | None = None
    verified_at: datetime | None = None
    freshness_score: float = 1.0
    searchable_text: str = ""
    content_hash: str = ""
    embedding_version: str = "v1.0.0"


class OpportunityCandidate(BaseModel):
    """A retrieved opportunity candidate passing multi-stage discovery."""

    opportunity_id: str
    title: str
    provider: str
    category: str
    document: OpportunitySearchDocument
    keyword_score: float = 0.0
    semantic_score: float = 0.0
    fusion_score: float = 0.0
    reranker_score: float = 0.0
    final_discovery_score: float = 0.0
    retrieval_sources: list[str] = Field(default_factory=list)
    hard_filter_passed: bool = True
    filter_rejection_reason: str | None = None
    cluster_source_urls: list[str] = Field(default_factory=list)
    canonical_source_url: str | None = None
    freshness_weight: float = 1.0
    trust_weight: float = 1.0


class RetrievalResult(BaseModel):
    """Final output of the multi-stage retrieval pipeline."""

    query: str
    normalized_query: str
    expanded_queries: list[str] = Field(default_factory=list)
    strategy: SearchStrategy
    candidates: list[OpportunityCandidate] = Field(default_factory=list)
    total_candidates_found: int = 0
    latency_ms: float = 0.0
    cached: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
