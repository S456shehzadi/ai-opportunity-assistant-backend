import uuid
from datetime import date

from app.models.profile import (
    AcademicRecord,
    EducationLevel,
    Language,
    LanguageProficiency,
    Skill,
    SkillProficiency,
    TestResult,
    UserPreferences,
    UserProfile,
)
from app.models.user import User
from app.services.normalization.test_normalizer import TestStatus
from app.services.profile_normalizer import ProfileNormalizer


def test_normalized_ai_profile_creation_and_unknowns() -> None:
    user_id = uuid.uuid4()
    user = User(id=user_id, email="applicant@test.com", is_active=True)

    # User with minimal profile (no tests entered yet)
    user.profile = UserProfile(
        user_id=user_id,
        nationality="United States",
        country_of_residence="Germany",
        city="Munich",
        education_level=EducationLevel.UNDERGRADUATE,
        degree_title="BS Computer Science",
        field_of_study="Computer Science",
        university="TUM",
        cgpa=3.85,
    )
    user.preferences = UserPreferences(
        user_id=user_id,
        preferred_countries=["Germany", "Switzerland"],
        preferred_opportunity_categories=["Scholarship"],
        funding_preference="Fully Funded",
    )
    user.academic_records = [
        AcademicRecord(
            user_id=user_id,
            institution="TUM",
            degree="Bachelor of Science in CS",
            field_of_study="Computer Science",
            start_year=2020,
            end_year=2024,
            grade="3.85",
        )
    ]
    user.skills = [
        Skill(
            user_id=user_id,
            name="python developer",
            proficiency=SkillProficiency.ADVANCED,
            years_of_experience=3.0,
        )
    ]
    user.languages = [
        Language(
            user_id=user_id,
            language_name="English",
            proficiency=LanguageProficiency.NATIVE,
        )
    ]

    ai_profile = ProfileNormalizer.normalize_ai_profile(user)

    # 1. Identity & Geography
    assert ai_profile.identity_context.nationality == "United States"
    assert ai_profile.identity_context.nationality_country_code == "US"
    assert ai_profile.identity_context.country_of_residence == "Germany"
    assert ai_profile.identity_context.residence_country_code == "DE"

    # 2. Education
    assert ai_profile.academic_performance.highest_degree_level == "Bachelor's"
    assert ai_profile.academic_performance.normalized_gpa_4_scale == 3.85
    assert len(ai_profile.education) > 0
    assert ai_profile.education[0].normalized_degree_level == "Bachelor's"
    assert ai_profile.education[0].broad_discipline == "Computing & Information Technology"

    # 3. Tests: Missing IELTS MUST be marked as UNKNOWN (Never "No" or False)
    assert "ielts" in ai_profile.tests
    ielts_item = ai_profile.tests["ielts"]
    assert ielts_item.status == TestStatus.UNKNOWN
    assert ielts_item.score is None

    assert "toefl" in ai_profile.tests
    assert ai_profile.tests["toefl"].status == TestStatus.UNKNOWN

    # 4. Skills
    assert len(ai_profile.skills) == 1
    assert ai_profile.skills[0].normalized_name == "Python"
    assert ai_profile.skills[0].years_of_experience == 3.0

    # 5. Completeness
    assert "tests" in ai_profile.completeness.unknown_fields
    assert "nationality" in ai_profile.completeness.known_fields


def test_normalized_ai_profile_with_valid_test() -> None:
    user_id = uuid.uuid4()
    user = User(id=user_id, email="scholar@test.com", is_active=True)
    user.profile = UserProfile(
        user_id=user_id,
        nationality="Pakistan",
        education_level=EducationLevel.MASTERS,
    )
    user.test_results = [
        TestResult(
            user_id=user_id,
            test_name="IELTS Academic",
            score="8.5",
            test_date=date(2025, 1, 15),
            score_details={"reading": 9.0, "listening": 8.5},
        )
    ]

    ai_profile = ProfileNormalizer.normalize_ai_profile(user)
    assert "ielts" in ai_profile.tests
    ielts = ai_profile.tests["ielts"]
    assert ielts.score == "8.5"
    assert ielts.status in (TestStatus.VALID, TestStatus.TAKEN)
    assert ielts.sub_scores["reading"] == 9.0
