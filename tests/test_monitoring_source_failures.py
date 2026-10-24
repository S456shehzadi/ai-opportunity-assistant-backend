"""Unit tests for deterministic source failure handling and error isolation."""

import uuid
from unittest.mock import AsyncMock

import pytest

from app.monitoring.models.change_event import OpportunityChangeType
from app.monitoring.services.change_detection_service import ChangeDetectionService
from app.monitoring.services.source_monitor import SourceMonitor
from app.web.models.document import WebDocument


@pytest.mark.asyncio
async def test_http_500_classified_as_source_unavailable():
    """Verify HTTP 500 server error is marked as SOURCE_UNAVAILABLE, never OPPORTUNITY_CLOSED."""
    mock_retrieval = AsyncMock()
    mock_doc = WebDocument(
        original_url="https://example.org/scholarship",
        final_url="https://example.org/scholarship",
        raw_html="",
        clean_text="",
        status_code=500,
        domain="example.org",
        title="500 Internal Server Error",
    )
    mock_retrieval.retrieve_document.return_value = mock_doc

    monitor = SourceMonitor(retrieval_service=mock_retrieval)
    is_avail, code, err = await monitor.check_source_availability("https://example.org/scholarship")

    assert is_avail is False
    assert code == 500
    assert "HTTP 500" in (err or "")


@pytest.mark.asyncio
async def test_connection_timeout_handled_gracefully():
    """Verify connection timeouts return failure without crashing or marking closed."""
    mock_retrieval = AsyncMock()
    mock_retrieval.retrieve_document.side_effect = TimeoutError("Connection timed out after 30s")

    monitor = SourceMonitor(retrieval_service=mock_retrieval)
    is_avail, code, err = await monitor.check_source_availability("https://example.org/scholarship")

    assert is_avail is False
    assert code == 0
    assert "Connection failure" in (err or "")


def test_explicit_closure_text_vs_network_failure():
    """Verify explicit closure text generates PROGRAM_CLOSED, distinct from network failure."""
    detector = ChangeDetectionService()
    opp_id = uuid.uuid4()

    # Network failure or 503 should produce NO change events from structured diff
    old_data = {"status": "active"}
    new_data_failure = {"status": "active"}  # status unchanged
    events_failure = detector.detect_structured_changes(old_data, new_data_failure, opp_id)
    assert len(events_failure) == 0

    # Explicit text saying program closed
    new_data_closed = {"status": "closed"}
    events_closed = detector.detect_structured_changes(old_data, new_data_closed, opp_id)
    assert len(events_closed) == 1
    assert events_closed[0].change_type == OpportunityChangeType.PROGRAM_CLOSED
