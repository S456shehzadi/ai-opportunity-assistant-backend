"""End-to-end test of the complete Human-in-the-Loop learning loop:
User feedback -> Auto review queue -> Human correction -> Dataset curation -> Evaluation.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.evaluation.models.dataset import DatasetQualityStatus, SplitType
from app.evaluation.schemas.evaluation import (
    DatasetCreate,
    DatasetVersionCreate,
    EvaluationRunCreate,
)
from app.evaluation.services.evaluation_service import EvaluationService
from app.feedback.models.feedback import FeedbackTargetType, FeedbackType
from app.feedback.schemas.feedback import FeedbackCreate
from app.feedback.services.feedback_service import FeedbackService
from app.learning.pipelines.dataset_curation_pipeline import DatasetCurationPipeline
from app.review.models.review_item import ReviewCategory, ReviewStatus
from app.review.schemas.review import ReviewResolutionCreate
from app.review.services.review_service import ReviewService


@pytest.mark.asyncio
async def test_complete_auditable_learning_loop(
    test_db_session: AsyncSession,
) -> None:
    feedback_service = FeedbackService()
    review_service = ReviewService()
    evaluation_service = EvaluationService()

    user_id = uuid.uuid4()
    reviewer_id = uuid.uuid4()

    # Step 1: User encounters extraction defect and submits feedback
    feedback_payload = FeedbackCreate(
        target_type=FeedbackTargetType.OPPORTUNITY,
        target_id="opp_mit_fellowship",
        feedback_type=FeedbackType.WRONG_DEADLINE,
        reason="Deadline says May 2024 instead of May 2026",
        comment="Admissions page says applications open through May 1, 2026.",
        context_snapshot={
            "domain": "mit.edu",
            "extracted_deadline": "2024-05-01",
            "opportunity_title": "MIT Global Graduate Fellowship",
        },
    )

    feedback_record = await feedback_service.submit_feedback(
        test_db_session,
        user_id=user_id,
        payload=feedback_payload,
    )
    assert feedback_record.id is not None

    # Step 2: System automatically routes to Review Queue
    queue_items = await review_service.list_review_items(
        test_db_session,
        category=ReviewCategory.DEADLINE,
    )
    assert len(queue_items) >= 1
    review_item = next(i for i in queue_items if i.entity_id == "opp_mit_fellowship")
    assert review_item.status == ReviewStatus.PENDING
    assert review_item.priority == "HIGH"

    # Step 3: Reviewer claims and resolves item with verified human correction
    await review_service.assign_item(
        test_db_session,
        item_id=review_item.id,
        reviewer_id=reviewer_id,
    )

    resolution_payload = ReviewResolutionCreate(
        status=ReviewStatus.CORRECTED,
        resolution_notes="Verified against official MIT graduate admissions portal.",
        evidence="https://gradadmissions.mit.edu/fellowships/global",
        corrected_value={
            "deadline": "2026-05-01",
            "opportunity_title": "MIT Global Graduate Fellowship",
        },
    )

    resolved_item = await review_service.resolve_item(
        test_db_session,
        item_id=review_item.id,
        reviewer_id=reviewer_id,
        payload=resolution_payload,
    )
    assert resolved_item.status == ReviewStatus.CORRECTED

    # Re-fetch item to load human corrections
    fetched_item = await review_service.get_review_item(test_db_session, item_id=review_item.id)
    assert fetched_item is not None
    assert len(fetched_item.corrections) == 1
    correction = fetched_item.corrections[0]

    # Step 4: Dataset curation pipeline converts correction into benchmark example
    curated_example = DatasetCurationPipeline.curate_from_correction(
        correction=correction,
        split=SplitType.TEST,
        task_type="EXTRACTION",
    )
    assert curated_example.split == SplitType.TEST
    assert curated_example.expected_output["deadline"] == "2026-05-01"
    assert curated_example.provenance_review_id == review_item.id

    # Step 5: Benchmark dataset definition and version release
    benchmark = await evaluation_service.create_dataset(
        test_db_session,
        payload=DatasetCreate(
            name="Admissions Deadline Extraction Benchmark",
            task_type="EXTRACTION",
            description="Verified corrections benchmark for deadline extraction.",
        ),
    )

    # Add prediction field to input_data to simulate a model run
    curated_example.input_data["prediction"] = {
        "deadline": "2026-05-01",
        "opportunity_title": "MIT Global Graduate Fellowship",
    }

    dataset_version = await evaluation_service.create_dataset_version(
        test_db_session,
        dataset_id=benchmark.id,
        payload=DatasetVersionCreate(
            version_tag="v1.0.0",
            quality_status=DatasetQualityStatus.VERIFIED,
            examples=[curated_example],
        ),
    )
    assert dataset_version.example_count == 1

    # Step 6: Execute reproducible evaluation run against dataset version
    eval_run = await evaluation_service.execute_evaluation_run(
        test_db_session,
        payload=EvaluationRunCreate(
            dataset_version_id=dataset_version.id,
            model_provider="anthropic",
            model_name="claude-3-5-sonnet",
            model_version="20241022",
            prompt_name="opportunity_extractor",
            prompt_version="v2.1",
        ),
    )

    assert eval_run.id is not None
    assert eval_run.status.value == "COMPLETED"
    assert eval_run.metrics_summary["exact_match_rate"] == 1.0
    assert eval_run.metrics_summary["precision"] == 1.0
    assert eval_run.metrics_summary["recall"] == 1.0
