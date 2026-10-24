"""Evaluation dataset covering Cases 1 through 12 for personalized ranking."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.opportunities.eligibility.profile_adapter import UnifiedUserFacts
from app.opportunities.eligibility.schemas import (
    EligibilityResult,
    OverallEligibilityStatus,
    PersonalizedIntelligenceSummary,
    RequirementEvaluation,
    RequirementPriority,
    RequirementStatus,
)
from app.opportunities.ranking.schemas import (
    PreferencePriority,
    UserPreference,
)
from app.opportunities.schemas.opportunity import (
    EligibilityCriteria,
    FundingType,
    OpportunityCategory,
    OpportunityRead,
    OpportunityStatus,
)


def create_user_profile(
    user_id: str = "user-123",
    field: str = "Computer Science",
    degree_level: str = "Bachelor's",
    cgpa: float = 3.85,
    nationality: str = "Pakistan",
    preferred_countries: list[str] | None = None,
    preferred_funding: str = "FULLY_FUNDED",
) -> tuple[UnifiedUserFacts, list[UserPreference]]:
    """Builds a standardized user test profile with explicit preferences."""
    user_facts = UnifiedUserFacts(
        user_id=user_id,
        email="student@example.org",
        nationality=nationality,
        nationality_country_code="PK" if nationality == "Pakistan" else "DE",
        academic_records=[
            {
                "institution": "National University",
                "degree_title": f"Bachelor of Science in {field}",
                "field_of_study": field,
                "degree_level": degree_level,
                "cgpa": cgpa,
                "grading_scale": "4.0",
                "is_completed": True,
            }
        ],
        highest_degree_level=degree_level,
        highest_cgpa=cgpa,
        normalized_gpa_4_scale=cgpa,
        has_english_medium_degree=True,
    )

    preferences: list[UserPreference] = [
        UserPreference(
            category="FUNDING",
            value=preferred_funding,
            priority=PreferencePriority.HIGH,
            explicit=True,
        ),
        UserPreference(
            category="LOCATION",
            value=preferred_countries or ["Germany", "Europe"],
            priority=PreferencePriority.HIGH,
            explicit=True,
        ),
        UserPreference(
            category="DEGREE_LEVEL",
            value="Master's",
            priority=PreferencePriority.HIGH,
            explicit=True,
        ),
    ]

    return user_facts, preferences


def create_opportunity(
    opp_id: str,
    title: str,
    org: str = "DAAD",
    category: OpportunityCategory = OpportunityCategory.SCHOLARSHIP,
    host_country: str = "Germany",
    funding_type: FundingType = FundingType.FULLY_FUNDED,
    deadline_days: int = 45,
    is_rolling: bool = False,
    min_gpa: float = 3.0,
    fields: list[str] | None = None,
    degree_levels: list[str] | None = None,
    last_verified_days_ago: int = 5,
    trust_score: float = 0.95,
    source_domain: str = "daad.de",
) -> OpportunityRead:
    """Helper to instantiate mock OpportunityRead candidates."""
    now = datetime.now(UTC)
    dl = None if is_rolling else (now + timedelta(days=deadline_days)).date()
    verified_dt = now - timedelta(days=last_verified_days_ago)

    return OpportunityRead(
        id=opp_id,
        title=title,
        organization=org,
        description=f"{title} offered by {org} in {host_country}.",
        category=category,
        host_country=host_country,
        funding_type=funding_type,
        deadline=dl,
        last_verified=verified_dt,
        status=OpportunityStatus.ACTIVE
        if (is_rolling or deadline_days >= 0)
        else OpportunityStatus.EXPIRED,
        official_source_url=f"https://{source_domain}/opp/{opp_id}",
        source_domain=source_domain,
        trust_score=trust_score,
        eligibility=EligibilityCriteria(
            min_gpa=min_gpa,
            fields_of_study=fields or ["Computer Science", "Informatics"],
            degree_levels=degree_levels or ["Master's"],
            eligible_nationalities=["Global", "Pakistan"],
        ),
        created_at=now - timedelta(days=60),
        updated_at=verified_dt,
    )


def create_eligibility_result(
    opp_id: str,
    user_id: str = "user-123",
    status: OverallEligibilityStatus = OverallEligibilityStatus.CLEARLY_ELIGIBLE,
    match_percentage: float = 100.0,
    unknowns: list[str] | None = None,
    blocking: list[str] | None = None,
) -> EligibilityResult:
    """Helper creating mock EligibilityResult."""
    unknown_reqs = [
        RequirementEvaluation(
            requirement_id=f"req-unk-{i}",
            requirement_type="test",
            requirement_description=u,
            status=RequirementStatus.UNKNOWN,
            priority=RequirementPriority.MANDATORY,
            explanation=u,
            requires_verification=True,
        )
        for i, u in enumerate(unknowns or [])
    ]
    blocking_reqs = [
        RequirementEvaluation(
            requirement_id=f"req-block-{i}",
            requirement_type="nationality",
            requirement_description=b,
            status=RequirementStatus.NO_MATCH,
            priority=RequirementPriority.MANDATORY,
            explanation=b,
            requires_verification=False,
        )
        for i, b in enumerate(blocking or [])
    ]

    return EligibilityResult(
        opportunity_id=opp_id,
        user_id=user_id,
        overall_status=status,
        match_percentage=match_percentage,
        unknown_requirements=unknown_reqs,
        blocking_requirements=blocking_reqs,
        explanation=f"Eligibility evaluated as {status.value}.",
        personalized_intelligence=PersonalizedIntelligenceSummary(
            unknown_requirements=[r.requirement_description for r in unknown_reqs],
            unsatisfied_requirements=[r.requirement_description for r in blocking_reqs],
        ),
    )
