"""Tests for database persistence of Opportunity, OpportunityEvidence, and OpportunityVersion."""

import uuid
from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.opportunity import (
    Opportunity,
    OpportunityCategory,
    OpportunityEvidence,
    OpportunityStatus,
    OpportunityVersion,
)


@pytest.mark.asyncio
async def test_opportunity_evidence_and_version_persistence(
    test_db_session: AsyncSession,
) -> None:
    """Verifies persisting opportunities with canonical keys, evidence citations, and versions."""
    opp_id = uuid.uuid4()
    canonical_key = "opp_daad_masters_scholarship_2026"

    opp = Opportunity(
        id=opp_id,
        canonical_key=canonical_key,
        title="DAAD Master Scholarship",
        organization="DAAD Germany",
        category=OpportunityCategory.SCHOLARSHIP,
        description="Comprehensive master funding.",
        country="Germany",
        eligible_countries=["Global"],
        eligible_nationalities=["Global"],
        degree_levels=["Master's"],
        fields=["All Fields"],
        funding_type="Fully Funded",
        deadline=date(2026, 11, 15),
        official_source_url="https://daad.de/scholarships/masters",
        source_domain="daad.de",
        status=OpportunityStatus.ACTIVE,
    )

    # Add atomic evidence records
    ev_deadline = OpportunityEvidence(
        opportunity_id=opp_id,
        source_url="https://daad.de/scholarships/masters",
        field_name="deadline",
        evidence_text="Application Deadline: November 15, 2026",
        evidence_type="direct_text",
        confidence=1.0,
    )
    ev_funding = OpportunityEvidence(
        opportunity_id=opp_id,
        source_url="https://daad.de/scholarships/masters",
        field_name="funding_type",
        evidence_text="This award is fully funded including a monthly stipend of €934",
        evidence_type="direct_text",
        confidence=0.95,
    )

    # Add version snapshot
    version_1 = OpportunityVersion(
        opportunity_id=opp_id,
        version_number=1,
        changed_fields=["title", "deadline", "funding_type"],
        snapshot={
            "title": "DAAD Master Scholarship",
            "deadline": "2026-11-15",
            "funding_type": "Fully Funded",
        },
        change_summary="Initial extraction from official webpage",
    )

    opp.evidences.extend([ev_deadline, ev_funding])
    opp.versions.append(version_1)

    test_db_session.add(opp)
    await test_db_session.flush()

    # Query back
    stmt = select(Opportunity).where(Opportunity.id == opp_id)
    result = await test_db_session.execute(stmt)
    retrieved = result.scalar_one()

    assert retrieved.canonical_key == canonical_key
    assert len(retrieved.evidences) == 2
    assert len(retrieved.versions) == 1

    ev_names = {e.field_name for e in retrieved.evidences}
    assert "deadline" in ev_names
    assert "funding_type" in ev_names

    saved_version = retrieved.versions[0]
    assert saved_version.version_number == 1
    assert saved_version.snapshot["deadline"] == "2026-11-15"
