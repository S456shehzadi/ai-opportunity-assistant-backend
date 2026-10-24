"""Retrieval quality evaluator measuring Precision@K, Recall@K, MRR, and NDCG."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from app.discovery.engine import AdvancedDiscoveryEngine
from app.discovery.evaluation.benchmark import BenchmarkQueryItem
from app.discovery.models import SearchStrategy


@dataclass
class EvaluationReport:
    """Quantitative performance report for a retrieval configuration."""

    strategy: str
    precision_at_k: float
    recall_at_k: float
    mrr: float
    ndcg_at_k: float
    hit_rate: float
    avg_latency_ms: float
    evaluated_queries: int
    detailed_metrics: list[dict[str, Any]] = field(default_factory=list)


class RetrievalEvaluator:
    """Evaluates and benchmarks search performance across retrieval strategies."""

    def __init__(self, engine: AdvancedDiscoveryEngine, k: int = 5) -> None:
        self.engine = engine
        self.k = k

    async def evaluate_strategy(
        self,
        strategy: SearchStrategy,
        benchmark_items: list[BenchmarkQueryItem],
    ) -> EvaluationReport:
        precisions: list[float] = []
        recalls: list[float] = []
        mrrs: list[float] = []
        ndcgs: list[float] = []
        hits: list[float] = []
        latencies: list[float] = []
        details: list[dict[str, Any]] = []

        for item in benchmark_items:
            res = await self.engine.search(item.query, strategy=strategy, limit=self.k)
            retrieved_ids = [c.opportunity_id for c in res.candidates[: self.k]]
            expected = set(item.expected_relevant_ids)

            # 1. Precision@K
            relevant_in_top_k = sum(1 for rid in retrieved_ids if rid in expected)
            p_at_k = relevant_in_top_k / self.k if self.k > 0 else 0.0
            precisions.append(p_at_k)

            # 2. Recall@K
            r_at_k = relevant_in_top_k / len(expected) if expected else 1.0
            recalls.append(r_at_k)

            # 3. MRR (Mean Reciprocal Rank)
            mrr_val = 0.0
            for rank, rid in enumerate(retrieved_ids):
                if rid in expected:
                    mrr_val = 1.0 / (rank + 1)
                    break
            mrrs.append(mrr_val)

            # 4. NDCG@K
            dcg = 0.0
            for rank, rid in enumerate(retrieved_ids):
                if rid in expected:
                    dcg += 1.0 / math.log2(rank + 2)
            idcg = sum(1.0 / math.log2(r + 2) for r in range(min(len(expected), self.k)))
            ndcg_val = (dcg / idcg) if idcg > 0 else 0.0
            ndcgs.append(ndcg_val)

            # 5. Hit Rate
            hit = 1.0 if relevant_in_top_k > 0 else 0.0
            hits.append(hit)

            latencies.append(res.latency_ms)

            details.append(
                {
                    "query": item.query,
                    "retrieved": retrieved_ids,
                    "expected": list(expected),
                    "precision": round(p_at_k, 4),
                    "recall": round(r_at_k, 4),
                    "mrr": round(mrr_val, 4),
                    "ndcg": round(ndcg_val, 4),
                    "latency_ms": res.latency_ms,
                }
            )

        count = len(benchmark_items) or 1
        return EvaluationReport(
            strategy=strategy.value,
            precision_at_k=round(sum(precisions) / count, 4),
            recall_at_k=round(sum(recalls) / count, 4),
            mrr=round(sum(mrrs) / count, 4),
            ndcg_at_k=round(sum(ndcgs) / count, 4),
            hit_rate=round(sum(hits) / count, 4),
            avg_latency_ms=round(sum(latencies) / count, 2),
            evaluated_queries=len(benchmark_items),
            detailed_metrics=details,
        )
