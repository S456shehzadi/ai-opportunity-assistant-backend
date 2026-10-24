"""Ranking metrics: Precision@K, Recall@K, MRR, NDCG@K, and eligibility consistency."""

from __future__ import annotations

import math


class RankingMetricsCalculator:
    """Calculates search and recommendation ranking quality metrics."""

    @staticmethod
    def evaluate_ranking(
        predicted_ids: list[str],
        relevance_dict: dict[str, int],  # id -> graded relevance (e.g. 0 to 3)
        k: int = 5,
        ineligible_ids: set[str] | None = None,
    ) -> dict[str, float]:
        """Evaluates ranking results against ground-truth relevance grades."""
        top_k = predicted_ids[:k]
        if not top_k:
            return {
                f"precision@{k}": 0.0,
                f"recall@{k}": 0.0,
                "mrr": 0.0,
                f"ndcg@{k}": 0.0,
                "eligibility_violation_rate": 0.0,
            }

        # 1. Precision@K and Recall@K
        relevant_total = sum(1 for grade in relevance_dict.values() if grade > 0)
        hits_in_k = sum(1 for item_id in top_k if relevance_dict.get(item_id, 0) > 0)

        precision_at_k = hits_in_k / len(top_k)
        recall_at_k = hits_in_k / relevant_total if relevant_total > 0 else 0.0

        # 2. MRR (Mean Reciprocal Rank)
        mrr = 0.0
        for rank, item_id in enumerate(predicted_ids, start=1):
            if relevance_dict.get(item_id, 0) > 0:
                mrr = 1.0 / rank
                break

        # 3. NDCG@K
        dcg = 0.0
        for i, item_id in enumerate(top_k):
            rel = relevance_dict.get(item_id, 0)
            dcg += (2**rel - 1) / math.log2(i + 2)

        ideal_grades = sorted(relevance_dict.values(), reverse=True)[:k]
        idcg = 0.0
        for i, rel in enumerate(ideal_grades):
            idcg += (2**rel - 1) / math.log2(i + 2)

        ndcg = dcg / idcg if idcg > 0 else 0.0

        # 4. Eligibility violation rate
        ineligible = ineligible_ids or set()
        violations = sum(1 for item_id in top_k if item_id in ineligible)
        violation_rate = violations / len(top_k)

        return {
            f"precision@{k}": round(precision_at_k, 4),
            f"recall@{k}": round(recall_at_k, 4),
            "mrr": round(mrr, 4),
            f"ndcg@{k}": round(ndcg, 4),
            "eligibility_violation_rate": round(violation_rate, 4),
        }

    @classmethod
    def calculate_ndcg_at_k(
        cls, predicted_ids: list[str], relevance_dict: dict[str, int | float], k: int = 5
    ) -> float:
        """Helper computing NDCG@K."""
        res = cls.evaluate_ranking(
            predicted_ids=predicted_ids,
            relevance_dict={k: int(v) for k, v in relevance_dict.items()},
            k=k,
        )
        return res[f"ndcg@{k}"]

    @classmethod
    def calculate_mrr(
        cls, predicted_ids: list[str], relevance_dict: dict[str, int | float]
    ) -> float:
        """Helper computing MRR."""
        res = cls.evaluate_ranking(
            predicted_ids=predicted_ids,
            relevance_dict={k: int(v) for k, v in relevance_dict.items()},
        )
        return res["mrr"]

    @classmethod
    def calculate_eligibility_violation_rate(
        cls,
        ranked_opportunity_ids: list[str],
        ineligible_opportunity_ids: set[str],
        k: int | None = None,
    ) -> float:
        """Helper computing eligibility violation rate in top ranked items."""
        eval_k = k or len(ranked_opportunity_ids)
        res = cls.evaluate_ranking(
            predicted_ids=ranked_opportunity_ids,
            relevance_dict={},
            k=eval_k,
            ineligible_ids=ineligible_opportunity_ids,
        )
        return res["eligibility_violation_rate"]
