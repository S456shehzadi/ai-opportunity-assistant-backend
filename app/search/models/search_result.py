import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class NormalizedSearchResult(BaseModel):
    """Normalized search result returned by any search provider adapter."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    title: str
    url: str  # Canonical normalized URL (stripped of tracking params, fragments, etc.)
    original_url: str
    snippet: str
    domain: str  # Clean domain (e.g. "daad.de", "fulbrightprogram.org")
    rank: int = 1
    provider: str
    query: str
    query_purpose: str = "general_search"
    published_at: str | None = None
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    relevance_score: float | None = None
    is_official_source_candidate: bool = False
    raw_metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    """Structured response returned by Search Agent and API endpoints."""

    search_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    original_query: str
    executed_queries: list[str] = Field(default_factory=list)
    results: list[NormalizedSearchResult] = Field(default_factory=list)
    total_results: int = 0
    provider_used: str = "mock"
    duration_ms: float = 0.0
    warnings: list[str] = Field(default_factory=list)
