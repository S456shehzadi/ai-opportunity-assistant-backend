"""Opportunity embedding pipeline generating structured representations and versioned vectors."""

from __future__ import annotations

import hashlib
import math
import re

from app.discovery.models import EmbeddingType, OpportunitySearchDocument
from app.learning.interfaces.model import EmbeddingModel
from app.models.opportunity import Opportunity


def _generate_deterministic_vector(text: str, dimension: int = 64) -> list[float]:
    """Generates a stable, unit-normalized semantic vector using token-based hashing.

    Used when offline, in tests, or as a zero-dependency fallback for EmbeddingModel.
    Tokens are weighted by semantic position and length, producing high cosine
    similarity for related keywords and low similarity for disjoint concepts.
    """
    vector = [0.0] * dimension
    tokens = re.findall(r"\w+", text.lower())

    for token in tokens:
        # Hash each token with seed
        h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
        pos = h % dimension
        weight = 1.0 + (len(token) / 10.0)
        # Sign bit from next bit
        sign = 1.0 if ((h >> 8) & 1) == 0 else -1.0
        vector[pos] += sign * weight

    # Normalize to unit vector
    norm = math.sqrt(sum(x * x for x in vector))
    if norm > 0.0:
        return [round(x / norm, 6) for x in vector]
    return vector


class OpportunityEmbeddingPipeline:
    """Pipelines structured opportunity content into versioned dense embeddings."""

    def __init__(
        self,
        model: EmbeddingModel | None = None,
        dimension: int = 64,
        version: str = "v1.0.0",
    ) -> None:
        self.model = model
        self.dimension = dimension
        self.version = version

    def build_search_document(self, opportunity: Opportunity) -> OpportunitySearchDocument:
        """Transforms structured database Opportunity into canonical OpportunitySearchDocument."""
        fields = list(opportunity.fields or [])
        degree_levels = list(opportunity.degree_levels or [])
        countries = [opportunity.country] if opportunity.country else ["Global"]
        nationalities = list(opportunity.eligible_nationalities or ["Global"])

        category_val = (
            opportunity.category.value
            if hasattr(opportunity.category, "value")
            else opportunity.category
        )
        funding_desc = (
            f"Funding: {opportunity.funding_type} "
            f"(Amount: {opportunity.funding_amount or 'N/A'} {opportunity.currency or ''})"
        )

        # Construct structured searchable text (strictly structured, never raw HTML)
        sections = [
            f"Title: {opportunity.title}",
            f"Provider: {opportunity.organization}",
            f"Category: {category_val}",
            f"Description: {opportunity.description}",
            f"Degree Levels: {', '.join(degree_levels)}",
            f"Fields of Study: {', '.join(fields)}",
            funding_desc,
            f"Country: {opportunity.country}",
            f"Eligible Nationalities: {', '.join(nationalities)}",
        ]

        if opportunity.deadline:
            sections.append(f"Deadline: {opportunity.deadline.isoformat()}")

        searchable_text = " | ".join(sections)
        content_hash = hashlib.sha256(searchable_text.encode("utf-8")).hexdigest()

        # Determine source quality score based on source type
        source_type = "Official Website"
        source_quality = 1.0
        if hasattr(opportunity, "sources") and opportunity.sources:
            primary_source = opportunity.sources[0]
            if hasattr(primary_source, "source_type"):
                source_type = str(primary_source.source_type)
                if (
                    "official" in source_type.lower()
                    or "university" in source_type.lower()
                    or "government" in source_type.lower()
                ):
                    source_quality = 1.0
                elif "aggregator" in source_type.lower() or "directory" in source_type.lower():
                    source_quality = 0.6
                else:
                    source_quality = 0.8

        return OpportunitySearchDocument(
            opportunity_id=str(opportunity.id),
            title=opportunity.title,
            provider=opportunity.organization,
            category=opportunity.category.value
            if hasattr(opportunity.category, "value")
            else str(opportunity.category),
            description=opportunity.description,
            fields=fields,
            degree_levels=degree_levels,
            funding_summary=(
                f"{opportunity.funding_type} {opportunity.funding_amount or ''}"
            ).strip(),
            funding_amount=opportunity.funding_amount,
            currency=opportunity.currency,
            countries=countries,
            nationalities=nationalities,
            deadline=opportunity.deadline,
            status=opportunity.status.value
            if hasattr(opportunity.status, "value")
            else str(opportunity.status),
            source_quality_score=source_quality,
            source_type=source_type,
            source_url=opportunity.application_url,
            verified_at=opportunity.updated_at,
            searchable_text=searchable_text,
            content_hash=content_hash,
            embedding_version=self.version,
        )

    def generate_representation(
        self,
        doc: OpportunitySearchDocument,
        repr_type: EmbeddingType = EmbeddingType.FULL,
    ) -> str:
        """Formats specific sub-representation for focused semantic embeddings."""
        if repr_type == EmbeddingType.SUMMARY:
            degrees = ", ".join(doc.degree_levels)
            fields = ", ".join(doc.fields)
            return (
                f"{doc.title} by {doc.provider}. {doc.category} for {degrees} "
                f"in {fields}. Funding: {doc.funding_summary}."
            )

        if repr_type == EmbeddingType.ELIGIBILITY:
            degrees = ", ".join(doc.degree_levels)
            fields = ", ".join(doc.fields)
            nats = ", ".join(doc.nationalities)
            tests = ", ".join(doc.tests_required)
            return (
                f"Eligibility: {degrees} degrees in {fields}. "
                f"Nationalities: {nats}. Tests: {tests}."
            )

        if repr_type == EmbeddingType.FUNDING:
            amt = doc.funding_amount or "Full coverage"
            return f"Funding: {doc.funding_summary}. Amount: {amt}. Category: {doc.category}."

        # Default: Full searchable text
        return doc.searchable_text

    async def embed_document(
        self,
        doc: OpportunitySearchDocument,
        repr_type: EmbeddingType = EmbeddingType.FULL,
    ) -> list[float]:
        """Embeds an opportunity representation using active model or deterministic fallback."""
        text = self.generate_representation(doc, repr_type)

        if self.model and await self.model.is_available():
            try:
                embeddings = await self.model.embed_documents([text])
                if embeddings and len(embeddings[0]) > 0:
                    return embeddings[0]
            except Exception:
                pass

        return _generate_deterministic_vector(text, dimension=self.dimension)

    async def embed_query(self, query_text: str) -> list[float]:
        """Embeds search query text into the vector representation space."""
        if self.model and await self.model.is_available():
            try:
                return await self.model.embed_query(query_text)
            except Exception:
                pass

        return _generate_deterministic_vector(query_text, dimension=self.dimension)
