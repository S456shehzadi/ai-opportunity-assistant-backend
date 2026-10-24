"""Freshness calculator evaluating source update recency and verification age."""

from __future__ import annotations

from datetime import UTC, date, datetime

from pydantic import BaseModel, Field


class FreshnessEvaluation(BaseModel):
    """Detailed freshness assessment for an opportunity."""

    score: float = Field(ge=0.0, le=1.0)
    age_days: int
    is_fresh: bool
    is_stale: bool
    summary: str


class FreshnessCalculator:
    """Evaluates time elapsed since last verification and source publication."""

    @classmethod
    def calculate(
        cls,
        last_verified_at: datetime | date | None,
        source_published_at: datetime | date | None = None,
        is_explicitly_stale: bool = False,
        now: datetime | None = None,
    ) -> FreshnessEvaluation:
        """Computes a normalized freshness score [0.0, 1.0] with exponential-style step decay."""
        if is_explicitly_stale:
            return FreshnessEvaluation(
                score=0.20,
                age_days=365,
                is_fresh=False,
                is_stale=True,
                summary="Information has been identified as potentially stale.",
            )

        current_time = now or datetime.now(UTC)
        eval_dt = last_verified_at or source_published_at

        if eval_dt is None:
            # Unknown verification date
            return FreshnessEvaluation(
                score=0.50,
                age_days=-1,
                is_fresh=False,
                is_stale=False,
                summary="Verification date unknown; treated neutrally.",
            )

        if isinstance(eval_dt, date) and not isinstance(eval_dt, datetime):
            eval_dt = datetime(eval_dt.year, eval_dt.month, eval_dt.day, tzinfo=UTC)
        elif eval_dt.tzinfo is None:
            eval_dt = eval_dt.replace(tzinfo=UTC)

        delta = current_time - eval_dt
        days = max(0, delta.days)

        if days <= 7:
            score = 1.0
            summary = "Verified within the past week (Very fresh)"
        elif days <= 30:
            score = 0.95
            summary = "Verified within the past month (Fresh)"
        elif days <= 60:
            score = 0.85
            summary = f"Verified {days} days ago"
        elif days <= 90:
            score = 0.75
            summary = f"Verified {days} days ago (Moderate age)"
        elif days <= 180:
            score = 0.55
            summary = f"Verified {days} days ago (Older listing)"
        else:
            score = 0.35
            summary = f"Verified over {days} days ago (Potentially outdated)"

        return FreshnessEvaluation(
            score=score,
            age_days=days,
            is_fresh=days <= 30,
            is_stale=days > 180,
            summary=summary,
        )
