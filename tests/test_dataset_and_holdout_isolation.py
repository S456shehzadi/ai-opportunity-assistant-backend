"""Tests for benchmark dataset versioning and strict holdout split isolation."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_dev_user
from app.evaluation.models.dataset import DatasetQualityStatus, SplitType
from app.evaluation.schemas.evaluation import (
    DatasetCreate,
    DatasetExampleInput,
    DatasetVersionCreate,
)
from app.evaluation.services.evaluation_service import EvaluationService
from app.models.user import User, UserRole


@pytest.mark.asyncio
async def test_dataset_versioning_and_holdout_isolation(
    test_db_session: AsyncSession,
) -> None:
    service = EvaluationService()

    # Create dataset
    dataset = await service.create_dataset(
        test_db_session,
        payload=DatasetCreate(
            name="Opportunity Extraction Benchmark",
            task_type="EXTRACTION",
            description="Gold standard opportunity extraction test cases.",
        ),
    )
    assert dataset.id is not None

    # Create version with TRAIN, TEST, and HOLDOUT examples
    examples = [
        DatasetExampleInput(
            split=SplitType.TRAIN,
            input_data={"html": "<html>Scholarship $5,000</html>"},
            expected_output={"amount": 5000},
        ),
        DatasetExampleInput(
            split=SplitType.TEST,
            input_data={"html": "<html>Fellowship $10,000</html>"},
            expected_output={"amount": 10000},
        ),
        DatasetExampleInput(
            split=SplitType.HOLDOUT,
            input_data={"html": "<html>Grant $25,000</html>"},
            expected_output={"amount": 25000},
        ),
    ]

    version = await service.create_dataset_version(
        test_db_session,
        dataset_id=dataset.id,
        payload=DatasetVersionCreate(
            version_tag="v1.0.0",
            quality_status=DatasetQualityStatus.VERIFIED,
            examples=examples,
        ),
    )

    assert version.example_count == 3
    assert version.split_counts[SplitType.TRAIN.value] == 1
    assert version.split_counts[SplitType.TEST.value] == 1
    assert version.split_counts[SplitType.HOLDOUT.value] == 1

    # Standard query excludes HOLDOUT
    standard_examples = await service.get_dataset_examples(
        test_db_session,
        version_id=version.id,
        allow_holdout=False,
    )
    assert len(standard_examples) == 2
    assert all(e.split != SplitType.HOLDOUT for e in standard_examples)

    # Specific TEST split
    test_examples = await service.get_dataset_examples(
        test_db_session,
        version_id=version.id,
        split=SplitType.TEST,
        allow_holdout=False,
    )
    assert len(test_examples) == 1
    assert test_examples[0].expected_output["amount"] == 10000

    # Strict isolation: attempting to access HOLDOUT without authorization raises PermissionError
    with pytest.raises(PermissionError) as exc_info:
        await service.get_dataset_examples(
            test_db_session,
            version_id=version.id,
            split=SplitType.HOLDOUT,
            allow_holdout=False,
        )
    assert "HOLDOUT split is restricted" in str(exc_info.value)

    # Authorized holdout access succeeds
    holdout_examples = await service.get_dataset_examples(
        test_db_session,
        version_id=version.id,
        split=SplitType.HOLDOUT,
        allow_holdout=True,
    )
    assert len(holdout_examples) == 1
    assert holdout_examples[0].expected_output["amount"] == 25000


@pytest.mark.asyncio
async def test_dataset_api_endpoints(
    client: AsyncClient,
    test_db_session: AsyncSession,
) -> None:
    admin_user = User(
        id=uuid.uuid4(),
        email="developer@example.com",
        role=UserRole.ADMIN,
        is_active=True,
    )
    test_db_session.add(admin_user)
    await test_db_session.commit()

    if hasattr(client, "_transport") and hasattr(client._transport, "app"):
        client._transport.app.dependency_overrides[get_current_dev_user] = lambda: admin_user

    # POST /api/v1/evaluation/datasets
    create_res = await client.post(
        "/api/v1/evaluation/datasets",
        json={
            "name": "Ranking Gold Benchmark",
            "task_type": "RANKING",
            "description": "Standard NDCG evaluation set",
        },
    )
    assert create_res.status_code == 201
    dataset_id = create_res.json()["id"]

    # POST /api/v1/evaluation/datasets/{id}/versions
    version_res = await client.post(
        f"/api/v1/evaluation/datasets/{dataset_id}/versions",
        json={
            "version_tag": "v1.0-alpha",
            "examples": [
                {
                    "split": "TEST",
                    "input_data": {"query": "Machine learning fellowship"},
                    "expected_output": {"relevant_ids": ["opp_ml_1"]},
                }
            ],
            "quality_status": "VERIFIED",
        },
    )
    assert version_res.status_code == 201
    assert version_res.json()["example_count"] == 1

    # GET /api/v1/evaluation/datasets
    list_res = await client.get("/api/v1/evaluation/datasets")
    assert list_res.status_code == 200
    datasets = list_res.json()
    assert any(d["id"] == dataset_id for d in datasets)
