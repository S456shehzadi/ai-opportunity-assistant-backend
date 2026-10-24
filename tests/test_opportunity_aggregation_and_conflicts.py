"""Tests for multi-page aggregation, conflict detection, and confidence calculation."""

import pytest

from app.opportunities.extraction.aggregation import OpportunityAggregator
from app.opportunities.extraction.confidence import ConfidenceCalculator
from app.opportunities.extraction.conflicts import ConflictDetector
from app.opportunities.extraction.engine import OpportunityExtractionEngine
from app.opportunities.extraction.schemas import FieldStatus
from tests.fixtures.opportunities.dataset import (
    COMPLETE_SCHOLARSHIP_HTML,
    CONFLICTING_SECONDARY_HTML,
    MULTIPAGE_FUNDING_HTML,
    MULTIPAGE_OVERVIEW_HTML,
    build_synthetic_document,
)


@pytest.mark.asyncio
async def test_multipage_aggregation():
    """Tests merging overview and funding pages for a single opportunity."""
    doc_overview = build_synthetic_document(
        title="Rotary Peace Fellowship - Program Overview",
        html=MULTIPAGE_OVERVIEW_HTML,
        url="https://rotary.org/peace-fellowship",
        domain="rotary.org",
    )
    doc_funding = build_synthetic_document(
        title="Rotary Peace Fellowship - Funding & Deadlines",
        html=MULTIPAGE_FUNDING_HTML,
        url="https://rotary.org/peace-fellowship/funding",
        domain="rotary.org",
    )

    engine = OpportunityExtractionEngine()
    opp_overview = await engine.extract(doc_overview)
    opp_funding = await engine.extract(doc_funding)

    # Overview alone has no deadline
    assert opp_overview.application_deadline.status == FieldStatus.NOT_FOUND

    # Funding page has deadline
    assert opp_funding.application_deadline.status == FieldStatus.FOUND

    # Merge them
    merged = OpportunityAggregator.merge([opp_overview, opp_funding])

    # Merged has both title from overview and deadline from funding
    assert "Rotary Peace Fellowship" in merged.title
    assert merged.funding_type == "Fully Funded"
    assert merged.deadline.status == FieldStatus.FOUND
    assert merged.deadline.value == "2026-05-15"
    assert len(merged.source_documents) == 2


@pytest.mark.asyncio
async def test_conflict_detection_and_resolution():
    """Tests resolving conflicting dates/fees in favor of official source with audit notes."""
    official_doc = build_synthetic_document(
        title="DAAD Helmut-Schmidt-Programme",
        html=COMPLETE_SCHOLARSHIP_HTML,
        url="https://daad.de/helmut",
        domain="daad.de",
    )
    secondary_doc = build_synthetic_document(
        title="DAAD Helmut-Schmidt-Programme - Aggregator Info",
        html=CONFLICTING_SECONDARY_HTML,
        url="https://scholarshipsportal.com/daad",
        domain="scholarshipsportal.com",
    )

    engine = OpportunityExtractionEngine()
    opp_official = await engine.extract(official_doc)
    opp_secondary = await engine.extract(secondary_doc)

    conflicts = ConflictDetector.detect_and_resolve_conflicts(opp_official, opp_secondary)
    assert len(conflicts) >= 1

    deadline_conflict = next((c for c in conflicts if c.field_name == "application_deadline"), None)
    assert deadline_conflict is not None
    assert deadline_conflict.official_value == "2026-07-31"
    assert deadline_conflict.secondary_value == "2026-09-30"

    # In merged record, official value should win and conflict should be noted
    merged = OpportunityAggregator.merge([opp_official, opp_secondary])
    assert merged.application_deadline.value == "2026-07-31"
    assert any("[Conflict]" in note for note in merged.notes)


def test_confidence_calculator():
    """Tests extraction confidence calculation across high vs low coverage."""
    doc = build_synthetic_document(
        title="DAAD Helmut-Schmidt-Programme",
        html=COMPLETE_SCHOLARSHIP_HTML,
        url="https://daad.de/helmut",
        domain="daad.de",
    )
    engine = OpportunityExtractionEngine()
    # Synchronously run rule extractor for confidence test
    extractor = engine.model
    # Using pytest run
    import asyncio

    opp = asyncio.run(extractor.extract_opportunity(doc))
    score = ConfidenceCalculator.calculate(opp)

    assert 0.7 <= score <= 1.0
