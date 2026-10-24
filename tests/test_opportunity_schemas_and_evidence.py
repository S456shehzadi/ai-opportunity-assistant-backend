"""Tests for opportunity extraction schemas and evidence grounding."""

from app.opportunities.extraction.evidence import Evidence, EvidenceType, EvidenceValidator
from app.opportunities.extraction.schemas import (
    ExtractedField,
    ExtractedOpportunity,
    FieldStatus,
    FundingPeriod,
    OpportunityCategory,
    SourceTrustType,
    StructuredFundingAmount,
)


def test_extracted_field_found_and_not_found():
    """Tests ExtractedField factory methods and statuses."""
    not_found = ExtractedField[str].not_found()
    assert not_found.status == FieldStatus.NOT_FOUND
    assert not_found.value is None
    assert not_found.confidence == 0.0
    assert not_found.evidence is None

    evidence = Evidence(
        source_url="https://example.edu/scholarship",
        field_name="title",
        evidence_text="Excellence Scholarship Program",
        evidence_type=EvidenceType.DIRECT_TEXT,
        confidence=0.95,
    )
    found = ExtractedField[str].found(
        value="Excellence Scholarship Program",
        evidence=evidence,
        confidence=0.95,
    )
    assert found.status == FieldStatus.FOUND
    assert found.value == "Excellence Scholarship Program"
    assert found.confidence == 0.95
    assert found.evidence is not None
    assert found.evidence.field_name == "title"


def test_evidence_validator_presence_and_text():
    """Tests EvidenceValidator verifying quotes in source text."""
    doc_text = "The university offers a €1,500 monthly stipend for international students."
    valid_ev = Evidence(
        source_url="https://example.edu",
        field_name="stipend",
        evidence_text="€1,500 monthly stipend",
        evidence_type=EvidenceType.DIRECT_TEXT,
    )
    assert EvidenceValidator.verify_evidence(valid_ev, doc_text) is True

    # Hallucinated evidence snippet not in text
    fake_ev = Evidence(
        source_url="https://example.edu",
        field_name="stipend",
        evidence_text="$5,000 monthly stipend",
        evidence_type=EvidenceType.DIRECT_TEXT,
    )
    assert EvidenceValidator.verify_evidence(fake_ev, doc_text) is False

    # Empty evidence
    empty_ev = Evidence(
        source_url="https://example.edu",
        field_name="stipend",
        evidence_text="",
        evidence_type=EvidenceType.DIRECT_TEXT,
    )
    assert EvidenceValidator.verify_evidence(empty_ev, doc_text) is False


def test_structured_funding_amount():
    """Tests StructuredFundingAmount serialization and periods."""
    amount = StructuredFundingAmount(
        amount=1200.0,
        currency="EUR",
        period=FundingPeriod.MONTHLY,
        amount_type="EXACT",
    )
    assert amount.amount == 1200.0
    assert amount.currency == "EUR"
    assert amount.period == FundingPeriod.MONTHLY


def test_extracted_opportunity_minimal_construction():
    """Tests constructing a valid minimal ExtractedOpportunity."""
    opp = ExtractedOpportunity(
        canonical_key="opp_test123",
        title="Global Masters Scholarship",
        organization="Oxford University",
        category=OpportunityCategory.SCHOLARSHIP,
        official_source_url="https://ox.ac.uk/scholarship",
        source_type=SourceTrustType.OFFICIAL,
        source_trust_score=1.0,
        source_documents=["https://ox.ac.uk/scholarship"],
    )
    assert opp.canonical_key == "opp_test123"
    assert opp.title == "Global Masters Scholarship"
    assert opp.category == OpportunityCategory.SCHOLARSHIP
    assert opp.source_type == SourceTrustType.OFFICIAL
    assert opp.funding_type == "Unknown"
    assert opp.deadlines == []
