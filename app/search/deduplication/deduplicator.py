import logging
from collections import defaultdict

from app.search.models.search_result import NormalizedSearchResult
from app.search.normalization.url_normalizer import UrlNormalizer

logger = logging.getLogger(__name__)


class SearchResultDeduplicator:
    """Deduplicates search results by canonical URL and limits domain dominance."""

    @classmethod
    def deduplicate(
        cls,
        results: list[NormalizedSearchResult],
        max_per_domain: int = 3,
        max_total: int = 30,
    ) -> list[NormalizedSearchResult]:
        """Deduplicates by canonical URL and diversifies domain distribution."""
        seen_urls: set[str] = set()
        domain_counts: dict[str, int] = defaultdict(int)
        deduped: list[NormalizedSearchResult] = []
        excess_domain_items: list[NormalizedSearchResult] = []

        for item in results:
            canonical_url = UrlNormalizer.normalize_url(item.url)
            if canonical_url in seen_urls:
                continue

            seen_urls.add(canonical_url)
            domain = item.domain or UrlNormalizer.extract_domain(canonical_url)

            if domain_counts[domain] < max_per_domain:
                domain_counts[domain] += 1
                deduped.append(item)
            else:
                # Buffer for potential filling if max_total is not met
                excess_domain_items.append(item)

            if len(deduped) >= max_total:
                break

        # If after diversification we have room under max_total, fill up with overflow
        if len(deduped) < max_total and excess_domain_items:
            for item in excess_domain_items:
                deduped.append(item)
                if len(deduped) >= max_total:
                    break

        return deduped[:max_total]
