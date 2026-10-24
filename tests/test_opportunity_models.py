import uuid
from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.opportunity import (
    Opportunity,
    OpportunityCategory,
    OpportunityRequirement,
    OpportunitySource,
    OpportunityStatus,
    RequirementOperator,
    SourceType,
)


@pytest.mark.asyncio
async def test_opportunity_and_requirements_persistence(
    test_db_session: AsyncSession,
) -> None:
    opp_id = uuid.uuid4()
    opp = Opportunity(
        id=opp_id,
        title="DAAD Study Scholarship",
        organization="DAAD Germany",
        category=OpportunityCategory.SCHOLARSHIP,
        description="Full scholarships for postgraduate studies in Germany.",
        country="Germany",
        eligible_countries=["Global"],
        eligible_nationalities=["Global", "Pakistan"],
        degree_levels=["Master's", "PhD"],
        fields=["All Fields"],
        funding_type="Fully Funded",
        deadline=date(2026, 10, 31),
        official_source_url="https://daad.de/study-scholarship",
        source_domain="daad.de",
        status=OpportunityStatus.ACTIVE,
    )

    source = OpportunitySource(
        opportunity_id=opp_id,
        url="https://daad.de/study-scholarship",
        domain="daad.de",
        source_type=SourceType.OFFICIAL_WEBSITE,
        is_official=True,
        verification_status="verified",
    )

    req_cgpa = OpportunityRequirement(
        opportunity_id=opp_id,
        requirement_type="cgpa",
        operator=RequirementOperator.GREATER_THAN_EQUAL,
        value=3.0,
        unit="cgpa",
        is_mandatory=True,
    )
    req_lang = OpportunityRequirement(
        opportunity_id=opp_id,
        requirement_type="ielts",
        operator=RequirementOperator.GREATER_THAN_EQUAL,
        value=6.5,
        unit="band",
        is_mandatory=True,
    )

    opp.sources.append(source)
    opp.requirements.extend([req_cgpa, req_lang])

    test_db_session.add(opp)
    await test_db_session.flush()

    stmt = select(Opportunity).where(Opportunity.id == opp_id)
    result = await test_db_session.execute(stmt)
    retrieved = result.scalar_one()

    assert retrieved.title == "DAAD Study Scholarship"
    assert retrieved.category == OpportunityCategory.SCHOLARSHIP
    assert len(retrieved.sources) == 1
    assert retrieved.sources[0].is_official is True
    assert len(retrieved.requirements) == 2
    assert retrieved.requirements[0].requirement_type == "cgpa"
