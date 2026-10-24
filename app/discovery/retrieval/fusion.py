"""Hybrid candidate fusion supporting Reciprocal Rank Fusion and Weighted Linear Combination."""

from __future__ import annotations

from app.discovery.models import FusionMethod, OpportunityCandidate


class CandidateFusionService:
    """Fuses multi-source retrieval candidates into a unified ranked list."""

    def __init__(
        self,
        method: FusionMethod = FusionMethod.RRF,
        rrf_k: int = 60,
        keyword_weight: float = 0.4,
        semantic_weight: float = 0.6,
    ) -> None:
        self.method = method
        self.rrf_k = rrf_k
        self.keyword_weight = keyword_weight
        self.semantic_weight = semantic_weight

    def fuse(
        self,
        keyword_candidates: list[OpportunityCandidate],
        semantic_candidates: list[OpportunityCandidate],
        top_k: int = 100,
    ) -> list[OpportunityCandidate]:
        """Merges keyword and semantic candidate lists into a single deduplicated ranked list."""
        merged_map: dict[str, OpportunityCandidate] = {}

        if self.method == FusionMethod.RRF:
            # Reciprocal Rank Fusion
            # 1. Process Keyword ranks
            for rank, c in enumerate(keyword_candidates):
                rrf_score = 1.0 / (self.rrf_k + (rank + 1))
                if c.opportunity_id not in merged_map:
                    merged_map[c.opportunity_id] = c.model_copy()
                    merged_map[c.opportunity_id].fusion_score = rrf_score
                else:
                    target = merged_map[c.opportunity_id]
                    target.fusion_score += rrf_score
                    target.keyword_score = max(target.keyword_score, c.keyword_score)
                    if "KEYWORD" not in target.retrieval_sources:
                        target.retrieval_sources.append("KEYWORD")

            # 2. Process Semantic ranks
            for rank, c in enumerate(semantic_candidates):
                rrf_score = 1.0 / (self.rrf_k + (rank + 1))
                if c.opportunity_id not in merged_map:
                    merged_map[c.opportunity_id] = c.model_copy()
                    merged_map[c.opportunity_id].fusion_score = rrf_score
                else:
                    target = merged_map[c.opportunity_id]
                    target.fusion_score += rrf_score
                    target.semantic_score = max(target.semantic_score, c.semantic_score)
                    if "SEMANTIC" not in target.retrieval_sources:
                        target.retrieval_sources.append("SEMANTIC")

        else:
            # Weighted Linear Score Fusion
            for c in keyword_candidates:
                merged_map[c.opportunity_id] = c.model_copy()

            for c in semantic_candidates:
                if c.opportunity_id in merged_map:
                    target = merged_map[c.opportunity_id]
                    target.semantic_score = c.semantic_score
                    if "SEMANTIC" not in target.retrieval_sources:
                        target.retrieval_sources.append("SEMANTIC")
                else:
                    merged_map[c.opportunity_id] = c.model_copy()

            for c in merged_map.values():
                c.fusion_score = (self.keyword_weight * c.keyword_score) + (
                    self.semantic_weight * c.semantic_score
                )

        fused_list = list(merged_map.values())
        fused_list.sort(key=lambda x: x.fusion_score, reverse=True)
        return fused_list[:top_k]
