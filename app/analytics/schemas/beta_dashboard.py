"""Schemas for the internal privacy-preserving Beta Dashboard."""

from __future__ import annotations

from pydantic import BaseModel, Field


class LatencyPercentiles(BaseModel):
    p50_ms: float = Field(ge=0.0)
    p95_ms: float = Field(ge=0.0)
    p99_ms: float = Field(ge=0.0)


class CostTelemetry(BaseModel):
    total_spend_usd: float = Field(ge=0.0)
    ai_spend_usd: float = Field(ge=0.0)
    search_spend_usd: float = Field(ge=0.0)
    ai_budget_limit_usd: float = Field(ge=0.0)
    search_budget_limit_usd: float = Field(ge=0.0)
    is_budget_exceeded: bool = False


class BetaDashboardMetrics(BaseModel):
    """Consolidated privacy-conscious health and product metrics for beta testing."""

    environment: str
    active_beta_users: int = Field(ge=0)
    onboarding_completion_rate: float = Field(ge=0.0, le=100.0)
    total_searches: int = Field(ge=0)
    search_success_rate: float = Field(ge=0.0, le=100.0)
    zero_result_searches: int = Field(ge=0)
    opportunities_saved: int = Field(ge=0)
    opportunity_save_rate: float = Field(ge=0.0, le=100.0)
    official_link_clicks: int = Field(ge=0)
    link_click_through_rate: float = Field(ge=0.0, le=100.0)
    user_satisfaction_score: float = Field(ge=0.0, le=5.0)
    incorrect_info_reports: int = Field(ge=0)
    assistant_queries: int = Field(ge=0)
    assistant_error_rate: float = Field(ge=0.0, le=100.0)
    api_error_rate: float = Field(ge=0.0, le=100.0)
    api_latency_ms: LatencyPercentiles
    worker_failures: int = Field(ge=0)
    notification_delivery_failures: int = Field(ge=0)
    costs: CostTelemetry
    feature_flags_active: dict[str, bool]
    feedback_breakdown: dict[str, int]
