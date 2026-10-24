"""Canonical deduplication of candidates before ranking."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from app.opportunities.extraction.normalization import OrganizationNormalizer
from app.opportunities.ranking.factors import (
    get_opp_category,
    get_opp_org,
    get_opp_title,
    get_opp_trust_score,
)


class CandidateDeduplicator:
    """Consolidates identical opportunities discovered via multiple URLs, queries, or pages."""

    @classmethod
    def get_candidate_key(cls, opp: Any) -> str:
        """Determines canonical identity key for any opportunity candidate."""
        existing_key = getattr(opp, "canonical_key", None)
        if existing_key:
            return str(existing_key)

        title = get_opp_title(opp)
        org = get_opp_org(opp)
        cat = get_opp_category(opp)

        norm_org = OrganizationNormalizer.normalize(org).canonical_name.lower().strip()
        clean_title = re.sub(r"[^\w\s]", " ", title.lower()).strip()
        clean_title = re.sub(r"\s+", " ", clean_title)
        norm_cat = (cat or "other").lower().strip()

        seed = f"{norm_org}::{clean_title}::{norm_cat}"
        digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]
        return f"opp_{digest}"

    @classmethod
    def deduplicate(cls, opportunities: list[Any]) -> list[Any]:
        """Deduplicates candidates, keeping the one with higher trust score."""
        seen: dict[str, Any] = {}

        for opp in opportunities:
            key = cls.get_candidate_key(opp)
            if key not in seen:
                seen[key] = opp
            else:
                # Retain the candidate with higher trust score
                existing = seen[key]
                if get_opp_trust_score(opp) > get_opp_trust_score(existing):
                    seen[key] = opp

        return list(seen.values())
