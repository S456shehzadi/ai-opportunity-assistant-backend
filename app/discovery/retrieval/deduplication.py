"""Opportunity identity service for cross-source deduplication and clustering."""

from __future__ import annotations

import re

from app.discovery.models import OpportunityCandidate


def _clean_str(text: str) -> str:
    return re.sub(r"[^\w\s]", "", text.lower()).strip()


class OpportunityIdentityService:
    """Detects and clusters cross-source duplicates while preserving canonical citations."""

    def cluster_and_deduplicate(
        self,
        candidates: list[OpportunityCandidate],
    ) -> list[OpportunityCandidate]:
        if not candidates:
            return []

        clusters: list[OpportunityCandidate] = []
        # Key: (normalized_title, normalized_provider)
        seen_identities: dict[tuple[str, str], OpportunityCandidate] = {}
        # Key: canonical URL
        seen_urls: dict[str, OpportunityCandidate] = {}

        for c in candidates:
            title_norm = _clean_str(c.title)
            provider_norm = _clean_str(c.provider)
            identity_key = (title_norm, provider_norm)
            url_key = c.document.source_url.strip().lower() if c.document.source_url else None

            existing_cluster: OpportunityCandidate | None = None

            if identity_key in seen_identities:
                existing_cluster = seen_identities[identity_key]
            elif url_key and url_key in seen_urls:
                existing_cluster = seen_urls[url_key]

            if existing_cluster:
                # Merge into existing cluster
                # Preserve candidate with higher source trust or score
                if (
                    c.canonical_source_url
                    and c.canonical_source_url not in existing_cluster.cluster_source_urls
                ):
                    existing_cluster.cluster_source_urls.append(c.canonical_source_url)

                for src in c.retrieval_sources:
                    if src not in existing_cluster.retrieval_sources:
                        existing_cluster.retrieval_sources.append(src)

                # If new source is official and existing was aggregator, upgrade canonical URL
                if (
                    "official" in (c.document.source_type or "").lower()
                    and "official" not in (existing_cluster.document.source_type or "").lower()
                ):
                    existing_cluster.canonical_source_url = c.canonical_source_url
                    existing_cluster.document.source_type = c.document.source_type
                    existing_cluster.document.source_quality_score = c.document.source_quality_score
            else:
                seen_identities[identity_key] = c
                if url_key:
                    seen_urls[url_key] = c
                clusters.append(c)

        return clusters
