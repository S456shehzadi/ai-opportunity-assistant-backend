"""Resource and cost tracker enforcing strict budget caps for external AI and search APIs."""

from __future__ import annotations

import logging
import threading
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class CostOperation(StrEnum):
    """Categories of cost-incurring operations."""

    SEARCH_QUERY = "search_query"
    WEB_PAGE_CRAWL = "web_page_crawl"
    LLM_INFERENCE = "llm_inference"
    EMBEDDING_GEN = "embedding_generation"
    RERANKING = "reranking"


# Unit costs in USD for estimation
UNIT_COSTS_USD: dict[CostOperation, float] = {
    CostOperation.SEARCH_QUERY: 0.01,
    CostOperation.WEB_PAGE_CRAWL: 0.002,
    CostOperation.LLM_INFERENCE: 0.003,
    CostOperation.EMBEDDING_GEN: 0.0002,
    CostOperation.RERANKING: 0.0015,
}


class CostBudgetExceededError(Exception):
    """Raised when an operation would exceed daily budget thresholds."""

    pass


class CostSummary(BaseModel):
    """Summary of daily consumption and budget status."""

    date: str
    total_spend_usd: float = Field(ge=0.0)
    ai_spend_usd: float = Field(ge=0.0)
    search_spend_usd: float = Field(ge=0.0)
    ai_budget_limit_usd: float = Field(ge=0.0)
    search_budget_limit_usd: float = Field(ge=0.0)
    is_ai_budget_exceeded: bool
    is_search_budget_exceeded: bool
    operation_counts: dict[str, int]


class CostTracker:
    """Thread-safe budget and telemetry tracker for staging/beta cost containment."""

    _instance: CostTracker | None = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._current_date: str = datetime.now(UTC).strftime("%Y-%m-%d")
        self._operation_counts: dict[CostOperation, int] = dict.fromkeys(CostOperation, 0)
        self._ai_spend_usd: float = 0.0
        self._search_spend_usd: float = 0.0

    @classmethod
    def get_instance(cls) -> CostTracker:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = CostTracker()
        return cls._instance

    def _rollover_day_if_needed(self) -> None:
        now_date = datetime.now(UTC).strftime("%Y-%m-%d")
        if now_date != self._current_date:
            self._current_date = now_date
            self._operation_counts = dict.fromkeys(CostOperation, 0)
            self._ai_spend_usd = 0.0
            self._search_spend_usd = 0.0

    def can_execute_ai_operation(self) -> bool:
        """Checks if current daily AI spend is below configured threshold."""
        with self._lock:
            self._rollover_day_if_needed()
            settings = get_settings()
            return self._ai_spend_usd < settings.AI_BUDGET_DAILY_LIMIT_USD

    def can_execute_search_operation(self) -> bool:
        """Checks if current daily search spend is below configured threshold."""
        with self._lock:
            self._rollover_day_if_needed()
            settings = get_settings()
            return self._search_spend_usd < settings.SEARCH_BUDGET_DAILY_LIMIT_USD

    def record_operation(
        self,
        operation: CostOperation,
        units: int = 1,
        cost_override: float | None = None,
    ) -> float:
        """Records an operation, increments counters, and checks budget bounds."""
        with self._lock:
            self._rollover_day_if_needed()
            cost_per_unit = (
                cost_override if cost_override is not None else UNIT_COSTS_USD.get(operation, 0.001)
            )
            op_cost = cost_per_unit * units

            self._operation_counts[operation] = self._operation_counts.get(operation, 0) + units

            if operation in (
                CostOperation.LLM_INFERENCE,
                CostOperation.EMBEDDING_GEN,
                CostOperation.RERANKING,
            ):
                self._ai_spend_usd += op_cost
            else:
                self._search_spend_usd += op_cost

            return round(op_cost, 6)

    def get_summary(self) -> CostSummary:
        """Returns consolidated daily spending summary."""
        with self._lock:
            self._rollover_day_if_needed()
            settings = get_settings()
            ai_limit = settings.AI_BUDGET_DAILY_LIMIT_USD
            search_limit = settings.SEARCH_BUDGET_DAILY_LIMIT_USD

            return CostSummary(
                date=self._current_date,
                total_spend_usd=round(self._ai_spend_usd + self._search_spend_usd, 4),
                ai_spend_usd=round(self._ai_spend_usd, 4),
                search_spend_usd=round(self._search_spend_usd, 4),
                ai_budget_limit_usd=ai_limit,
                search_budget_limit_usd=search_limit,
                is_ai_budget_exceeded=self._ai_spend_usd >= ai_limit,
                is_search_budget_exceeded=self._search_spend_usd >= search_limit,
                operation_counts={k.value: v for k, v in self._operation_counts.items()},
            )

    def reset_for_testing(self) -> None:
        """Testing utility to clear current accumulators."""
        with self._lock:
            self._current_date = datetime.now(UTC).strftime("%Y-%m-%d")
            self._operation_counts = dict.fromkeys(CostOperation, 0)
            self._ai_spend_usd = 0.0
            self._search_spend_usd = 0.0


def get_cost_tracker() -> CostTracker:
    return CostTracker.get_instance()
