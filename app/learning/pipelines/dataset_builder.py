"""Dataset construction, deduplication, group-aware splitting, and task builders."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from app.evaluation.models.dataset import SplitType
from app.learning.models.model_registry import ModelType
from app.learning.sanitizers.training_sanitizer import TrainingDataSanitizer

logger = logging.getLogger(__name__)


def _compute_example_hash(example: dict[str, Any]) -> str:
    """Computes deterministic MD5/SHA256 fingerprint for example content."""
    canonical_repr = {
        "input_data": example.get("input_data", {}),
        "expected_output": example.get("expected_output", {}),
    }
    encoded = json.dumps(canonical_repr, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _extract_tokens(text: str) -> set[str]:
    """Simple tokenization for jaccard similarity check."""
    return {w.lower() for w in text.split() if len(w) > 2}


def _jaccard_similarity(set_a: set[str], set_b: set[str]) -> float:
    """Computes Jaccard index between two token sets."""
    if not set_a and not set_b:
        return 1.0
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a.intersection(set_b))
    union = len(set_a.union(set_b))
    return float(intersection) / float(union) if union > 0 else 0.0


class DatasetBuilder:
    """Builder for curated task-specific training and evaluation datasets."""

    def __init__(self, sanitizer: TrainingDataSanitizer | None = None) -> None:
        self.sanitizer = sanitizer or TrainingDataSanitizer()

    def deduplicate_examples(
        self,
        examples: list[dict[str, Any]],
        near_duplicate_threshold: float = 0.90,
    ) -> list[dict[str, Any]]:
        """Removes exact hash duplicates and token-similar near duplicates."""
        seen_hashes: set[str] = set()
        deduped: list[dict[str, Any]] = []
        token_sets: list[set[str]] = []

        for ex in examples:
            h = _compute_example_hash(ex)
            if h in seen_hashes:
                continue

            # Check near duplicate against existing retained examples
            input_text = str(ex.get("input_data", ""))
            tokens = _extract_tokens(input_text)

            is_near_dup = False
            if len(tokens) >= 5:
                for existing_tokens in token_sets:
                    if _jaccard_similarity(tokens, existing_tokens) >= near_duplicate_threshold:
                        is_near_dup = True
                        break

            if not is_near_dup:
                seen_hashes.add(h)
                deduped.append(ex)
                if len(tokens) >= 5:
                    token_sets.append(tokens)

        return deduped

    def group_aware_split(
        self,
        examples: list[dict[str, Any]],
        train_ratio: float = 0.70,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        holdout_ratio: float = 0.0,
        group_key: str = "opportunity_id",
    ) -> dict[SplitType, list[dict[str, Any]]]:
        """Partitions examples into splits ensuring all records for any group stay together."""
        total_ratio = train_ratio + val_ratio + test_ratio + holdout_ratio
        if abs(total_ratio - 1.0) > 0.01:
            raise ValueError(f"Ratios must sum to 1.0, got {total_ratio}")

        groups: dict[str, list[dict[str, Any]]] = {}
        for idx, ex in enumerate(examples):
            meta = ex.get("metadata", {})
            gid = (
                meta.get(group_key)
                or meta.get("opportunity_id")
                or meta.get("source_domain")
                or meta.get("group_id")
                or f"single_example_{idx}"
            )
            groups.setdefault(str(gid), []).append(ex)

        sorted_group_ids = sorted(groups.keys())
        total_groups = len(sorted_group_ids)

        train_cutoff = int(total_groups * train_ratio)
        val_cutoff = train_cutoff + int(total_groups * val_ratio)
        test_cutoff = val_cutoff + int(total_groups * test_ratio)

        splits: dict[SplitType, list[dict[str, Any]]] = {
            SplitType.TRAIN: [],
            SplitType.VALIDATION: [],
            SplitType.TEST: [],
            SplitType.HOLDOUT: [],
        }

        for i, gid in enumerate(sorted_group_ids):
            items = groups[gid]
            if i < train_cutoff:
                for item in items:
                    item["split"] = SplitType.TRAIN
                splits[SplitType.TRAIN].extend(items)
            elif i < val_cutoff:
                for item in items:
                    item["split"] = SplitType.VALIDATION
                splits[SplitType.VALIDATION].extend(items)
            elif i < test_cutoff:
                for item in items:
                    item["split"] = SplitType.TEST
                splits[SplitType.TEST].extend(items)
            else:
                for item in items:
                    item["split"] = SplitType.HOLDOUT
                splits[SplitType.HOLDOUT].extend(items)

        return splits

    def validate_and_sanitize(
        self,
        examples: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], int, int]:
        """Scrubs PII and rejects records without valid provenance or consent."""
        sanitized_list: list[dict[str, Any]] = []
        redacted_count = 0
        rejected_count = 0

        for ex in examples:
            if not self.sanitizer.verify_provenance_and_consent(ex):
                rejected_count += 1
                continue

            cleaned, was_redacted = self.sanitizer.sanitize_example(ex)
            if was_redacted:
                redacted_count += 1
            sanitized_list.append(cleaned)

        return sanitized_list, redacted_count, rejected_count

    def build_task_dataset(
        self,
        task: ModelType,
        raw_examples: list[dict[str, Any]],
        train_ratio: float = 0.70,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        holdout_ratio: float = 0.0,
    ) -> dict[SplitType, list[dict[str, Any]]]:
        """End-to-end dataset builder pipeline with governance and group isolation."""
        # 1. Validate & Sanitize
        valid_examples, _, _ = self.validate_and_sanitize(raw_examples)

        # 2. Deduplicate
        deduped = self.deduplicate_examples(valid_examples)

        # 3. Group-aware split
        return self.group_aware_split(
            examples=deduped,
            train_ratio=train_ratio,
            val_ratio=val_ratio,
            test_ratio=test_ratio,
            holdout_ratio=holdout_ratio,
        )
