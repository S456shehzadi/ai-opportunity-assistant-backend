"""Provider-independent semantic relevance models and embedding provider abstractions."""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from typing import Any

from app.opportunities.eligibility.profile_adapter import UnifiedUserFacts
from app.opportunities.ranking.factors import (
    get_opp_category,
    get_opp_description,
    get_opp_host_country,
    get_opp_title,
)


class EmbeddingProvider(ABC):
    """Abstract interface for text and profile embedding generation."""

    @abstractmethod
    def embed_text(self, text: str) -> list[float]:
        """Generates a dense vector representation for the given text."""
        pass

    def similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """Calculates cosine similarity between two vector representations."""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        dot = sum(a * b for a, b in zip(vec1, vec2, strict=False))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        if norm1 <= 0.0 or norm2 <= 0.0:
            return 0.0
        return max(0.0, min(1.0, dot / (norm1 * norm2)))


class DeterministicEmbeddingProvider(EmbeddingProvider):
    """Deterministic token-frequency based vector generator for offline execution."""

    def __init__(self, vector_dim: int = 64):
        self.vector_dim = vector_dim

    def embed_text(self, text: str) -> list[float]:
        import re

        tokens = re.findall(r"\w+", text.lower())
        vec = [0.0] * self.vector_dim
        if not tokens:
            return vec

        for t in tokens:
            idx = hash(t) % self.vector_dim
            vec[idx] += 1.0

        # Normalize L2
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]
        return vec


class OpportunityRelevanceModel(ABC):
    """Abstract interface for semantic comparison between profiles and opportunities."""

    @abstractmethod
    def calculate_semantic_relevance(self, user_text: str, opportunity_text: str) -> float:
        """Computes semantic alignment score between user description and opportunity."""
        pass

    @abstractmethod
    def compare_profile_to_opportunity(self, user_facts: UnifiedUserFacts, opp: Any) -> float:
        """Calculates holistic semantic profile-to-opportunity affinity."""
        pass


class RuleBasedRelevanceModel(OpportunityRelevanceModel):
    """Default deterministic semantic model using token-based similarity and taxonomy."""

    def __init__(self, embedder: EmbeddingProvider | None = None):
        self.embedder = embedder or DeterministicEmbeddingProvider()

    def calculate_semantic_relevance(self, user_text: str, opportunity_text: str) -> float:
        v1 = self.embedder.embed_text(user_text)
        v2 = self.embedder.embed_text(opportunity_text)
        return self.embedder.similarity(v1, v2)

    def compare_profile_to_opportunity(self, user_facts: UnifiedUserFacts, opp: Any) -> float:
        user_bio_parts = [
            user_facts.highest_degree_level or "",
            " ".join(str(rec.get("field_of_study", "")) for rec in user_facts.academic_records),
            " ".join(user_facts.skills),
        ]
        user_str = " ".join(part for part in user_bio_parts if part)

        opp_parts = [
            get_opp_title(opp),
            get_opp_category(opp),
            get_opp_host_country(opp),
            get_opp_description(opp)[:300],
        ]
        opp_str = " ".join(opp_parts)

        return self.calculate_semantic_relevance(user_str, opp_str)
