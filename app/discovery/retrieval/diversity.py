"""Diversity optimizer balancing relevance with provider and geographic variety."""

from __future__ import annotations

from app.discovery.models import OpportunityCandidate


class DiversityOptimizer:
    """Prevents result monopolization by a single provider or region without hurting relevance."""

    def __init__(self, max_per_provider: int = 3) -> None:
        self.max_per_provider = max_per_provider

    def optimize(
        self,
        candidates: list[OpportunityCandidate],
        limit: int = 50,
    ) -> list[OpportunityCandidate]:
        if len(candidates) <= limit:
            return candidates

        selected: list[OpportunityCandidate] = []
        overflow: list[OpportunityCandidate] = []
        provider_counts: dict[str, int] = {}

        # 1. Primary pass respecting diversity cap
        for c in candidates:
            provider = (c.provider or "Unknown").strip().lower()
            count = provider_counts.get(provider, 0)

            if count < self.max_per_provider:
                selected.append(c)
                provider_counts[provider] = count + 1
            else:
                overflow.append(c)

            if len(selected) >= limit:
                break

        # 2. If limit not reached, backfill from overflow by relevance
        if len(selected) < limit and overflow:
            remaining_slots = limit - len(selected)
            selected.extend(overflow[:remaining_slots])

        return selected
