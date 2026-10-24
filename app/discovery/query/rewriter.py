"""Semantic query rewriter extracting structured intent signals without fabricating constraints."""

from __future__ import annotations

import re

from app.discovery.models import RetrievalFilters


class SemanticQueryRewriter:
    """Normalizes natural queries into clean semantic text and structured filter hints."""

    def rewrite_and_extract_filters(
        self,
        query: str,
        base_filters: RetrievalFilters | None = None,
    ) -> tuple[str, RetrievalFilters]:
        filters = base_filters.model_copy() if base_filters else RetrievalFilters()
        cleaned = query.strip()
        lowered = cleaned.lower()

        # 1. Degree level hint detection
        if any(term in lowered for term in ["master's", "masters", "msc", "postgraduate"]):
            if "Master" not in filters.degree_levels and "Master's" not in filters.degree_levels:
                filters.degree_levels.append("Master's")

        if any(term in lowered for term in ["phd", "doctoral", "doctorate"]):
            if "PhD" not in filters.degree_levels and "Doctorate" not in filters.degree_levels:
                filters.degree_levels.append("PhD")

        if any(term in lowered for term in ["bachelor", "bachelors", "undergraduate", "bsc"]):
            if (
                "Bachelor" not in filters.degree_levels
                and "Bachelor's" not in filters.degree_levels
            ):
                filters.degree_levels.append("Bachelor's")

        # 2. Funding type hint detection
        if "fully funded" in lowered or "full funding" in lowered or "100% scholarship" in lowered:
            filters.fully_funded_only = True

        # 3. IELTS / Language test hint detection
        if "no ielts" in lowered or "without ielts" in lowered or "ielts not required" in lowered:
            filters.no_ielts_required = True

        # 4. Application fee hint detection
        if "no application fee" in lowered or "free application" in lowered or "no fee" in lowered:
            filters.no_application_fee = True

        # 5. Opportunity category hint detection
        if "internship" in lowered or "placement" in lowered:
            if not filters.category:
                filters.category = "Internship"
        elif "scholarship" in lowered or "fellowship" in lowered:
            if not filters.category:
                filters.category = "Scholarship"
        elif "grant" in lowered or "research funding" in lowered:
            if not filters.category:
                filters.category = "Grant"

        # 6. Normalize search text
        # Remove noisy conversational filler words while preserving key entities
        semantic_query = re.sub(
            r"\b(i am looking for|find me|show me|can you give me|list all|please find)\b",
            "",
            cleaned,
            flags=re.IGNORECASE,
        ).strip()

        if not semantic_query:
            semantic_query = cleaned

        return semantic_query, filters
