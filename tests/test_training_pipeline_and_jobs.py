"""Tests for fine-tuning jobs, execution backends, and training APIs."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_dev_user
from app.learning.models.model_registry import ModelType
from app.learning.models.training_job import TrainingJob, TrainingJobStatus
from app.learning.schemas.training import (
    ResourceLimits,
    TrainingHyperparameters,
    TrainingJobCreate,
)
from app.learning.services.training_service import TrainingService
from app.learning.training.mock_backend import MockLocalTrainingBackend
from app.models.user import User, UserRole


@pytest.mark.asyncio
async def test_mock_training_backend_execution() -> None:
    backend = MockLocalTrainingBackend(artifact_dir="tests/test_artifacts")

    dummy_job = TrainingJob(
        id=uuid.uuid4(),
        job_name="query_classifier_v1",
        task=ModelType.QUERY_UNDERSTANDING,
        base_model="distilbert-base-uncased",
    )

    train_examples = [{"input": f"query {i}"} for i in range(10)]
    val_examples = [{"input": f"val {i}"} for i in range(5)]

    config = {"epochs": 2, "max_duration_seconds": 60}
    res = await backend.run_job(
        job=dummy_job,
        config=config,
        train_examples=train_examples,
        val_examples=val_examples,
    )

    assert res.success is True
    assert res.artifact_path is not None
    assert res.checksum is not None
    assert res.file_size_bytes > 0
    assert res.metrics["epochs_completed"] == 2
    assert "val_accuracy" in res.metrics
    assert len(res.logs) >= 3


@pytest.mark.asyncio
async def test_mock_training_backend_cancellation() -> None:
    backend = MockLocalTrainingBackend(artifact_dir="tests/test_artifacts")

    dummy_job = TrainingJob(
        id=uuid.uuid4(),
        job_name="cancel_test_job",
        task=ModelType.OPPORTUNITY_EXTRACTION,
        base_model="llama-3-8b",
    )

    # Immediately cancel before running
    await backend.cancel_job(str(dummy_job.id))

    res = await backend.run_job(
        job=dummy_job,
        config={"epochs": 5},
        train_examples=[{"input": "a"}],
        val_examples=[{"input": "b"}],
    )

    assert res.success is False
    assert "cancelled" in (res.error_message or "").lower()


@pytest.mark.asyncio
async def test_training_service_job_lifecycle(test_db_session: AsyncSession) -> None:
    service = TrainingService(backend=MockLocalTrainingBackend(artifact_dir="tests/test_artifacts"))

    payload = TrainingJobCreate(
        job_name="reranker_finetune_run1",
        task=ModelType.RERANKING,
        base_model="bge-reranker-large",
        training_backend="LOCAL",
        hyperparameters=TrainingHyperparameters(epochs=2),
        resource_limits=ResourceLimits(max_duration_seconds=30),
    )

    job = await service.create_and_start_job(db=test_db_session, payload=payload)

    assert job.status == TrainingJobStatus.COMPLETED
    assert job.metrics["epochs_completed"] == 2
    assert len(job.artifacts) == 1
    assert job.artifacts[0].checksum != ""

    # Test get_job and list_jobs
    fetched = await service.get_job(test_db_session, job.id)
    assert fetched is not None
    assert fetched.job_name == "reranker_finetune_run1"

    jobs_list = await service.list_jobs(test_db_session, task=ModelType.RERANKING)
    assert len(jobs_list) >= 1


@pytest.mark.asyncio
async def test_training_api_endpoints(
    client: AsyncClient,
    test_db_session: AsyncSession,
) -> None:
    admin_user = User(
        id=uuid.UUID("00000000-0000-0000-0000-000000000099"),
        email="admin_trainer@example.com",
        role=UserRole.ADMIN,
        is_active=True,
    )
    test_db_session.add(admin_user)
    await test_db_session.commit()

    if hasattr(client, "_transport") and hasattr(client._transport, "app"):
        client._transport.app.dependency_overrides[get_current_dev_user] = lambda: admin_user

    # 1. Create training job via API
    payload = {
        "job_name": "api_trained_query_model",
        "task": "QUERY_UNDERSTANDING",
        "base_model": "bert-base-uncased",
        "training_backend": "LOCAL",
        "hyperparameters": {"epochs": 1},
        "resource_limits": {"max_duration_seconds": 60},
    }

    response = await client.post("/api/v1/training/jobs", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["job_name"] == "api_trained_query_model"
    assert data["status"] == "COMPLETED"
    job_id = data["id"]

    # 2. Get training job details
    get_res = await client.get(f"/api/v1/training/jobs/{job_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == job_id

    # 3. List training jobs
    list_res = await client.get("/api/v1/training/jobs?task=QUERY_UNDERSTANDING")
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1
