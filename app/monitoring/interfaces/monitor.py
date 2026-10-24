"""Interfaces for monitoring providers, change detection, and scheduling."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any
from uuid import UUID

from app.monitoring.models.change_event import OpportunityChangeEvent
from app.monitoring.models.subscription import (
    OpportunitySubscription,
)


class ISourceMonitor(ABC):
    """Interface for retrieving remote opportunity sources and evaluating freshness."""

    @abstractmethod
    async def check_source_availability(
        self,
        url: str,
    ) -> tuple[bool, int, str | None]:
        """Verify if source URL is reachable. Returns (is_available, status_code, error)."""
        pass

    @abstractmethod
    async def fetch_latest_content(
        self,
        url: str,
    ) -> tuple[str | None, str | None, dict[str, Any]]:
        """Fetch raw HTML and cleaned text from remote source."""
        pass


class IChangeDetector(ABC):
    """Interface for comparing versions of an opportunity or page."""

    @abstractmethod
    def detect_content_changes(
        self,
        old_text: str,
        new_text: str,
    ) -> bool:
        """Determines if there is a substantive (non-trivial) text change."""
        pass

    @abstractmethod
    def detect_structured_changes(
        self,
        old_data: dict[str, Any],
        new_data: dict[str, Any],
        opportunity_id: UUID,
    ) -> list[OpportunityChangeEvent]:
        """Detect and construct typed change events between structured opportunity snapshots."""
        pass


class IMonitoringScheduler(ABC):
    """Interface for queuing and scheduling monitoring executions."""

    @abstractmethod
    async def schedule_opportunity_check(
        self,
        subscription_id: UUID,
        run_at: datetime | None = None,
    ) -> UUID:
        """Enqueues an opportunity check job."""
        pass

    @abstractmethod
    async def schedule_search_sweep(
        self,
        search_id: UUID,
        run_at: datetime | None = None,
    ) -> UUID:
        """Enqueues a search sweep job."""
        pass

    @abstractmethod
    async def schedule_deadline_sweep(
        self,
        run_at: datetime | None = None,
    ) -> UUID:
        """Enqueues a deadline reminder sweep job."""
        pass


class IOpportunityMonitoringEngine(ABC):
    """High-level interface orchestrating all monitoring operations."""

    @abstractmethod
    async def check_opportunity(
        self,
        subscription: OpportunitySubscription,
    ) -> list[OpportunityChangeEvent]:
        """Execute a single subscription's opportunity check."""
        pass

    @abstractmethod
    async def sweep_deadlines(self) -> int:
        """Evaluate upcoming deadlines across all active subscriptions."""
        pass

    @abstractmethod
    async def sweep_searches(self) -> int:
        """Re-run active monitored searches and detect new opportunities."""
        pass
