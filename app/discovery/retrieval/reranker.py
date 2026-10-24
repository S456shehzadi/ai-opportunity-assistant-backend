"""Semantic cross-matching reranker evaluating candidate relevance and intent alignment."""

from __future__ import annotations

import re

from app.discovery.interfaces import Reranker
from app.discovery.models import OpportunityCandidate
from app.learning.interfaces.model import RerankingModel


class SemanticReranker(Reranker):
    """Deep cross-attention or heuristic semantic reranker assessing candidate relevance."""

    def __init__(self, model: RerankingModel | None = None) -> None:
        self.model = model

    async def rerank(
        self,
        query: str,
        candidates: list[OpportunityCandidate],
        top_k: int = 50,
    ) -> list[OpportunityCandidate]:
        if not candidates:
            return []

        # If a specialized neural reranking model is available, use it
        if self.model and await self.model.is_available():
            try:
                documents = [
                    f"{c.title} by {c.provider}. {c.document.description}" for c in candidates
                ]
                results = await self.model.rerank(query, documents, top_k=top_k)
                score_map = {res.index: res.score for res in results}
                for idx, c in enumerate(candidates):
                    if idx in score_map:
                        c.reranker_score = round(score_map[idx], 4)
                        c.final_discovery_score = (c.fusion_score * 0.4) + (c.reranker_score * 0.6)
                candidates.sort(key=lambda x: x.final_discovery_score, reverse=True)
                return candidates[:top_k]
            except Exception:
                pass  # Fall back to heuristic alignment scoring

        # Heuristic cross-matching alignment
        query_lower = query.lower()
        query_tokens = set(re.findall(r"\w+", query_lower))

        for c in candidates:
            doc = c.document
            alignment_score = 0.5  # base neutral score

            # 1. Field of study alignment
            field_tokens = set(re.findall(r"\w+", " ".join(doc.fields).lower()))
            if query_tokens.intersection(field_tokens):
                alignment_score += 0.2

            # 2. Degree alignment
            deg_tokens = set(re.findall(r"\w+", " ".join(doc.degree_levels).lower()))
            if query_tokens.intersection(deg_tokens):
                alignment_score += 0.15

            # 3. Funding alignment
            if "fund" in query_lower and (
                "fully funded" in doc.funding_summary.lower() or "100%" in doc.funding_summary
            ):
                alignment_score += 0.15

            # 4. Location alignment
            country_tokens = set(re.findall(r"\w+", " ".join(doc.countries).lower()))
            if query_tokens.intersection(country_tokens):
                alignment_score += 0.1

            norm_rerank = min(1.0, alignment_score)
            c.reranker_score = round(norm_rerank, 4)
            # Final discovery score blends fusion score and reranker score
            c.final_discovery_score = round((c.fusion_score * 0.35) + (norm_rerank * 0.65), 4)

        candidates.sort(key=lambda x: x.final_discovery_score, reverse=True)
        return candidates[:top_k]
