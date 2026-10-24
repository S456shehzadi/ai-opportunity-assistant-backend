"""Evidence selection mapping claims to verbatim source snippets and verified URLs."""

from __future__ import annotations

from typing import Any

from app.ai.conversation.citations import CitationService
from app.ai.conversation.schemas import CitationItem, ClaimType


class EvidenceSelector:
    """Selects and binds verifiable evidence to factual claims."""

    @classmethod
    def select_evidence_for_opportunity(
        cls,
        opportunity: Any,
        requested_fields: list[str] | None = None,
    ) -> list[CitationItem]:
        """Extracts grounded citations with exact snippets from an opportunity record."""
        citations: list[CitationItem] = []
        title = cls._get_val(opportunity, "title", "Opportunity")
        official_url = str(
            cls._get_val(opportunity, "official_source_url", "")
            or cls._get_val(opportunity, "source_url", "")
            or cls._get_val(opportunity, "application_url", "")
        )

        if not official_url:
            return []

        # Claim types supported by this opportunity record
        claim_types = [ClaimType.TITLE, ClaimType.ORGANIZATION]
        funding = cls._get_val(opportunity, "funding_type", None)
        if funding:
            claim_types.append(ClaimType.FUNDING)
        deadline = cls._get_val(opportunity, "deadline", None)
        if deadline:
            claim_types.append(ClaimType.DEADLINE)
        elig = cls._get_val(opportunity, "eligibility", None)
        if elig:
            claim_types.append(ClaimType.REQUIREMENT)

        # Snippet from description or summary
        desc = str(cls._get_val(opportunity, "description", ""))
        snippet = desc[:200] + "..." if len(desc) > 200 else desc

        citation = CitationService.create_citation(
            title=f"{title} - Official Details",
            url=official_url,
            claim_types=claim_types,
            exact_snippet=snippet if snippet else None,
        )
        citations.append(citation)

        # Include additional evidence sources if available in metadata or evidence links
        extra_sources = cls._get_val(opportunity, "evidence_sources", []) or cls._get_val(
            opportunity, "sources", []
        )
        for src in extra_sources:
            if isinstance(src, dict):
                src_url = src.get("url") or src.get("source_url")
                src_title = src.get("title", f"{title} Source")
                src_snip = src.get("snippet") or src.get("text")
                if src_url and src_url != official_url:
                    citations.append(
                        CitationService.create_citation(
                            title=src_title,
                            url=src_url,
                            claim_types=[ClaimType.REQUIREMENT],
                            exact_snippet=src_snip,
                        )
                    )

        return CitationService.rank_citations(citations)

    @classmethod
    def _get_val(cls, obj: Any, key: str, default: Any = None) -> Any:
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)
