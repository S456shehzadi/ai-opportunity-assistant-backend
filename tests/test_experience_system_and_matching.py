"""Comprehensive verification of Prompt 27:
Experience System, 12 Experience Categories, CRUD, Idempotency, Normalization, and Ranking.
"""

from datetime import date
import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.profile import UserProfile, WorkExperience
from app.models.user import User
from app.schemas.profile import WorkExperienceCreate, WorkExperienceUpdate
from app.schemas.ai_profile import WorkExperienceSummary, NormalizedAIProfile
from app.services.profile_normalizer import ProfileNormalizer
from app.opportunities.eligibility.profile_adapter import ProfileAdapter, UnifiedUserFacts
from app.opportunities.ranking.factors import ExperienceFitCalculator
from app.opportunities.ranking.engine import PersonalizedRankingEngine
from app.opportunities.ranking.schemas import (
    OpportunityRankingContext,
    RankingFactorType,
)


ALL_12_EXPERIENCE_CATEGORIES = [
    "Employment",
    "Internship",
    "Freelance or Contract Work",
    "Entrepreneurship or Startup",
    "Research Experience",
    "Academic or Personal Projects",
    "Volunteering and Community Service",
    "Leadership and Student Activities",
    "Apprenticeship or Practical Training",
    "Teaching, Tutoring, or Mentoring",
    "Competitions and Hackathons",
    "Other Relevant Experience",
]


def test_experience_categories_and_date_validation() -> None:
    """Verifies all 12 categories are valid in schema and date rules are enforced."""
    for cat in ALL_12_EXPERIENCE_CATEGORIES:
        exp = WorkExperienceCreate(
            job_title="Lead Developer",
            organization="Tech Hub",
            category=cat,
            start_date=date(2023, 1, 1),
            is_current=True,
            end_date=date(2023, 12, 1),  # Should be cleared since is_current is True
            achievements=["Built an automated pipeline"],
        )
        assert exp.category == cat
        assert exp.is_current is True
        assert exp.end_date is None  # Automatically cleared by validator

    # Test independent default organization
    proj_exp = WorkExperienceCreate(
        job_title="Open Source Contributor",
        organization="",  # Empty string should default to "Independent"
        category="Academic or Personal Projects",
        is_current=True,
    )
    assert proj_exp.organization == "Independent"


def test_profile_normalizer_and_adapter_experience_signals() -> None:
    """Verifies that profile normalizer extracts rich category signals and populates facts."""
    user_id = uuid.uuid4()
    user = User(id=user_id, email="student@example.com", is_active=True)
    user.profile = UserProfile(
        user_id=user_id,
        headline="AI & Open Source Enthusiast",
        summary="Undergraduate passionate about generative AI and robotics.",
    )
    user.work_experiences = [
        WorkExperience(
            id=uuid.uuid4(),
            user_id=user_id,
            job_title="Machine Learning Intern",
            organization="Data Corp",
            category="Internship",
            start_date=date(2023, 6, 1),
            end_date=date(2023, 9, 1),
            is_current=False,
            achievements=[{"description": "Trained lightweight transformer model"}],
        ),
        WorkExperience(
            id=uuid.uuid4(),
            user_id=user_id,
            job_title="Lead Organizer",
            organization="Google Developer Student Club",
            category="Leadership and Student Activities",
            start_date=date(2023, 9, 1),
            is_current=True,
            achievements=[{"description": "Organized campus hackathons with 200+ attendees"}],
        ),
        WorkExperience(
            id=uuid.uuid4(),
            user_id=user_id,
            job_title="Autonomous Rover Project",
            organization="Robotics Club",
            category="Academic or Personal Projects",
            start_date=date(2022, 1, 1),
            end_date=date(2022, 12, 1),
            is_current=False,
            achievements=[{"description": "Won 1st place in national engineering challenge"}],
        ),
    ]
    user.academic_records = []
    user.test_results = []
    user.skills = []
    user.languages = []
    user.research_experiences = []
    user.publications = []
    user.projects = []
    user.certifications = []

    normalized = ProfileNormalizer.normalize_ai_profile(user)
    assert normalized.headline == "AI & Open Source Enthusiast"
    assert normalized.summary == "Undergraduate passionate about generative AI and robotics."

    we = normalized.work_experience
    assert we.has_internship is True
    assert we.has_leadership is True
    assert we.has_competition_or_award is True
    assert "Internship" in we.categories
    assert "Leadership and Student Activities" in we.categories
    assert "Academic or Personal Projects" in we.categories

    # Adapt to UnifiedUserFacts
    facts = ProfileAdapter.adapt(normalized)
    assert facts.headline == "AI & Open Source Enthusiast"
    assert facts.has_internship is True
    assert facts.has_leadership is True
    assert facts.has_competitions is True
    assert len(facts.experience_items) == 3


def test_ranking_experience_fit_zero_experience_scholarship_never_penalized() -> None:
    """Early students with zero experience applying for scholarships or grants must NEVER be penalized."""
    # User with zero work experience records
    user_facts = UnifiedUserFacts(
        user_id="user-early-student",
        highest_degree_level="Matriculation / Secondary School",
        work_experience_years=0.0,
        experience_categories=[],
        experience_items=[],
    )

    class MockScholarship:
        title = "Global Undergraduate Merit Scholarship"
        category = "scholarship"
        description = "Full tuition grant for academic excellence in secondary and higher education."

    detail = ExperienceFitCalculator.calculate(MockScholarship(), user_facts)
    assert detail.score >= 0.85
    assert detail.status == "HIGH"
    assert "does not mandate prior work experience" in detail.reason


def test_ranking_experience_fit_internship_and_projects_matching() -> None:
    """Tests that internship roles properly recognize internships, projects, and early students."""
    class MockInternship:
        title = "Summer Software Engineering Intern"
        category = "internship"
        description = "Exciting 3-month summer internship for students and early-career developers."

    # 1. Candidate with direct internship experience
    facts_with_internship = UnifiedUserFacts(
        user_id="user-intern",
        work_experience_years=0.5,
        experience_categories=["Internship"],
        has_internship=True,
    )
    res_intern = ExperienceFitCalculator.calculate(MockInternship(), facts_with_internship)
    assert res_intern.score == 1.0
    assert res_intern.status == "HIGH"

    # 2. Candidate with personal/academic projects and freelance
    facts_with_projects = UnifiedUserFacts(
        user_id="user-projects",
        work_experience_years=0.0,
        experience_categories=["Academic or Personal Projects"],
        has_freelance=True,
    )
    res_proj = ExperienceFitCalculator.calculate(MockInternship(), facts_with_projects)
    assert res_proj.score >= 0.90
    assert "demonstrates practical competency" in res_proj.reason

    # 3. Early student with 0 experience applying for internship
    facts_zero_exp = UnifiedUserFacts(
        user_id="user-beginner",
        work_experience_years=0.0,
        experience_categories=[],
    )
    res_beginner = ExperienceFitCalculator.calculate(MockInternship(), facts_zero_exp)
    assert res_beginner.score >= 0.80
    assert res_beginner.status == "HIGH"


def test_ranking_experience_fit_explicit_years_requirement() -> None:
    """Verifies that an opportunity requiring 5+ years of experience scores appropriately."""
    class MockSeniorRole:
        title = "Senior Principal Researcher"
        category = "fellowship"
        description = "Requires at least 5 years of professional research experience in advanced systems."

    # User meeting requirement
    senior_facts = UnifiedUserFacts(
        user_id="user-senior",
        work_experience_years=6.0,
        experience_categories=["Employment", "Research Experience"],
        has_research_experience=True,
    )
    res_senior = ExperienceFitCalculator.calculate(MockSeniorRole(), senior_facts)
    assert res_senior.score == 1.0
    assert res_senior.status == "HIGH"

    # User with partial experience (2 years)
    mid_facts = UnifiedUserFacts(
        user_id="user-mid",
        work_experience_years=2.0,
        experience_categories=["Employment"],
    )
    res_mid = ExperienceFitCalculator.calculate(MockSeniorRole(), mid_facts)
    assert 0.60 <= res_mid.score <= 0.80
    assert res_mid.status == "MEDIUM"

    # User with 0 experience
    no_exp_facts = UnifiedUserFacts(
        user_id="user-none",
        work_experience_years=0.0,
        experience_categories=[],
    )
    res_no_exp = ExperienceFitCalculator.calculate(MockSeniorRole(), no_exp_facts)
    assert res_no_exp.score <= 0.50
    assert res_no_exp.status == "LOW"


def test_personalized_ranking_engine_includes_experience_dimension() -> None:
    """Verifies PersonalizedRankingEngine includes EXPERIENCE_FIT in factor breakdowns."""
    engine = PersonalizedRankingEngine()

    class MockOpp:
        id = "opp-123"
        title = "International Tech Fellowship"
        category = "fellowship"
        description = "A prestigious global fellowship for developers and researchers."
        organization = "Global Innovation Foundation"
        host_country = "United Kingdom"
        funding_type = "fully_funded"
        is_rolling = False
        source_domain = "ox.ac.uk"
        trust_score = 0.95

    user_facts = UnifiedUserFacts(
        user_id="test-user-ranking",
        primary_field="Computer Science",
        work_experience_years=1.5,
        experience_categories=["Internship", "Academic or Personal Projects"],
        has_internship=True,
    )

    context = OpportunityRankingContext(
        opportunities=[MockOpp()],
        user_facts=user_facts,
    )

    result = engine.rank(context)
    assert len(result.opportunities) == 1
    ranked_opp = result.opportunities[0]
    assert "experience_fit" in ranked_opp.ranking_factors or RankingFactorType.EXPERIENCE_FIT.value in ranked_opp.ranking_factors
    exp_factor = ranked_opp.ranking_factors.get("experience_fit") or ranked_opp.ranking_factors.get(RankingFactorType.EXPERIENCE_FIT.value)
    assert exp_factor is not None
    assert exp_factor.score >= 0.85
    assert exp_factor.factor_type == RankingFactorType.EXPERIENCE_FIT


@pytest.mark.asyncio
async def test_experience_api_crud_and_idempotency(client: AsyncClient) -> None:
    """Verifies CRUD operations and idempotency across /api/v1/profile/work-experience and /experience endpoints."""
    # 1. First ensure user profile exists
    await client.post(
        "/api/v1/profile",
        json={
            "nationality": "Pakistan",
            "country_of_residence": "Pakistan",
            "city": "Lahore",
            "headline": "Junior AI Researcher",
            "summary": "Passionate about computer vision and robotics.",
        },
    )

    # 2. Add an experience record
    exp_payload = {
        "job_title": "Research Assistant",
        "organization": "University Robotics Lab",
        "category": "Research Experience",
        "industry": "Robotics & Automation",
        "department": "Computer Science",
        "city": "Lahore",
        "work_arrangement": "Hybrid",
        "start_date": "2023-01-15",
        "is_current": True,
        "description": "Led perception benchmarking experiments.",
        "achievements": ["Co-authored conference workshop paper", "Achieved 94% mAP on benchmark"],
    }
    create_res = await client.post("/api/v1/profile/work-experience", json=exp_payload)
    assert create_res.status_code == 201
    created_data = create_res.json()
    exp_id = created_data["id"]
    assert created_data["category"] == "Research Experience"
    assert created_data["job_title"] == "Research Assistant"
    assert len(created_data["achievements"]) == 2

    # 3. Test Idempotency: Repeating the exact same POST should return 200/201 and not duplicate
    dup_res = await client.post("/api/v1/profile/work-experience", json=exp_payload)
    assert dup_res.status_code in (200, 201)
    assert dup_res.json()["id"] == exp_id

    # 4. Patch experience via /experience/{exp_id} alias
    patch_payload = {
        "is_current": False,
        "end_date": "2023-12-31",
        "achievements": [
            "Co-authored conference workshop paper",
            "Achieved 94% mAP",
            "Released open source dataset",
        ],
    }
    patch_res = await client.patch(f"/api/v1/profile/experience/{exp_id}", json=patch_payload)
    assert patch_res.status_code == 200
    patched_data = patch_res.json()
    assert patched_data["is_current"] is False
    assert patched_data["end_date"] == "2023-12-31"
    assert len(patched_data["achievements"]) == 3

    # 5. Verify Consolidated Profile includes the work experience
    get_profile = await client.get("/api/v1/profile")
    assert get_profile.status_code == 200
    profile_json = get_profile.json()
    exps = profile_json.get("work_experiences", [])
    assert len(exps) == 1
    assert exps[0]["category"] == "Research Experience"

    # 6. Delete experience via /api/v1/profile/work-experience/{exp_id}
    del_res = await client.delete(f"/api/v1/profile/work-experience/{exp_id}")
    assert del_res.status_code == 204

    # Verify deletion
    get_profile_after = await client.get("/api/v1/profile")
    assert len(get_profile_after.json().get("work_experiences", [])) == 0

