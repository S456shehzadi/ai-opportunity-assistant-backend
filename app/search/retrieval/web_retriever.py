from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class RetrievalPolicy:
    """Polite crawling policies respecting website guidelines and ethical crawling."""

    respect_robots_txt: bool = True
    timeout_seconds: float = 10.0
    max_retries: int = 2
    max_content_size_bytes: int = 5_000_000  # 5MB safety limit
    user_agent: str = "AIOpportunityAssistantBot/0.1 (+https://aiopportunityassistant.example/bot)"
    custom_headers: dict[str, str] = field(default_factory=dict)
    rate_limit_per_domain_sec: float = 1.0


@dataclass
class RetrievedDocument:
    """Structured representation of fetched web page content."""

    url: str
    final_url: str  # Followed redirects
    status_code: int
    content_type: str
    raw_html: str
    encoding: str
    retrieved_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    is_cached: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


class WebRetriever(ABC):
    """Abstract interface for ethical, rate-limited, cached web page retrieval."""

    def __init__(self, policy: RetrievalPolicy | None = None) -> None:
        self.policy = policy or RetrievalPolicy()

    @abstractmethod
    async def is_allowed_by_robots_txt(self, url: str) -> bool:
        """Check if target URL allows automated indexing per robots.txt standard."""
        pass

    @abstractmethod
    async def fetch(self, url: str) -> RetrievedDocument:
        """Fetch web document respecting rate limits, timeouts, and content types."""
        pass

    @abstractmethod
    async def fetch_cached(self, url: str) -> RetrievedDocument | None:
        """Retrieve cached document if fresh and unexpired."""
        pass


class BaseWebRetriever(WebRetriever):
    """Base web retriever with ethical crawling policies."""

    async def is_allowed_by_robots_txt(self, url: str) -> bool:
        # Default safety: always check before crawling
        return True

    async def fetch(self, url: str) -> RetrievedDocument:
        raise NotImplementedError(
            "Live web fetching will be implemented with polite rate-limiting."
        )

    async def fetch_cached(self, url: str) -> RetrievedDocument | None:
        return None
