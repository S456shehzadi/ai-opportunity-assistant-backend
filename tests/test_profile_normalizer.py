import uuid

from app.models.profile import (
    AcademicRecord,
    EducationLevel,
    Language,
    LanguageProficiency,
    Publication,
    Skill,
    SkillProficiency,
    TestResult,
    UserPreferences,
    UserProfile,
    WorkExperience,
)
from app.models.user import User
from app.services.profile_normalizer import AIProfileContext, ProfileNormalizer


def test_profile_normalizer_generates_ai_context() -> None:
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email="scholar@example.com",
        is_active=True,
    )
    user.profile = UserProfile(
        user_id=user_id,
        nationality="Pakistan",
        country_of_residence="United States",
        city="Boston",
        education_level=EducationLevel.MASTERS,
        degree_title="Master of Science",
        field_of_study="Computer Science",
        university="MIT",
        cgpa=3.9,
    )
    user.preferences = UserPreferences(
        user_id=user_id,
        preferred_countries=["Germany", "United States", "Canada"],
        preferred_opportunity_categories=["Scholarship", "Fellowship"],
        preferred_fields=["Artificial Intelligence"],
        funding_preference="Fully Funded",
    )
    user.academic_records = [
        AcademicRecord(
            user_id=user_id,
            institution="LUMS",
            degree="BSc Computer Science",
            field_of_study="Computer Science",
            start_year=2018,
            end_year=2022,
            grade="3.8",
        )
    ]
    user.test_results = [
        TestResult(
            user_id=user_id,
            test_name="IELTS",
            score="8.0",
            score_details={"overall": 8.0, "reading": 8.5},
        ),
        TestResult(
            user_id=user_id,
            test_name="GRE",
            score="330",
            score_details={"verbal": 165, "quant": 165},
        ),
    ]
    user.skills = [
        Skill(
            user_id=user_id,
            name="Deep Learning",
            proficiency=SkillProficiency.ADVANCED,
        ),
        Skill(
            user_id=user_id,
            name="Python",
            proficiency=SkillProficiency.EXPERT,
        ),
    ]
    user.languages = [
        Language(
            user_id=user_id,
            language_name="English",
            proficiency=LanguageProficiency.FLUENT,
        ),
        Language(
            user_id=user_id,
            language_name="Urdu",
            proficiency=LanguageProficiency.NATIVE,
        ),
    ]
    user.work_experiences = [
        WorkExperience(
            user_id=user_id,
            organization="AI Lab",
            job_title="Research Assistant",
        )
    ]
    user.publications = [
        Publication(
            user_id=user_id,
            title="Transformer Optimization in Low-Resource Settings",
            authors=["scholar@example.com"],
        )
    ]

    ai_context = ProfileNormalizer.normalize(user)

    assert isinstance(ai_context, AIProfileContext)
    assert ai_context.user_id == user_id
    assert ai_context.is_profile_complete is True
    assert ai_context.demographics.nationality == "Pakistan"
    assert "Master" in ai_context.academics.highest_education_level
    assert "Computer Science" in ai_context.academics.fields_of_study
    assert ai_context.standardized_tests.test_scores["IELTS"] == "8.0"
    assert "Deep Learning" in ai_context.skills
    assert ai_context.languages["English"] == "Fluent"
    assert ai_context.experience.publication_count == 1
    assert "Germany" in ai_context.preferences.preferred_countries
    assert "Pakistan" in ai_context.matching_signals["eligible_nationalities"]
