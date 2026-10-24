"""Tests for human review queue, reviewer assignment, and human corrections."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_dev_user
from app.models.user import User, UserRole
from app.review.models.review_item import ReviewCategory, ReviewStatus
from app.review.schemas.review import (
    ReviewItemCreate,
    ReviewResolutionCreate,
)
from app.review.services.review_service import ReviewService


@pytest.mark.asyncio
async def test_review_service_lifecycle_with_corrections(
    test_db_session: AsyncSession,
) -> None:
    service = ReviewService()
    reviewer_id = uuid.uuid4()

    # Create review item
    item = await service.create_review_item(
        test_db_session,
        payload=ReviewItemCreate(
            category=ReviewCategory.OPPORTUNITY_EXTRACTION,
            entity_id="opp_review_100",
            reason="Deadline is extracted as 2024 instead of 2026",
            evidence_text="Application portal says deadline: Dec 15, 2026",
            current_system_output={"deadline": "2024-12-15", "amount": "$10,000"},
            priority="HIGH",
        ),
    )
    assert item.id is not None
    assert item.status == ReviewStatus.PENDING

    # Assign to reviewer
    assigned = await service.assign_item(test_db_session, item_id=item.id, reviewer_id=reviewer_id)
    assert assigned is not None
    assert assigned.status == ReviewStatus.IN_REVIEW
    assert assigned.assigned_to == reviewer_id

    # Resolve with correction
    resolution = ReviewResolutionCreate(
        status=ReviewStatus.CORRECTED,
        resolution_notes="Verified against live official admissions portal.",
        evidence="https://portal.university.edu/scholarships",
        corrected_value={"deadline": "2026-12-15", "amount": "$10,000"},
    )

    resolved = await service.resolve_item(
        test_db_session,
        item_id=item.id,
        reviewer_id=reviewer_id,
        payload=resolution,
    )
    assert resolved.status == ReviewStatus.CORRECTED

    # Re-fetch item to verify eager-loaded corrections
    fetched = await service.get_review_item(test_db_session, item_id=item.id)
    assert fetched is not None
    assert len(fetched.corrections) == 1
    corr = fetched.corrections[0]
    assert corr.original_value["deadline"] == "2024-12-15"
    assert corr.corrected_value["deadline"] == "2026-12-15"
    assert corr.reviewer_id == reviewer_id


@pytest.mark.asyncio
async def test_review_api_endpoints(
    client: AsyncClient,
    test_db_session: AsyncSession,
) -> None:
    reviewer = User(
        id=uuid.uuid4(),
        email="developer@example.com",
        role=UserRole.REVIEWER,
        is_active=True,
    )
    test_db_session.add(reviewer)
    await test_db_session.commit()

    if hasattr(client, "_transport") and hasattr(client._transport, "app"):
        client._transport.app.dependency_overrides[get_current_dev_user] = lambda: reviewer

    service = ReviewService()
    item = await service.create_review_item(
        test_db_session,
        payload=ReviewItemCreate(
            category=ReviewCategory.ELIGIBILITY,
            entity_id="elig_review_200",
            reason="Citizenship requirement conflict",
            evidence_text="Open to all international students.",
            current_system_output={"eligible": False},
        ),
    )

    # List queue
    get_res = await client.get("/api/v1/review/queue")
    assert get_res.status_code == 200
    items = get_res.json()
    assert any(i["id"] == str(item.id) for i in items)

    # Assign item
    assign_res = await client.post(f"/api/v1/review/queue/{item.id}/assign")
    assert assign_res.status_code == 200
    assert assign_res.json()["status"] == "IN_REVIEW"

    # Resolve item as VERIFIED
    resolve_res = await client.post(
        f"/api/v1/review/queue/{item.id}/resolve",
        json={
            "status": "VERIFIED",
            "resolution_notes": "Verified system was correct: requires citizenship.",
        },
    )
    assert resolve_res.status_code == 200
    assert resolve_res.json()["status"] == "VERIFIED"
