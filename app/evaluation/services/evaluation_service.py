"""Service orchestrating benchmark dataset versioning and reproducible evaluation runs."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.evaluation.evaluators.eligibility_evaluator import EligibilityEvaluator
from app.evaluation.evaluators.extraction_evaluator import ExtractionEvaluator
from app.evaluation.evaluators.grounding_evaluator import GroundingEvaluator
from app.evaluation.evaluators.ranking_evaluator import RankingEvaluator
from app.evaluation.models.dataset import (
    Dataset,
    DatasetExample,
    DatasetVersion,
    SplitType,
)
from app.evaluation.models.evaluation_run import EvaluationRun, EvaluationStatus
from app.evaluation.schemas.evaluation import (
    DatasetCreate,
    DatasetVersionCreate,
    EvaluationRunCreate,
)

logger = logging.getLogger(__name__)


class EvaluationService:
    """Orchestrates reproducible benchmark datasets, holdout isolation, and evaluation runs."""

    def __init__(self) -> None:
        self.extraction_evaluator = ExtractionEvaluator()
        self.eligibility_evaluator = EligibilityEvaluator()
        self.ranking_evaluator = RankingEvaluator()
        self.grounding_evaluator = GroundingEvaluator()

    async def create_dataset(
        self,
        db: AsyncSession,
        payload: DatasetCreate,
    ) -> Dataset:
        """Initializes a new logical dataset definition."""
        dataset = Dataset(
            name=payload.name,
            task_type=payload.task_type,
            description=payload.description,
        )
        db.add(dataset)
        await db.commit()
        query = (
            select(Dataset).options(selectinload(Dataset.versions)).where(Dataset.id == dataset.id)
        )
        res = await db.execute(query)
        return res.scalar_one()

    async def create_dataset_version(
        self,
        db: AsyncSession,
        dataset_id: UUID,
        payload: DatasetVersionCreate,
    ) -> DatasetVersion:
        """Creates an immutable dataset version and assigns ground truth examples to splits."""
        split_counts: dict[str, int] = {
            SplitType.TRAIN.value: 0,
            SplitType.VALIDATION.value: 0,
            SplitType.TEST.value: 0,
            SplitType.HOLDOUT.value: 0,
        }
        for eg in payload.examples:
            split_key = eg.split.value if hasattr(eg.split, "value") else str(eg.split)
            split_counts[split_key] = split_counts.get(split_key, 0) + 1

        version = DatasetVersion(
            dataset_id=dataset_id,
            version_tag=payload.version_tag,
            example_count=len(payload.examples),
            quality_status=payload.quality_status,
            split_counts=split_counts,
        )
        db.add(version)
        await db.flush()

        for eg in payload.examples:
            example_record = DatasetExample(
                dataset_version_id=version.id,
                split=eg.split,
                input_data=eg.input_data,
                expected_output=eg.expected_output,
                metadata_json=eg.metadata_json,
                provenance_review_id=eg.provenance_review_id,
            )
            db.add(example_record)

        await db.commit()
        await db.refresh(version)
        return version

    async def get_dataset_examples(
        self,
        db: AsyncSession,
        version_id: UUID,
        split: SplitType | None = None,
        allow_holdout: bool = False,
    ) -> list[DatasetExample]:
        """Retrieves examples with strict holdout isolation enforcement."""
        if split == SplitType.HOLDOUT and not allow_holdout:
            raise PermissionError(
                "Access to HOLDOUT split is restricted to final verification runs."
            )

        query = select(DatasetExample).where(DatasetExample.dataset_version_id == version_id)
        if split is not None:
            query = query.where(DatasetExample.split == split)

        result = await db.execute(query)
        examples = list(result.scalars().all())

        if not allow_holdout:
            # Exclude any holdout examples from standard access
            examples = [e for e in examples if e.split != SplitType.HOLDOUT]

        return examples

    async def execute_evaluation_run(
        self,
        db: AsyncSession,
        payload: EvaluationRunCreate,
    ) -> EvaluationRun:
        """Executes a benchmark run against a dataset version and captures auditable metrics."""
        version_query = (
            select(DatasetVersion)
            .options(selectinload(DatasetVersion.dataset))
            .where(DatasetVersion.id == payload.dataset_version_id)
        )
        v_res = await db.execute(version_query)
        version = v_res.scalar_one_or_none()
        if not version:
            raise ValueError(f"DatasetVersion {payload.dataset_version_id} not found")

        task_type = version.dataset.task_type.upper()

        run = EvaluationRun(
            model_provider=payload.model_provider,
            model_name=payload.model_name,
            model_version=payload.model_version,
            prompt_name=payload.prompt_name,
            prompt_version=payload.prompt_version,
            dataset_version_id=payload.dataset_version_id,
            configuration=payload.configuration,
            metrics_summary={},
            claim_evaluations=payload.claims_to_evaluate or [],
            status=EvaluationStatus.RUNNING,
        )
        db.add(run)
        await db.commit()
        await db.refresh(run)

        try:
            # Fetch test examples (holdout excluded)
            examples = await self.get_dataset_examples(
                db=db,
                version_id=version.id,
                split=SplitType.TEST,
                allow_holdout=False,
            )

            # Fallback to validation or all non-holdout if no explicit TEST split
            if not examples:
                examples = await self.get_dataset_examples(
                    db=db,
                    version_id=version.id,
                    allow_holdout=False,
                )

            metrics: dict[str, Any] = {}

            if "EXTRACTION" in task_type:
                preds = [e.input_data.get("prediction", {}) for e in examples]
                gts = [e.expected_output for e in examples]
                metrics = self.extraction_evaluator.evaluate_batch(preds, gts)

            elif "ELIGIBILITY" in task_type:
                test_cases = [
                    {
                        "profile": e.input_data.get("profile", {}),
                        "opportunity": e.input_data.get("opportunity", {}),
                        "expected_status": e.expected_output.get("status", "POTENTIALLY_ELIGIBLE"),
                    }
                    for e in examples
                ]
                metrics = await self.eligibility_evaluator.evaluate_dataset(test_cases)

            elif "RANKING" in task_type:
                pred_ids = payload.configuration.get("predicted_ids", [])
                relevance = payload.configuration.get("relevance_dict", {})
                k_val = payload.configuration.get("k", 5)
                metrics = self.ranking_evaluator.evaluate(
                    predicted_ids=pred_ids,
                    relevance_grades=relevance,
                    k=k_val,
                )

            elif "GROUNDING" in task_type or "ASSISTANT" in task_type:
                claims = payload.claims_to_evaluate or []
                metrics = self.grounding_evaluator.evaluate_claims(claims)

            else:
                # Generic metric aggregation
                metrics = {
                    "total_examples_evaluated": len(examples),
                    "status": "completed",
                }

            run.metrics_summary = metrics
            run.status = EvaluationStatus.COMPLETED
            run.error_message = None

        except Exception as exc:
            logger.exception("Evaluation run %s failed", run.id)
            run.status = EvaluationStatus.FAILED
            run.error_message = str(exc)

        await db.commit()
        await db.refresh(run)
        return run

    async def list_datasets(
        self,
        db: AsyncSession,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Dataset]:
        """Lists benchmark datasets with eager-loaded versions."""
        query = (
            select(Dataset)
            .options(selectinload(Dataset.versions))
            .order_by(Dataset.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        res = await db.execute(query)
        return list(res.scalars().all())

    async def list_evaluation_runs(
        self,
        db: AsyncSession,
        limit: int = 50,
        offset: int = 0,
    ) -> list[EvaluationRun]:
        """Lists evaluation benchmark runs in reverse chronological order."""
        query = (
            select(EvaluationRun)
            .order_by(EvaluationRun.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        res = await db.execute(query)
        return list(res.scalars().all())
