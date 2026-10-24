from datetime import date

from app.opportunities.schemas.opportunity import (
    EligibilityCriteria,
    FundingType,
    OpportunityBase,
    OpportunityCategory,
    OpportunityStatus,
)


def test_opportunity_schema_validation() -> None:
    opportunity = OpportunityBase(
        title="Global Research Fellowship",
        organization="International Science Foundation",
        description="A fellowship program supporting innovative AI research.",
        category=OpportunityCategory.FELLOWSHIP,
        host_country="Germany",
        countries_allowed=["Global"],
        funding_type=FundingType.FULLY_FUNDED,
        funding_amount="€50,000 / year",
        deadline=date(2026, 11, 30),
        official_source_url="https://isf.example.org/fellowships",
        source_domain="isf.example.org",
        eligibility=EligibilityCriteria(
            degree_levels=["PhD", "Postdoc"],
            eligible_nationalities=["Global"],
            fields_of_study=["Computer Science", "Artificial Intelligence"],
        ),
        status=OpportunityStatus.ACTIVE,
    )

    assert opportunity.title == "Global Research Fellowship"
    assert opportunity.category == OpportunityCategory.FELLOWSHIP
    assert opportunity.funding_type == FundingType.FULLY_FUNDED
    assert opportunity.deadline == date(2026, 11, 30)
    assert len(opportunity.eligibility.degree_levels) == 2
