from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class SearchFilter(BaseModel):
    country: str | None = None
    category: str | None = None
    site_whitelist: list[str] = Field(default_factory=list)
    after_date: str | None = None


class SearchQuery(BaseModel):
    query_text: str
    limit: int = 10
    filters: SearchFilter = Field(default_factory=SearchFilter)


class SearchResultItem(BaseModel):
    title: str
    url: str
    snippet: str
    domain: str
    rank: int = 1
    published_date: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResults(BaseModel):
    query: SearchQuery
    provider: str
    items: list[SearchResultItem] = Field(default_factory=list)
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    total_results: int = 0
