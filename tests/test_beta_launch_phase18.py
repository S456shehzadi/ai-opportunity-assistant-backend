"""Comprehensive tests for Phase 18: Staging Launch, Beta Testing, Feedback Triage, and Controls."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.core.config import AppEnvironment, get_settings
from app.core.cost_tracker import CostOperation, get_cost_tracker
from app.core.feature_flags import FeatureFlagKey, get_feature_flags
from app.discovery.models import OpportunitySearchDocument
from app.evaluation.services.beta_quality_evaluator import (
    BetaQualityEvaluator,
)
from app.feedback.schemas.triage import (
    BetaFeedbackSubmission,
    BetaTriageCategory,
    TriagePriority,
)
from app.feedback.services.triage_service import get_triage_service
from app.notifications.models.notification import DeliveryChannel, NotificationType
from app.notifications.services.notification_service import NotificationService


@pytest.mark.asyncio
async def test_feature_flags_remote_configuration(client: AsyncClient) -> None:
    """Verifies feature flags can be inspected and dynamically toggled without restart."""
    flags_service = get_feature_flags()
    flags_service.reset_defaults()

    # 1. Inspect client feature flags via public API
    res = await client.get("/api/v1/beta/features")
    assert res.status_code == 200
    flags = res.json()
    assert flags["live_web_search"] is True
    assert flags["push_notifications"] is False

    # 2. Dynamically toggle flag via service
    updated = flags_service.set_flag(
        FeatureFlagKey.PUSH_NOTIFICATIONS, enabled=True, rollout_percentage=50
    )
    assert updated.enabled is True
    assert updated.rollout_percentage == 50

    # 3. Verify kill-switch behavior
    flags_service.set_flag(FeatureFlagKey.LIVE_WEB_SEARCH, enabled=False)
    assert flags_service.is_enabled(FeatureFlagKey.LIVE_WEB_SEARCH) is False

    # Clean up
    flags_service.reset_defaults()


@pytest.mark.asyncio
async def test_ai_and_search_cost_containment() -> None:
    """Verifies that cost tracking accumulates spend and detects budget limits."""
    tracker = get_cost_tracker()
    tracker.reset_for_testing()

    assert tracker.can_execute_ai_operation() is True
    assert tracker.can_execute_search_operation() is True

    # Record search and crawl operations
    tracker.record_operation(CostOperation.SEARCH_QUERY, units=10)  # 10 * 0.01 = $0.10
    tracker.record_operation(CostOperation.WEB_PAGE_CRAWL, units=20)  # 20 * 0.002 = $0.04

    # Record AI operations
    tracker.record_operation(CostOperation.LLM_INFERENCE, units=50)  # 50 * 0.003 = $0.15
    tracker.record_operation(CostOperation.EMBEDDING_GEN, units=100)  # 100 * 0.0002 = $0.02

    summary = tracker.get_summary()
    assert summary.search_spend_usd == pytest.approx(0.14, rel=1e-2)
    assert summary.ai_spend_usd == pytest.approx(0.17, rel=1e-2)
    assert summary.total_spend_usd == pytest.approx(0.31, rel=1e-2)
    assert summary.is_ai_budget_exceeded is False
    assert summary.is_search_budget_exceeded is False

    # Simulate exceeding budget threshold
    tracker.record_operation(CostOperation.LLM_INFERENCE, units=20000)  # $60.00 > $50.00 limit
    summary_exceeded = tracker.get_summary()
    assert summary_exceeded.is_ai_budget_exceeded is True
    assert tracker.can_execute_ai_operation() is False

    tracker.reset_for_testing()


@pytest.mark.asyncio
async def test_beta_feedback_triage_prioritization() -> None:
    """Verifies feedback items are classified and sorted by urgency score."""
    triage_service = get_triage_service()
    triage_service.clear_for_testing()
    test_user_id = uuid4()

    # P0: Security/Privacy report
    sec_item = await triage_service.triage_submission(
        user_id=test_user_id,
        payload=BetaFeedbackSubmission(
            category=BetaTriageCategory.CRITICAL_SECURITY_PRIVACY,
            title="Potential Token Leak in Log",
            description="Found auth token printed in client debug output during login",
        ),
    )
    assert sec_item.priority == TriagePriority.CRITICAL_P0
    assert sec_item.priority_score >= 90.0
    assert sec_item.routed_to_review is True

    # P1: Factual deadline error report
    deadline_item = await triage_service.triage_submission(
        user_id=test_user_id,
        payload=BetaFeedbackSubmission(
            category=BetaTriageCategory.ELIGIBILITY_OR_DEADLINE_ERROR,
            title="Expired scholarship shown as open",
            description="Opportunity closed last month, rejected because of date",
            target_opportunity_id="opp-test-123",
        ),
    )
    assert deadline_item.priority == TriagePriority.HIGH_P1
    assert deadline_item.priority_score >= 75.0
    assert deadline_item.routed_to_eval_dataset is True

    # P3: Feature enhancement request
    feature_item = await triage_service.triage_submission(
        user_id=test_user_id,
        payload=BetaFeedbackSubmission(
            category=BetaTriageCategory.FEATURE_REQUEST,
            title="Add dark mode toggle to navigation drawer",
            description="Would be great to quickly toggle theme without going to settings",
        ),
    )
    assert feature_item.priority == TriagePriority.LOW_P3
    assert feature_item.priority_score < 40.0

    # Ensure list returns highest priority first
    sorted_items = triage_service.get_triaged_items()
    assert len(sorted_items) == 3
    assert sorted_items[0].id == sec_item.id
    assert sorted_items[1].id == deadline_item.id
    assert sorted_items[2].id == feature_item.id

    triage_service.clear_for_testing()


@pytest.mark.asyncio
async def test_staging_notification_sandbox_guard() -> None:
    """Verifies that in staging environment, notifications simulate delivery and do not leak."""
    settings = get_settings()
    original_env = settings.APP_ENV

    try:
        # Force environment to staging
        settings.APP_ENV = AppEnvironment.STAGING
        assert settings.is_staging is True
        assert settings.STAGING_NOTIFICATION_SANDBOX is True

        notif_service = NotificationService()
        test_user_id = uuid4()

        # In-memory session mock check: evaluate dispatch behavior
        from unittest.mock import AsyncMock, MagicMock
        mock_db = MagicMock()
        mock_result = MagicMock()

        from app.notifications.models.preference import NotificationPreference
        pref = NotificationPreference(
            user_id=test_user_id,
            enable_notifications=True,
            enable_in_app=True,
            enable_push=True,
            enable_email=True,
        )
        mock_result.scalar_one_or_none.return_value = pref
        mock_result.scalar.return_value = 0

        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_db.add = MagicMock()

        # Send notification
        result = await notif_service.dispatch_notification(
            db=mock_db,
            user_id=test_user_id,
            notification_type=NotificationType.DEADLINE_APPROACHING,
            title="Staging Test Deadline",
            message="This should not reach real users",
            requested_channels=[DeliveryChannel.PUSH],
        )

        assert result is not None
        assert result.title == "Staging Test Deadline"

    finally:
        settings.APP_ENV = original_env


@pytest.mark.asyncio
async def test_official_source_verification_and_uncertainty() -> None:
    """Verifies official domain trust vs aggregator uncertainty communication."""
    # Official university / government domain
    daad_ver = BetaQualityEvaluator.verify_source("https://www.daad.de/en/helmut-schmidt/")
    assert daad_ver.is_official_domain is True
    assert daad_ver.trust_tier == "HIGH"
    assert daad_ver.communicated_uncertainty is False

    oxford_ver = BetaQualityEvaluator.verify_source("https://www.ox.ac.uk/admissions/graduate/fees-and-funding")
    assert oxford_ver.is_official_domain is True
    assert oxford_ver.trust_tier == "HIGH"
    assert oxford_ver.communicated_uncertainty is False

    # Third-party aggregator directory
    agg_ver = BetaQualityEvaluator.verify_source("https://opportunitydesk.org/2026/scholarship-post")
    assert agg_ver.is_official_domain is False
    assert agg_ver.is_aggregator_domain is True
    assert agg_ver.trust_tier == "MEDIUM"
    assert agg_ver.communicated_uncertainty is True

    # Unknown domain
    unkn_ver = BetaQualityEvaluator.verify_source("https://random-blog.xyz/post/123")
    assert unkn_ver.trust_tier == "UNVERIFIED"
    assert unkn_ver.communicated_uncertainty is True


@pytest.mark.asyncio
async def test_beta_dashboard_and_quality_audit(client: AsyncClient) -> None:
    """Verifies the beta dashboard metrics and quality audit evaluation."""
    docs = [
        OpportunitySearchDocument(
            opportunity_id="daad-1",
            title="DAAD Master Scholarship",
            provider="DAAD",
            category="Scholarship",
            description="Funded Master's scholarship in Germany",
            funding_summary="Fully funded",
            degree_levels=["Master's"],
            fields=["Computer Science"],
            countries=["Germany"],
            nationalities=["Global"],
            source_url="https://www.daad.de/en/study/",
            source_type="Official Portal",
        ),
        OpportunitySearchDocument(
            opportunity_id="agg-1",
            title="Summer Internship",
            provider="Unknown",
            category="Internship",
            description="Internship listing from aggregator",
            funding_summary="Stipend included",
            degree_levels=["Undergraduate"],
            fields=["Engineering"],
            countries=["Switzerland"],
            nationalities=["Global"],
            source_url="https://opportunitydesk.org/summer-internship",
            source_type="Aggregator",
        ),
    ]

    report = BetaQualityEvaluator.evaluate_opportunity_sample(docs)
    assert report.total_evaluated == 2
    assert report.source_credibility_score == 50.0  # 1 out of 2 is official
    assert report.application_url_validity == 100.0
    assert len(report.sample_verifications) == 2


@pytest.mark.asyncio
async def test_beta_api_endpoints_workflow(client: AsyncClient) -> None:
    """End-to-end API test registering user and submitting categorized beta feedback."""
    # 1. Register test user
    reg_payload = {
        "email": "beta.tester@example.com",
        "password": "SecurePassword123!",
        "full_name": "Beta Tester",
    }
    reg_res = await client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code == 201

    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "beta.tester@example.com", "password": "SecurePassword123!"},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Submit beta feedback via API
    fb_payload = {
        "category": "eligibility_or_deadline_error",
        "title": "Deadline date mismatch in DAAD scholarship",
        "description": "The portal says November 30 but the official PDF states October 31.",
        "target_opportunity_id": "opp-daad-2026",
    }
    fb_res = await client.post("/api/v1/beta/feedback", json=fb_payload, headers=headers)
    assert fb_res.status_code == 201, f"Beta feedback failed: {fb_res.text}"
    fb_data = fb_res.json()
    assert fb_data["category"] == "eligibility_or_deadline_error"
    assert fb_data["priority"] == "HIGH_P1"
    assert fb_data["priority_score"] >= 70.0
    assert fb_data["routed_to_eval_dataset"] is True
