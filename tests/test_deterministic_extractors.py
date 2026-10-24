"""Tests for deterministic extractors (deadlines, funding, academics, tests, app info)."""

from app.opportunities.extraction.extractors import (
    AcademicRequirementExtractor,
    ApplicationInfoExtractor,
    DeadlineExtractor,
    FundingExtractor,
    LanguageRequirementExtractor,
    SourceTrustAssessor,
)
from app.opportunities.extraction.schemas import (
    FieldStatus,
    FundingPeriod,
    SourceTrustType,
)
from tests.fixtures.opportunities.dataset import (
    COMPLETE_SCHOLARSHIP_HTML,
    EXACT_FUNDING_AMOUNT_HTML,
    MULTIPLE_DEADLINES_HTML,
    PARTIALLY_FUNDED_HTML,
    ROLLING_DEADLINE_HTML,
    build_synthetic_document,
)


def test_deadline_extractor_complete():
    """Tests extracting fixed application and opening dates from text."""
    doc = build_synthetic_document(
        title="DAAD Scholarship",
        html=COMPLETE_SCHOLARSHIP_HTML,
        url="https://daad.de/programme",
        domain="daad.de",
    )
    deadlines, primary, opening, is_rolling = DeadlineExtractor.extract_deadlines(doc)

    assert primary.status == FieldStatus.FOUND
    assert primary.value == "2026-07-31"
    assert primary.evidence is not None
    assert "2026-07-31" in primary.evidence.evidence_text

    assert opening.status == FieldStatus.FOUND
    assert opening.value == "2026-06-01"
    assert is_rolling.value is False


def test_deadline_extractor_rolling():
    """Tests identifying rolling deadlines."""
    doc = build_synthetic_document(
        title="CERN Internship",
        html=ROLLING_DEADLINE_HTML,
        url="https://cern.ch/internship",
        domain="cern.ch",
    )
    deadlines, primary, opening, is_rolling = DeadlineExtractor.extract_deadlines(doc)

    assert is_rolling.status == FieldStatus.FOUND
    assert is_rolling.value is True
    assert primary.value is None


def test_deadline_extractor_table_multiple():
    """Tests extracting multiple deadline stages from an HTML table."""
    doc = build_synthetic_document(
        title="Oxford Fellowship",
        html=MULTIPLE_DEADLINES_HTML,
        url="https://ox.ac.uk/fellowship",
        domain="ox.ac.uk",
    )
    deadlines, primary, opening, is_rolling = DeadlineExtractor.extract_deadlines(doc)

    assert len(deadlines) >= 2
    dates = [d.deadline_date for d in deadlines]
    assert "2026-01-20" in dates


def test_funding_extractor_fully_funded():
    """Tests extracting fully funded status, stipend, and benefits."""
    doc = build_synthetic_document(
        title="DAAD Helmut Schmidt",
        html=COMPLETE_SCHOLARSHIP_HTML,
        url="https://daad.de/helmut",
        domain="daad.de",
    )
    funding_type, funding_amount, benefits = FundingExtractor.extract_funding(doc)

    assert funding_type.status == FieldStatus.FOUND
    assert funding_type.value == "Fully Funded"
    assert funding_amount.status == FieldStatus.FOUND
    assert funding_amount.value.amount == 934.0
    assert funding_amount.value.currency == "EUR"
    assert funding_amount.value.period == FundingPeriod.MONTHLY

    assert "Travel Allowance" in benefits
    assert "Health Insurance" in benefits


def test_funding_extractor_partially_funded():
    """Tests extracting partially funded tuition waiver."""
    doc = build_synthetic_document(
        title="Melbourne Fee Remission",
        html=PARTIALLY_FUNDED_HTML,
        url="https://unimelb.edu.au/fee",
        domain="unimelb.edu.au",
    )
    funding_type, funding_amount, benefits = FundingExtractor.extract_funding(doc)

    assert funding_type.status == FieldStatus.FOUND
    assert funding_type.value == "Partially Funded"
    assert "Tuition Waiver" in benefits


def test_funding_extractor_exact_currency_stipend():
    """Tests SGD currency and monthly stipend."""
    doc = build_synthetic_document(
        title="SINGA Award",
        html=EXACT_FUNDING_AMOUNT_HTML,
        url="https://a-star.edu.sg/singa",
        domain="a-star.edu.sg",
    )
    funding_type, funding_amount, benefits = FundingExtractor.extract_funding(doc)

    assert funding_amount.status == FieldStatus.FOUND
    assert funding_amount.value.amount == 2700.0
    assert funding_amount.value.currency == "SGD"
    assert funding_amount.value.period == FundingPeriod.MONTHLY


def test_academic_requirement_extractor():
    """Tests extracting degree, minimum CGPA, and percentage."""
    doc = build_synthetic_document(
        title="DAAD Programme",
        html=COMPLETE_SCHOLARSHIP_HTML,
        url="https://daad.de/programme",
        domain="daad.de",
    )
    (
        reqs,
        degree_req,
        gpa_field,
        pct_field,
        degree_levels,
        fields,
    ) = AcademicRequirementExtractor.extract_academic_requirements(doc)

    assert gpa_field.status == FieldStatus.FOUND
    assert gpa_field.value == 3.2

    assert pct_field.status == FieldStatus.FOUND
    assert pct_field.value == 75.0

    assert "Bachelor's" in degree_levels
    assert "Master's" in degree_levels


def test_language_requirement_extractor():
    """Tests IELTS and TOEFL extraction, score cutoff, and waiver clause."""
    doc = build_synthetic_document(
        title="DAAD Programme",
        html=COMPLETE_SCHOLARSHIP_HTML,
        url="https://daad.de/programme",
        domain="daad.de",
    )
    (
        reqs,
        primary_field,
        tests,
        waiver_allowed,
        waiver_conditions,
    ) = LanguageRequirementExtractor.extract_language_requirements(doc)

    assert primary_field.status == FieldStatus.FOUND
    assert "IELTS" in tests
    assert waiver_allowed.value is True
    assert waiver_conditions.value is not None

    ielts_req = next((r for r in reqs if r.test_name == "IELTS"), None)
    assert ielts_req is not None
    assert ielts_req.minimum_score == "6.5"
    assert ielts_req.waiver_allowed is True


def test_application_info_extractor():
    """Tests application URL and application fee ($0 free)."""
    doc = build_synthetic_document(
        title="DAAD Programme",
        html=COMPLETE_SCHOLARSHIP_HTML,
        url="https://daad.de/programme",
        domain="daad.de",
    )
    (
        app_url,
        app_method,
        is_free,
        fee_amount,
    ) = ApplicationInfoExtractor.extract_application_info(doc)

    assert app_url.status == FieldStatus.FOUND
    assert "https://daad.de/apply" in app_url.value
    assert is_free.status == FieldStatus.FOUND
    assert is_free.value is True


def test_source_trust_assessor():
    """Tests distinguishing official institutions from third-party blogs/aggregators."""
    edu_trust, edu_score = SourceTrustAssessor.assess_trust("https://mit.edu/admissions", "mit.edu")
    assert edu_trust == SourceTrustType.OFFICIAL
    assert edu_score >= 0.9

    gov_trust, gov_score = SourceTrustAssessor.assess_trust(
        "https://state.gov/fulbright", "state.gov"
    )
    assert gov_trust == SourceTrustType.OFFICIAL
    assert gov_score >= 0.9

    agg_trust, agg_score = SourceTrustAssessor.assess_trust(
        "https://scholarshipsads.com/daad", "scholarshipsads.com"
    )
    assert agg_trust == SourceTrustType.DIRECTORY
    assert agg_score < 0.6
