from datetime import date

import pytest
from pydantic import ValidationError

from app.models.profile import EducationLevel, SkillProficiency, TestType
from app.schemas.profile import (
    AcademicRecordCreate,
    SkillCreate,
    TestResultCreate,
    UserProfileCreate,
    WorkExperienceCreate,
)


def test_valid_profile_creation() -> None:
    profile = UserProfileCreate(
        nationality="Pakistan",
        country_of_residence="Germany",
        city="Munich",
        education_level=EducationLevel.MASTERS,
        degree_title="MSc Computer Science",
        field_of_study="Artificial Intelligence",
        university="Technical University of Munich",
        graduation_year=2024,
        cgpa=3.85,
        percentage=88.5,
    )
    assert profile.nationality == "Pakistan"
    assert profile.cgpa == 3.85
    assert profile.education_level == EducationLevel.MASTERS


def test_invalid_cgpa_out_of_range() -> None:
    with pytest.raises(ValidationError):
        UserProfileCreate(cgpa=11.0)  # Max allowed is 10.0

    with pytest.raises(ValidationError):
        UserProfileCreate(cgpa=-0.5)


def test_invalid_percentage_out_of_range() -> None:
    with pytest.raises(ValidationError):
        UserProfileCreate(percentage=105.0)

    with pytest.raises(ValidationError):
        UserProfileCreate(percentage=-2.0)


def test_invalid_graduation_year() -> None:
    with pytest.raises(ValidationError):
        UserProfileCreate(graduation_year=1890)

    with pytest.raises(ValidationError):
        UserProfileCreate(graduation_year=2250)


def test_invalid_academic_year_range() -> None:
    # start_year > end_year must raise ValueError
    with pytest.raises(ValidationError, match="end_year cannot be before start_year"):
        AcademicRecordCreate(
            institution="Fast NUCES",
            degree="BS CS",
            field_of_study="Computer Science",
            start_year=2022,
            end_year=2018,
        )


def test_valid_academic_record() -> None:
    record = AcademicRecordCreate(
        institution="LUMS",
        degree="BSc Electrical Engineering",
        field_of_study="Engineering",
        start_year=2016,
        end_year=2020,
        grade="3.7",
        grading_scale="4.0",
        country="Pakistan",
    )
    assert record.institution == "LUMS"
    assert record.end_year == 2020


def test_invalid_test_result_dates() -> None:
    # expiry before test date
    with pytest.raises(ValidationError, match="expiry_date cannot be before test_date"):
        TestResultCreate(
            test_name="IELTS Academic",
            test_type=TestType.LANGUAGE,
            score="8.0",
            test_date=date(2025, 6, 1),
            expiry_date=date(2024, 6, 1),
        )


def test_valid_test_result_with_subscores() -> None:
    result = TestResultCreate(
        test_name="IELTS Academic",
        test_type=TestType.LANGUAGE,
        score="7.5",
        score_details={
            "overall": 7.5,
            "listening": 8.0,
            "reading": 7.5,
            "writing": 7.0,
            "speaking": 7.5,
        },
        test_date=date(2024, 5, 10),
        expiry_date=date(2026, 5, 10),
    )
    assert result.score_details["listening"] == 8.0


def test_work_experience_date_validation() -> None:
    with pytest.raises(ValidationError, match="end_date cannot be before start_date"):
        WorkExperienceCreate(
            organization="Tech Corp",
            job_title="Software Engineer",
            start_date=date(2024, 1, 1),
            end_date=date(2023, 1, 1),
        )


def test_valid_skill_creation() -> None:
    skill = SkillCreate(
        name="Python",
        category="Programming",
        proficiency=SkillProficiency.EXPERT,
        years_of_experience=5.5,
    )
    assert skill.name == "Python"
    assert skill.proficiency == SkillProficiency.EXPERT
