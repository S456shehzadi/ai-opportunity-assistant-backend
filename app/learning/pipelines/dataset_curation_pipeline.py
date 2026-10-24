"""Curated dataset pipeline converting verified human corrections into dataset examples."""

from __future__ import annotations

from app.evaluation.models.dataset import SplitType
from app.evaluation.schemas.evaluation import DatasetExampleInput
from app.review.models.correction import HumanCorrection


class CuratedDatasetPipeline:
    """Pipelines human-verified corrections into standardized dataset examples."""

    @staticmethod
    def process_corrections_into_examples(
        corrections: list[HumanCorrection],
        target_split: SplitType = SplitType.TRAIN,
    ) -> list[DatasetExampleInput]:
        """Transforms auditable review corrections into curated benchmark ground truth."""
        examples: list[DatasetExampleInput] = []

        for c in corrections:
            example = DatasetExampleInput(
                split=target_split,
                input_data=c.original_value,
                expected_output=c.corrected_value,
                metadata_json={
                    "evidence": c.evidence,
                    "reason": c.reason,
                    "reviewer_id": str(c.reviewer_id) if c.reviewer_id else None,
                },
                provenance_review_id=c.review_id,
            )
            examples.append(example)
        return examples

    @classmethod
    def curate_from_correction(
        cls,
        correction: HumanCorrection,
        split: SplitType = SplitType.TRAIN,
        task_type: str = "EXTRACTION",
    ) -> DatasetExampleInput:
        """Transforms a single correction into a DatasetExampleInput."""
        return cls.process_corrections_into_examples([correction], target_split=split)[0]


DatasetCurationPipeline = CuratedDatasetPipeline
