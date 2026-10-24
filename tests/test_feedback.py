"""Tests for user feedback submission, routing, and error clustering."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_dev_user
from app.feedback.models.feedback import FeedbackTargetType, FeedbackType
from app.feedback.schemas.feedback import FeedbackCreate
from app.feedback.services.feedback_service import FeedbackService
from app.models.user import User, UserRole
from app.review.models.review_item import ReviewCategory, ReviewStatus


@pytest.mark.asyncio
async def test_submit_helpful_feedback_service(test_db_session: AsyncSession) -> None:
    service = FeedbackService()
    user_id = uuid.uuid4()

    payload = FeedbackCreate(
        target_type=FeedbackTargetType.OPPORTUNITY,
        target_id="opp_123",
        feedback_type=FeedbackType.HELPFUL,
        context_snapshot={"title": "Tech Scholarship"},
    )

    record = await service.submit_feedback(test_db_session, user_id=user_id, payload=payload)
    assert record.id is not None
    assert record.user_id == user_id
    assert record.feedback_type == FeedbackType.HELPFUL
    assert record.status == "NEW"

    # Query for target
    items = await service.get_feedback_for_target(
        test_db_session,
        target_type=FeedbackTargetType.OPPORTUNITY,
        target_id="opp_123",
    )
    assert len(items) == 1
    assert items[0].id == record.id


@pytest.mark.asyncio
async def test_submit_wrong_eligibility_feedback_creates_review_and_cluster(
    test_db_session: AsyncSession,
) -> None:
    service = FeedbackService()
    user_id = uuid.uuid4()

    payload = FeedbackCreate(
        target_type=FeedbackTargetType.ELIGIBILITY,
        target_id="elig_456",
        feedback_type=FeedbackType.WRONG_ELIGIBILITY,
        reason="Minimum GPA is actually 3.5, not 3.0",
        comment="Official university catalog says 3.5 is required.",
        context_snapshot={"domain": "example.edu", "opportunity_id": "opp_789"},
    )

    record = await service.submit_feedback(test_db_session, user_id=user_id, payload=payload)
    assert record.id is not None

    # Verify review queue item was created
    queue_items = await service.review_service.list_review_items(
        test_db_session,
        category=ReviewCategory.ELIGIBILITY,
    )
    assert len(queue_items) >= 1
    item = next(i for i in queue_items if i.entity_id == "elig_456")
    assert item.priority == "HIGH"
    assert item.status == ReviewStatus.PENDING
    assert item.user_feedback_id == record.id
    assert "WRONG_ELIGIBILITY" in item.reason


@pytest.mark.asyncio
async def test_feedback_api_endpoints(
    client: AsyncClient,
    test_db_session: AsyncSession,
) -> None:
    # Ensure reviewer dev user for querying feedback
    dev_user = User(
        id=uuid.uuid4(),
        email="developer@example.com",
        role=UserRole.REVIEWER,
        is_active=True,
    )
    test_db_session.add(dev_user)
    await test_db_session.commit()

    if hasattr(client, "_transport") and hasattr(client._transport, "app"):
        client._transport.app.dependency_overrides[get_current_dev_user] = lambda: dev_user

    res = await client.post(
        "/api/v1/feedback",
        json={
            "target_type": "OPPORTUNITY",
            "target_id": "opp_api_1",
            "feedback_type": "OUTDATED",
            "reason": "Deadline passed last month",
            "comment": "Check updated site",
            "context_snapshot": {"url": "https://example.org/opp"},
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["target_id"] == "opp_api_1"
    assert data["feedback_type"] == "OUTDATED"

    # Query feedback API
    get_res = await client.get(
        "/api/v1/feedback",
        params={"target_type": "OPPORTUNITY", "target_id": "opp_api_1"},
    )
    assert get_res.status_code == 200
    list_data = get_res.json()
    assert len(list_data) >= 1
    assert list_data[0]["target_id"] == "opp_api_1"
