"""Unit tests for change detection and semantic diffing."""

import uuid
from datetime import date

from app.monitoring.models.change_event import OpportunityChangeType
from app.monitoring.services.change_detection_service import ChangeDetectionService


def test_change_detection_boilerplate_rejection():
    """Verify changes in copyright, analytics, or cookie policies are rejected as no-op."""
    detector = ChangeDetectionService()

    base_text = "The Global Scholars Program awards $20,000 for Master's study in STEM fields."
    text_v1 = f"{base_text}\n© 2024 Global Education. All rights reserved. Cookie policy."
    text_v2 = f"{base_text}\n© 2025 Global Education. All rights reserved. Last modified: Jan 2025."

    is_changed = detector.detect_content_changes(text_v1, text_v2)
    assert is_changed is False, (
        "Boilerplate/copyright update should not be detected as substantive change"
    )


def test_change_detection_substantive_text_change():
    """Verify genuine text updates are detected."""
    detector = ChangeDetectionService()

    text_v1 = "The scholarship awards a partial stipend of $5,000."
    text_v2 = "The scholarship awards a fully funded stipend of $25,000."

    is_changed = detector.detect_content_changes(text_v1, text_v2)
    assert is_changed is True


def test_structured_deadline_extended():
    """Verify deadline extension generates DEADLINE_EXTENDED with HIGH priority."""
    detector = ChangeDetectionService()
    opp_id = uuid.uuid4()

    old_data = {"deadline": "2026-10-01", "status": "active"}
    new_data = {"deadline": "2026-11-15", "status": "active"}

    events = detector.detect_structured_changes(old_data, new_data, opp_id)
    assert len(events) == 1
    ev = events[0]
    assert ev.change_type == OpportunityChangeType.DEADLINE_EXTENDED
    assert ev.notification_priority == "HIGH"
    assert ev.effective_date == date(2026, 11, 15)
    assert ev.verified is True


def test_structured_deadline_shortened():
    """Verify deadline shortened generates DEADLINE_SHORTENED with URGENT priority."""
    detector = ChangeDetectionService()
    opp_id = uuid.uuid4()

    old_data = {"deadline": "2026-12-01", "status": "active"}
    new_data = {"deadline": "2026-11-01", "status": "active"}

    events = detector.detect_structured_changes(old_data, new_data, opp_id)
    assert len(events) == 1
    ev = events[0]
    assert ev.change_type == OpportunityChangeType.DEADLINE_SHORTENED
    assert ev.notification_priority == "URGENT"


def test_structured_program_closure():
    """Verify transition from active to closed generates PROGRAM_CLOSED with URGENT priority."""
    detector = ChangeDetectionService()
    opp_id = uuid.uuid4()

    old_data = {"status": "active"}
    new_data = {"status": "closed"}

    events = detector.detect_structured_changes(old_data, new_data, opp_id)
    assert len(events) == 1
    ev = events[0]
    assert ev.change_type == OpportunityChangeType.PROGRAM_CLOSED
    assert ev.notification_priority == "URGENT"


def test_structured_funding_and_requirements():
    """Verify funding and test requirement changes produce appropriate change events."""
    detector = ChangeDetectionService()
    opp_id = uuid.uuid4()

    old_data = {
        "funding_type": "Partial",
        "funding_amount": "$10,000",
        "english_tests": ["TOEFL"],
        "degree_levels": ["Master's"],
    }
    new_data = {
        "funding_type": "Full",
        "funding_amount": "$35,000",
        "english_tests": ["IELTS", "TOEFL"],
        "degree_levels": ["Master's", "PhD"],
    }

    events = detector.detect_structured_changes(old_data, new_data, opp_id)
    types = {ev.change_type for ev in events}
    assert OpportunityChangeType.FUNDING_CHANGED in types
    assert OpportunityChangeType.TEST_REQUIREMENT_CHANGED in types
    assert OpportunityChangeType.DEGREE_REQUIREMENT_CHANGED in types
