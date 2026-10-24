"""Tests for role-based access control, endpoint security, and safety guardrails."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_dev_user
from app.learning.schemas.learning import ExperimentCreate
from app.learning.services.learning_service import LearningService
from app.models.user import User, UserRole


@pytest.mark.asyncio
async def test_standard_user_forbidden_from_review_queue(
    client: AsyncClient,
    test_db_session: AsyncSession,
) -> None:
    regular_user = User(
        id=uuid.uuid4(),
        email="developer@example.com",
        role=UserRole.USER,
        is_active=True,
    )
    test_db_session.add(regular_user)
    await test_db_session.commit()

    if hasattr(client, "_transport") and hasattr(client._transport, "app"):
        client._transport.app.dependency_overrides[get_current_dev_user] = lambda: regular_user

    res = await client.get("/api/v1/review/queue")
    assert res.status_code == 403
    assert "Reviewer authorization required" in res.json()["detail"]


@pytest.mark.asyncio
async def test_reviewer_forbidden_from_admin_endpoints(
    client: AsyncClient,
    test_db_session: AsyncSession,
) -> None:
    reviewer_user = User(
        id=uuid.uuid4(),
        email="developer@example.com",
        role=UserRole.REVIEWER,
        is_active=True,
    )
    test_db_session.add(reviewer_user)
    await test_db_session.commit()

    if hasattr(client, "_transport") and hasattr(client._transport, "app"):
        client._transport.app.dependency_overrides[get_current_dev_user] = lambda: reviewer_user

    # Reviewer can view datasets
    get_res = await client.get("/api/v1/evaluation/datasets")
    assert get_res.status_code == 200

    # But reviewer cannot define new datasets (admin only)
    post_res = await client.post(
        "/api/v1/evaluation/datasets",
        json={"name": "Forbidden Benchmark", "task_type": "EXTRACTION"},
    )
    assert post_res.status_code == 403
    assert "Admin authorization required" in post_res.json()["detail"]


@pytest.mark.asyncio
async def test_eligibility_experimentation_safety_gate(test_db_session: AsyncSession) -> None:
    learning_service = LearningService()

    # Attempting to run an A/B experiment on eligibility criteria violates platform safety policy
    with pytest.raises(ValueError) as exc_info:
        await learning_service.create_experiment(
            test_db_session,
            payload=ExperimentCreate(
                name="Eligibility relaxation test",
                description="Testing whether relaxing GPA increases conversion",
                hypothesis="Lowering GPA threshold will increase engagement",
                target_metric="ELIGIBILITY_RATE",
            ),
        )

    assert "forbidden by safety policy" in str(exc_info.value)
