"""Citation ranking, source hierarchy, and multi-source conflict reconciliation."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from app.ai.conversation.schemas import CitationItem, ClaimType


class CitationService:
    """Manages evidence citations enforcing authoritative source hierarchy and conflict warnings."""

    AUTHORITY_DOMAINS = {
        "daad.de": "OFFICIAL_PORTAL",
        "fulbrightprogram.org": "OFFICIAL_PORTAL",
        "erasmus-plus.ec.europa.eu": "OFFICIAL_PORTAL",
        "chevening.org": "OFFICIAL_PORTAL",
        "gatescambridge.org": "OFFICIAL_PORTAL",
        "rhodeshouse.ox.ac.uk": "OFFICIAL_PORTAL",
        "mext.go.jp": "OFFICIAL_PORTAL",
        "gov": "OFFICIAL_PORTAL",
        "europa.eu": "OFFICIAL_PORTAL",
    }

    @classmethod
    def classify_source(cls, url: str) -> tuple[str, str]:
        """Returns (source_type, trust_tier) for a given URL."""
        if not url:
            return "SECONDARY", "LOW"
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # Check official authority portals
        for auth, stype in cls.AUTHORITY_DOMAINS.items():
            if auth in domain:
                return stype, "HIGH"

        # Check academic / university domains
        if domain.endswith(".edu") or domain.endswith(".ac.uk") or "uni-" in domain:
            return "UNIVERSITY", "HIGH"

        # Check known educational/governmental TLDs
        if domain.endswith(".gov") or domain.endswith(".org"):
            return "OFFICIAL_PORTAL", "HIGH"

        return "SECONDARY", "MEDIUM"

    @classmethod
    def create_citation(
        cls,
        title: str,
        url: str,
        claim_types: list[ClaimType] | None = None,
        exact_snippet: str | None = None,
    ) -> CitationItem:
        """Constructs a validated CitationItem with authoritative trust classification."""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        source_type, trust_tier = cls.classify_source(url)

        return CitationItem(
            title=title,
            url=url,
            source_type=source_type,
            source_domain=domain,
            trust_tier=trust_tier,
            claim_types=claim_types or [],
            exact_snippet=exact_snippet,
        )

    @classmethod
    def reconcile_conflicts(
        cls,
        citations: list[CitationItem],
        field_name: str,
        official_value: Any,
        secondary_value: Any,
    ) -> tuple[Any, str | None]:
        """Resolves multi-source contradiction: official source wins; secondary conflict flagged."""
        if official_value == secondary_value or not secondary_value:
            return official_value, None

        warning = (
            f"Note: An alternative source reported {field_name} as '{secondary_value}', "
            f"but authoritative portal confirms '{official_value}'."
        )
        return official_value, warning

    @classmethod
    def rank_citations(cls, citations: list[CitationItem]) -> list[CitationItem]:
        """Orders citations prioritizing Official Portal > University > Secondary."""
        tier_weights = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        type_weights = {
            "OFFICIAL_PORTAL": 4,
            "UNIVERSITY": 3,
            "DIRECTORY": 2,
            "SECONDARY": 1,
        }

        return sorted(
            citations,
            key=lambda c: (
                tier_weights.get(c.trust_tier, 0),
                type_weights.get(c.source_type, 0),
            ),
            reverse=True,
        )
