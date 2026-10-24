"""Tests for privacy sanitizer, user event logging, and system health analytics."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.models.event import EventType
from app.analytics.schemas.event import UserEventCreate
from app.analytics.security.privacy_sanitizer import PrivacyPreservingAnalytics
from app.analytics.services.analytics_service import AnalyticsService
from app.api.dependencies import get_current_dev_user
from app.models.user import User, UserRole


def test_privacy_sanitizer_redacts_credentials_and_tokens() -> None:
    raw_payload = {
        "user_query": "Find scholarships for student@university.edu",
        "auth": "Bearer secret_jwt_token_12345.xyz",
        "api_key": "AIzaSyD-9876543210",
        "password": "SuperSecretPassword123!",
        "client_secret": "abcdef123456",
        "nested": {
            "token": "tok_live_12345",
            "safe_field": "Scholarship info",
            "contact_email": "dean@harvard.edu",
        },
        "safe_list": ["Computer Science", "Engineering", "info@mit.edu"],
    }

    sanitized = PrivacyPreservingAnalytics.sanitize_metadata(raw_payload)

    # Key-based secret redaction
    assert sanitized["api_key"] == "[REDACTED_SECRET]"
    assert sanitized["password"] == "[REDACTED_SECRET]"
    assert sanitized["client_secret"] == "[REDACTED_SECRET]"
    assert sanitized["nested"]["token"] == "[REDACTED_SECRET]"

    # Pattern-based text redaction (Bearer & Email)
    assert "[REDACTED_TOKEN]" in sanitized["auth"]
    assert "[REDACTED_EMAIL]" in sanitized["user_query"]
    assert "student@university.edu" not in sanitized["user_query"]
    assert "[REDACTED_EMAIL]" in sanitized["nested"]["contact_email"]
    assert "[REDACTED_EMAIL]" in sanitized["safe_list"][2]

    # Non-sensitive fields preserved
    assert sanitized["nested"]["safe_field"] == "Scholarship info"
    assert sanitized["safe_list"][0] == "Computer Science"


@pytest.mark.asyncio
async def test_analytics_service_tracks_sanitized_event(test_db_session: AsyncSession) -> None:
    service = AnalyticsService()
    user_id = uuid.uuid4()

    event = await service.track_event(
        test_db_session,
        user_id=user_id,
        event=UserEventCreate(
            event_type=EventType.SEARCH_STARTED,
            entity_type="SEARCH_SESSION",
            entity_id="session_101",
            metadata_json={
                "query": "Full funding in UK",
                "bearer_token": "Bearer abc.def.ghi",
            },
        ),
    )

    assert event.id is not None
    assert event.event_type == EventType.SEARCH_STARTED
    assert event.metadata_json["bearer_token"] == "[REDACTED_SECRET]"


@pytest.mark.asyncio
async def test_analytics_overview_and_endpoints(
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

    # Post event
    post_res = await client.post(
        "/api/v1/analytics/events",
        json={
            "event_type": "OPPORTUNITY_VIEWED",
            "entity_type": "OPPORTUNITY",
            "entity_id": "opp_999",
            "metadata_json": {"source": "web"},
        },
    )
    assert post_res.status_code == 201
    assert post_res.json()["event_type"] == "OPPORTUNITY_VIEWED"

    # Get overview
    overview_res = await client.get("/api/v1/analytics/overview")
    assert overview_res.status_code == 200
    data = overview_res.json()
    assert "total_events" in data
    assert data["total_events"] >= 1
    assert "search_success_rate" in data
    assert "feedback_counts" in data
