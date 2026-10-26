"""Comprehensive verification of Prompt 26:
Fields, Skills, Competencies, Specializations, Certifications, and Career Goals.
"""

import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.profile import SkillProficiency, SkillStatus
from app.services.normalization.field_taxonomy import (
    FieldCategory,
    FieldTaxonomyService,
)
from app.services.normalization.skills_normalizer import SkillsNormalizer
from app.opportunities.ranking.factors import FieldFitCalculator
from app.opportunities.eligibility.profile_adapter import UnifiedUserFacts


def test_field_taxonomy_all_eleven_categories() -> None:
    """Verifies all 11 global categories are present and structured."""
    categories = FieldTaxonomyService.get_all_categories()
    assert len(categories) == 11
    expected_categories = [
        "Computing and Information Technology",
        "Engineering and Technology",
        "Natural and Physical Sciences",
        "Health and Life Sciences",
        "Business, Economics and Management",
        "Social Sciences and Humanities",
        "Creative and Communication Fields",
        "Law, Governance and Public Service",
        "Agriculture, Environment and Food Systems",
        "Vocational, Technical and Practical Fields",
        "Other Education and Professional Fields",
    ]
    names = [c.name for c in categories]
    for cat in expected_categories:
        assert cat in names, f"Missing category: {cat}"


def test_field_taxonomy_search_and_matching() -> None:
    """Verifies school subjects, vocational trades, and higher ed disciplines match properly."""
    # Higher ed / academic disciplines
    cat_physics = FieldTaxonomyService.find_category_for_discipline("Physics")
    assert cat_physics is not None
    assert cat_physics.name == "Natural and Physical Sciences"

    cat_cs = FieldTaxonomyService.find_category_for_discipline("Computer Science")
    assert cat_cs is not None
    assert cat_cs.name == "Computing and Information Technology"

    # Search disciplines returns relevant items
    results = FieldTaxonomyService.search_disciplines("Biomedical")
    assert len(results) > 0
    assert any("Biomedical" in r["name"] or "Biomedical" in r["category"] for r in results)

    # Suggestions for school level
    suggestions_school = FieldTaxonomyService.get_suggested_specializations("Physics", is_school_level=True)
    assert len(suggestions_school) > 0


def test_skill_normalization_and_status_separation() -> None:
    """Verifies skills are normalized across categories and status is strictly preserved."""
    # 1. Have skill
    s_have = SkillsNormalizer.normalize_skill(
        "Python Programming",
        proficiency="expert",
        status="have",
        acquisition_source="Degree Coursework",
    )
    assert s_have.normalized_name == "Python"
    assert s_have.status == "have"
    assert s_have.acquisition_source == "Degree Coursework"

    # 2. Learning skill
    s_learning = SkillsNormalizer.normalize_skill(
        "Docker",
        status="learning",
        acquisition_source="Self-Study",
    )
    assert s_learning.normalized_name == "Docker"
    assert s_learning.status == "learning"

    # 3. Desired skill
    s_desired = SkillsNormalizer.normalize_skill(
        "Quantum Computing",
        status="desired",
    )
    assert s_desired.status == "desired"


def test_ranking_field_and_skill_fit_strict_competency() -> None:
    """Verifies FieldFitCalculator strictly rewards 'have' skills and does not falsely treat 'desired' skills as proven."""
    class DummyOpp:
        title = "AI & Machine Learning Research Fellowship"
        description = "Requires Python and Machine Learning expertise."
        fields = ["Computer Science"]
        category = "fellowship"

    # User 1: Has Python verified in skills_have
    facts_with_have = UnifiedUserFacts(
        user_id=str(uuid.uuid4()),
        primary_field="Computing, Artificial Intelligence & Digital Technologies",
        specializations=["Machine Learning"],
        skills_have=["Python", "Machine Learning"],
        skills_desired=["Quantum Computing"],
    )

    fit_have = FieldFitCalculator.calculate(DummyOpp(), facts_with_have)
    assert fit_have.score >= 0.8
    assert "matches" in fit_have.reason.lower() or "aligned" in fit_have.reason.lower() or "field" in fit_have.reason.lower()

    # User 2: Only has Python in 'skills_desired' (NO verified skills_have)
    facts_with_desired = UnifiedUserFacts(
        user_id=str(uuid.uuid4()),
        primary_field="Creative Arts, Design, Media, Music & Film",
        skills_have=["Graphic Design"],
        skills_desired=["Python", "Machine Learning"],
    )

    fit_desired = FieldFitCalculator.calculate(DummyOpp(), facts_with_desired)
    # The score should NOT be rewarded as high match for technical requirement
    assert fit_desired.score < 0.8
    assert "Graphic Design" not in fit_desired.reason


@pytest.mark.asyncio
async def test_certifications_and_profile_api(client: AsyncClient) -> None:
    """Verifies certification and project API endpoints operate correctly."""
    # 1. Update Profile with Fields & Career Goals
    patch_res = await client.patch(
        "/api/v1/profile",
        json={
            "primary_field": "Computing and Information Technology",
            "secondary_fields": ["Data Science & Analytics"],
            "specializations": ["Machine Learning", "Cloud Infrastructure"],
            "career_goals": ["Machine Learning Engineer", "AI Researcher"],
            "learning_goals": ["Deep Reinforcement Learning", "Kubernetes"],
        },
    )
    assert patch_res.status_code == 200
    p_data = patch_res.json()
    assert p_data["primary_field"] == "Computing and Information Technology"
    assert "Machine Learning" in p_data["specializations"]

    # 2. Add Certification
    cert_res = await client.post(
        "/api/v1/profile/certifications",
        json={
            "title": "AWS Certified Solutions Architect",
            "issuing_organization": "Amazon Web Services",
            "category": "Cloud Computing",
            "status": "Completed",
            "credential_id": "AWS-12345",
            "skills": ["AWS", "Cloud Architecture"],
        },
    )
    assert cert_res.status_code == 201
    c_data = cert_res.json()
    assert c_data["title"] == "AWS Certified Solutions Architect"
    cert_id = c_data["id"]

    # 3. Add Project with new fields
    proj_res = await client.post(
        "/api/v1/profile/projects",
        json={
            "title": "Autonomous Drone Navigation",
            "project_type": "Academic Capstone",
            "role": "Lead ML Engineer",
            "description": "Vision-based obstacle avoidance drone.",
            "skills": ["Python", "Computer Vision", "ROS"],
            "outcome": "Published paper in IEEE student conference.",
        },
    )
    assert proj_res.status_code == 201
    proj_data = proj_res.json()
    assert proj_data["title"] == "Autonomous Drone Navigation"
    assert proj_data["project_type"] == "Academic Capstone"
    proj_id = proj_data["id"]

    # 4. Add Skill with status
    skill_res = await client.post(
        "/api/v1/profile/skills",
        json={
            "name": "Rust",
            "category": "Technical & Digital Skills",
            "proficiency": "Basic working knowledge",
            "status": "learning",
            "acquisition_source": "Personal Project",
        },
    )
    assert skill_res.status_code == 201
    skill_data = skill_res.json()
    assert skill_data["name"] == "Rust"
    assert skill_data["status"] == "learning"
    skill_id = skill_data["id"]

    # 5. Verify Full Profile contains all new entities
    full_res = await client.get("/api/v1/profile")
    assert full_res.status_code == 200
    full_data = full_res.json()
    assert len(full_data.get("certifications", [])) >= 1
    assert any(c["title"] == "AWS Certified Solutions Architect" for c in full_data["certifications"])
    assert any(p["title"] == "Autonomous Drone Navigation" for p in full_data.get("projects", []))

    # 6. Verify Deletion of sub-records
    del_cert = await client.delete(f"/api/v1/profile/certifications/{cert_id}")
    assert del_cert.status_code == 204

    del_proj = await client.delete(f"/api/v1/profile/projects/{proj_id}")
    assert del_proj.status_code == 204

    del_skill = await client.delete(f"/api/v1/profile/skills/{skill_id}")
    assert del_skill.status_code == 204
