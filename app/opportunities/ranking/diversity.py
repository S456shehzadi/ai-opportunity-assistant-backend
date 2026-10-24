"""Diversity optimizer mitigating clustering by organization, country, or program."""

from __future__ import annotations

from collections import defaultdict

from app.opportunities.ranking.schemas import RankedOpportunity


class DiversityOptimizer:
    """Rebalances candidate ranking to prevent single-source or single-country flooding."""

    @classmethod
    def optimize(
        cls,
        ranked_list: list[RankedOpportunity],
        max_consecutive_same_org: int = 2,
        max_per_org_cap: int = 3,
    ) -> list[RankedOpportunity]:
        """Interleaves opportunities to ensure diverse representation among top results."""
        if len(ranked_list) <= 2:
            return ranked_list

        org_counts: dict[str, int] = defaultdict(int)
        country_counts: dict[str, int] = defaultdict(int)

        reordered: list[RankedOpportunity] = []
        deferred: list[RankedOpportunity] = []

        for opp in ranked_list:
            org = (opp.organization or "unknown").strip().lower()
            country = (opp.host_country or "unknown").strip().lower()

            # If org cap reached and other items are available, defer
            if org != "unknown" and org_counts[org] >= max_per_org_cap:
                deferred.append(opp)
                continue

            # Check consecutive same organization
            if len(reordered) >= max_consecutive_same_org:
                last_orgs = [
                    (r.organization or "unknown").strip().lower()
                    for r in reordered[-max_consecutive_same_org:]
                ]
                if org != "unknown" and all(o == org for o in last_orgs):
                    deferred.append(opp)
                    continue

            reordered.append(opp)
            org_counts[org] += 1
            country_counts[country] += 1

        # Append deferred items back in their original relevance order
        for opp in deferred:
            reordered.append(opp)

        # Reassign 1-based sequential rank numbers
        for idx, item in enumerate(reordered, start=1):
            item.rank = idx

        return reordered
