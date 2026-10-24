"""Tests verifying the strict boundary between unknown/unmentioned and negative facts."""

import pytest

from app.opportunities.extraction.engine import OpportunityExtractionEngine
from app.opportunities.extraction.extractors import (
    ApplicationInfoExtractor,
    DeadlineExtractor,
    LanguageRequirementExtractor,
)
from app.opportunities.extraction.schemas import FieldStatus
from tests.fixtures.opportunities.dataset import (
    IELTS_NOT_MENTIONED_HTML,
    MISSING_DEADLINE_HTML,
    NO_IELTS_REQUIRED_HTML,
    ROLLING_DEADLINE_HTML,
    build_synthetic_document,
)


@pytest.mark.asyncio
async def test_ielts_unmentioned_is_not_found():
    """Verifies that an unmentioned language test is NOT_FOUND and not converted to 'no IELTS'."""
    doc = build_synthetic_document(
        title="Quantum Grant",
        html=IELTS_NOT_MENTIONED_HTML,
        url="https://quantum.eu/grant",
        domain="quantum.eu",
    )
    (
        reqs,
        primary_field,
        tests,
        waiver_allowed,
        waiver_conditions,
    ) = LanguageRequirementExtractor.extract_language_requirements(doc)

    # Must be NOT_FOUND
    assert primary_field.status == FieldStatus.NOT_FOUND
    assert primary_field.value is None
    assert len(reqs) == 0
    assert "IELTS" not in tests

    # Through complete engine
    engine = OpportunityExtractionEngine()
    extracted = await engine.extract(doc)
    assert extracted.language_requirement.status == FieldStatus.NOT_FOUND
    assert extracted.language_requirement.value is None
    assert len(extracted.language_requirements) == 0


@pytest.mark.asyncio
async def test_explicit_no_ielts_required():
    """Verifies that an explicit 'No IELTS required' is extracted with is_required=False."""
    doc = build_synthetic_document(
        title="MEXT Scholarship",
        html=NO_IELTS_REQUIRED_HTML,
        url="https://mext.go.jp/scholarship",
        domain="mext.go.jp",
    )
    (
        reqs,
        primary_field,
        tests,
        waiver_allowed,
        waiver_conditions,
    ) = LanguageRequirementExtractor.extract_language_requirements(doc)

    assert primary_field.status == FieldStatus.FOUND
    ielts_req = next((r for r in reqs if r.test_name == "IELTS"), None)
    assert ielts_req is not None
    assert ielts_req.is_required is False
    assert "no ielts required" in ielts_req.evidence.evidence_text.lower()


def test_missing_deadline_vs_rolling():
    """Verifies missing deadline yields NOT_FOUND, while rolling yields is_rolling=True."""
    # 1. Missing deadline
    missing_doc = build_synthetic_document(
        title="Leaders Grant",
        html=MISSING_DEADLINE_HTML,
        url="https://leaders.org/grant",
        domain="leaders.org",
    )
    deadlines, primary, opening, is_rolling = DeadlineExtractor.extract_deadlines(missing_doc)
    assert primary.status == FieldStatus.NOT_FOUND
    assert primary.value is None
    assert is_rolling.value is False

    # 2. Explicit rolling deadline
    rolling_doc = build_synthetic_document(
        title="CERN Internship",
        html=ROLLING_DEADLINE_HTML,
        url="https://cern.ch/openlab",
        domain="cern.ch",
    )
    deadlines, primary, opening, is_rolling = DeadlineExtractor.extract_deadlines(rolling_doc)
    assert is_rolling.status == FieldStatus.FOUND
    assert is_rolling.value is True
    assert primary.value is None


def test_fee_unmentioned_vs_free():
    """Verifies missing fee remains NOT_FOUND rather than assuming free."""
    # When no mention of fee exists
    doc_no_fee = build_synthetic_document(
        title="Leaders Grant",
        html=MISSING_DEADLINE_HTML,
        url="https://leaders.org/grant",
        domain="leaders.org",
    )
    app_url, app_method, is_free, fee_amount = ApplicationInfoExtractor.extract_application_info(
        doc_no_fee
    )
    assert is_free.status == FieldStatus.NOT_FOUND
    assert is_free.value is None
