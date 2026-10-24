"""End-to-end integration test for Phase 13 training, governance, and deployment loop."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.evaluation.models.dataset import SplitType
from app.learning.models.model_registry import (
    ModelStatus,
    ModelType,
)
from app.learning.pipelines.dataset_builder import DatasetBuilder
from app.learning.schemas.learning import ModelDefinitionCreate
from app.learning.schemas.training import (
    ModelCardCreate,
    ModelPromotionRequest,
    ModelRollbackRequest,
    ResourceLimits,
    TrainingHyperparameters,
    TrainingJobCreate,
)
from app.learning.services.model_registry_service import ModelRegistryService
from app.learning.services.model_serving_service import ModelServingService
from app.learning.services.training_service import TrainingService
from app.learning.training.mock_backend import MockLocalTrainingBackend


@pytest.mark.asyncio
async def test_full_phase13_training_and_deployment_lifecycle(
    test_db_session: AsyncSession,
) -> None:
    # -------------------------------------------------------------
    # 1. Curate, Sanitize, and Split Task Dataset
    # -------------------------------------------------------------
    raw_data = [
        {
            "input_data": {"text": "Scholarship for Computer Science at TUM john@test.com"},
            "expected_output": {"intent": "SEARCH_OPPORTUNITY", "degree": "Master"},
            "provenance_review_id": "00000000-0000-0000-0000-000000000001",
            "metadata": {"opportunity_id": "tum_cs_2026", "license": "MIT"},
        },
        {
            "input_data": {"text": "TUM CS application requirements"},
            "expected_output": {"intent": "CHECK_REQUIREMENTS"},
            "provenance_review_id": "00000000-0000-0000-0000-000000000001",
            "metadata": {"opportunity_id": "tum_cs_2026", "license": "MIT"},
        },
        {
            "input_data": {"text": "DAAD scholarship in Berlin"},
            "expected_output": {"intent": "SEARCH_OPPORTUNITY", "location": "Berlin"},
            "provenance_review_id": "00000000-0000-0000-0000-000000000002",
            "metadata": {"opportunity_id": "daad_berlin", "license": "CC-BY-4.0"},
        },
    ]

    builder = DatasetBuilder()
    splits = builder.build_task_dataset(
        task=ModelType.QUERY_UNDERSTANDING,
        raw_examples=raw_data,
        train_ratio=0.5,
        val_ratio=0.5,
        test_ratio=0.0,
    )
    # Check that PII was redacted
    assert "[REDACTED_EMAIL]" in str(splits[SplitType.TRAIN] + splits[SplitType.VALIDATION])
    assert "john@test.com" not in str(splits[SplitType.TRAIN] + splits[SplitType.VALIDATION])

    # -------------------------------------------------------------
    # 2. Run Training Job via TrainingService
    # -------------------------------------------------------------
    backend = MockLocalTrainingBackend(artifact_dir="tests/test_artifacts")
    training_service = TrainingService(backend=backend)

    job_create = TrainingJobCreate(
        job_name="e2e_query_understanding_model",
        task=ModelType.QUERY_UNDERSTANDING,
        base_model="deberta-v3-small",
        training_backend="LOCAL",
        hyperparameters=TrainingHyperparameters(epochs=2),
        resource_limits=ResourceLimits(max_duration_seconds=60),
    )
    job = await training_service.create_and_start_job(db=test_db_session, payload=job_create)
    assert job.status.value == "COMPLETED"
    assert len(job.artifacts) == 1
    artifact_checksum = job.artifacts[0].checksum
    assert len(artifact_checksum) == 64  # valid SHA256 hex digest

    # -------------------------------------------------------------
    # 3. Register Model with Model Card in Catalog
    # -------------------------------------------------------------
    registry_service = ModelRegistryService()
    model = await registry_service.register_model(
        db=test_db_session,
        payload=ModelDefinitionCreate(
            model_id="query-deberta-v1",
            provider="LOCAL",
            model_name="deberta-v3-small-finetuned",
            model_type=ModelType.QUERY_UNDERSTANDING,
            version="1.0.0",
            capabilities=["QUERY_UNDERSTANDING"],
        ),
        model_card_payload=ModelCardCreate(
            purpose="Parse and categorize complex educational queries",
            task="QUERY_UNDERSTANDING",
            intended_use="Extract academic intents and constraints",
            evaluation_metrics={"accuracy": job.metrics["val_accuracy"]},
            license="MIT",
        ),
    )
    assert model.status == ModelStatus.DEVELOPMENT

    # -------------------------------------------------------------
    # 4. Gate Promotion: Development -> Evaluation -> Candidate -> Staging -> Production
    # -------------------------------------------------------------
    model = await registry_service.promote_model(
        db=test_db_session,
        model_id="query-deberta-v1",
        request=ModelPromotionRequest(target_status=ModelStatus.EVALUATION),
    )
    model = await registry_service.promote_model(
        db=test_db_session,
        model_id="query-deberta-v1",
        request=ModelPromotionRequest(
            target_status=ModelStatus.CANDIDATE,
            min_metric_threshold={"accuracy": 0.80},
        ),
    )
    model = await registry_service.promote_model(
        db=test_db_session,
        model_id="query-deberta-v1",
        request=ModelPromotionRequest(target_status=ModelStatus.STAGING),
    )
    model = await registry_service.promote_model(
        db=test_db_session,
        model_id="query-deberta-v1",
        request=ModelPromotionRequest(target_status=ModelStatus.PRODUCTION),
    )
    assert model.status == ModelStatus.PRODUCTION

    # -------------------------------------------------------------
    # 5. Serve Query with Safe Fallback Protection
    # -------------------------------------------------------------
    serving_service = ModelServingService()

    async def specialized_invoker():
        return {"intent": "SEARCH_OPPORTUNITY", "domain": "Computer Science"}

    async def fallback_invoker():
        return {"intent": "FALLBACK_GENERAL"}

    res, meta = await serving_service.execute_with_fallback(
        db=test_db_session,
        task=ModelType.QUERY_UNDERSTANDING,
        specialized_invoker=specialized_invoker,
        fallback_invoker=fallback_invoker,
    )
    assert res["intent"] == "SEARCH_OPPORTUNITY"
    assert meta["used_fallback"] is False
    assert meta["model_id"] == "query-deberta-v1"

    # -------------------------------------------------------------
    # 6. Verify Rollback on Demotion / Regression
    # -------------------------------------------------------------
    # Register v2 as next production model
    v2_model = await registry_service.register_model(
        db=test_db_session,
        payload=ModelDefinitionCreate(
            model_id="query-deberta-v2",
            provider="LOCAL",
            model_name="deberta-v3-large-finetuned",
            model_type=ModelType.QUERY_UNDERSTANDING,
        ),
    )
    v2_model.status = ModelStatus.STAGING
    await test_db_session.commit()

    promoted_v2 = await registry_service.promote_model(
        db=test_db_session,
        model_id="query-deberta-v2",
        request=ModelPromotionRequest(target_status=ModelStatus.PRODUCTION),
    )
    assert promoted_v2.status == ModelStatus.PRODUCTION
    assert promoted_v2.rollback_model_id == "query-deberta-v1"

    # Rollback to v1
    restored = await registry_service.rollback_model(
        db=test_db_session,
        model_id="query-deberta-v2",
        request=ModelRollbackRequest(reason="Performance regression detected"),
    )
    assert restored.model_id == "query-deberta-v1"
    assert restored.status == ModelStatus.PRODUCTION
