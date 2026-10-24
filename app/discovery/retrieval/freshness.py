"""Freshness and source trust weighting service."""

from __future__ import annotations

from datetime import UTC, date, datetime

from app.discovery.models import OpportunityCandidate


class FreshnessAndTrustScorer:
    """Calculates freshness decay and source authority trust factors."""

    def score(self, candidates: list[OpportunityCandidate]) -> list[OpportunityCandidate]:
        now = datetime.now(UTC)
        today = date.today()

        for c in candidates:
            doc = c.document

            # 1. Source Trust
            # Official sources (universities, governments) receive full weight 1.0;
            # directories get lower weight
            s_type = (doc.source_type or "").lower()
            if any(term in s_type for term in ["official", "university", "government"]):
                trust_weight = 1.0
            elif "news" in s_type or "organization" in s_type:
                trust_weight = 0.85
            elif "aggregator" in s_type or "directory" in s_type:
                trust_weight = 0.70
            else:
                trust_weight = 0.80

            c.trust_weight = trust_weight

            # 2. Freshness Score
            freshness_weight = 1.0
            if doc.verified_at:
                # Calculate age in days
                v_date = doc.verified_at
                if v_date.tzinfo is None:
                    v_date = v_date.replace(tzinfo=UTC)
                age_days = max(0, (now - v_date).days)
                # Exponential decay: half-life of 90 days
                freshness_weight = max(0.6, 1.0 - (age_days / 180.0))

            # Upcoming deadlines with active status receive a modest urgency boost
            if doc.deadline and doc.deadline >= today:
                days_until_deadline = (doc.deadline - today).days
                if days_until_deadline <= 60:
                    freshness_weight = min(1.1, freshness_weight * 1.05)

            c.freshness_weight = round(freshness_weight, 4)

            # Modulate final score by trust and freshness factors
            c.final_discovery_score = round(
                c.final_discovery_score * c.trust_weight * c.freshness_weight,
                4,
            )

        candidates.sort(key=lambda x: x.final_discovery_score, reverse=True)
        return candidates
