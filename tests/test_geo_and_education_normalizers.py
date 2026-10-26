from datetime import UTC, datetime, timedelta

from app.services.normalization.education_normalizer import EducationNormalizer
from app.services.normalization.geo_normalizer import GeoNormalizer
from app.services.normalization.skills_normalizer import SkillsNormalizer
from app.services.normalization.test_normalizer import TestNormalizer, TestStatus


def test_geo_normalizer_country_aliases() -> None:
    # USA variations
    for name in ["USA", "United States", "United States of America", "US", "america", "U.S."]:
        c = GeoNormalizer.normalize_country(name)
        assert c is not None, f"Failed to normalize {name}"
        assert c.code == "US"
        assert c.name == "United States"
        assert c.continent == "Americas"

    # Germany variations
    for name in ["Germany", "Deutschland", "DE"]:
        c = GeoNormalizer.normalize_country(name)
        assert c is not None, f"Failed to normalize {name}"
        assert c.code == "DE"
        assert c.name == "Germany"

    # UK variations
    for name in ["UK", "United Kingdom", "Great Britain", "Britain", "England"]:
        c = GeoNormalizer.normalize_country(name)
        assert c is not None, f"Failed to normalize {name}"
        assert c.code == "GB"


def test_geo_normalizer_regions_and_membership() -> None:
    assert GeoNormalizer.normalize_region("Europe") == "Europe"
    assert GeoNormalizer.normalize_region("in Europe") == "Europe"
    assert GeoNormalizer.normalize_region("European Union") == "European Union"
    assert GeoNormalizer.normalize_region("Asia") == "Asia"

    # Region membership
    assert GeoNormalizer.is_in_region("DE", "Europe") is True
    assert GeoNormalizer.is_in_region("FR", "Europe") is True
    assert GeoNormalizer.is_in_region("US", "Europe") is False
    assert GeoNormalizer.is_in_region("US", "North America") is True
    assert GeoNormalizer.is_in_region("PK", "Asia") is True


def test_education_normalizer_degree_levels() -> None:
    assert EducationNormalizer.normalize_degree_level("Bachelor of Science in CS") == EducationNormalizer.LEVEL_BACHELORS
    assert EducationNormalizer.normalize_degree_level("BS Computer Science") == EducationNormalizer.LEVEL_BACHELORS
    assert EducationNormalizer.normalize_degree_level("B.Sc. Software Engineering") == EducationNormalizer.LEVEL_BACHELORS
    assert EducationNormalizer.normalize_degree_level("Undergraduate degree") == EducationNormalizer.LEVEL_BACHELORS

    assert EducationNormalizer.normalize_degree_level("Master of Science") == EducationNormalizer.LEVEL_MASTERS
    assert EducationNormalizer.normalize_degree_level("MS Artificial Intelligence") == EducationNormalizer.LEVEL_MASTERS
    assert EducationNormalizer.normalize_degree_level("MSc Data Science") == EducationNormalizer.LEVEL_MASTERS
    assert EducationNormalizer.normalize_degree_level("Postgraduate diploma/degree") == EducationNormalizer.LEVEL_MASTERS

    assert EducationNormalizer.normalize_degree_level("PhD in Machine Learning") == EducationNormalizer.LEVEL_DOCTORATE
    assert EducationNormalizer.normalize_degree_level("Doctor of Philosophy") == EducationNormalizer.LEVEL_DOCTORATE
    assert EducationNormalizer.normalize_degree_level("Doctoral Candidate") == EducationNormalizer.LEVEL_DOCTORATE

    assert EducationNormalizer.normalize_degree_level("Postdoctoral Fellow") == EducationNormalizer.LEVEL_POSTDOCTORAL

    # Worldwide Levels
    assert EducationNormalizer.normalize_degree_level("Matriculation Science") == EducationNormalizer.LEVEL_MATRICULATION
    assert EducationNormalizer.normalize_degree_level("FSc Pre-Engineering") == EducationNormalizer.LEVEL_INTERMEDIATE
    assert EducationNormalizer.normalize_degree_level("A-Levels STEM") == EducationNormalizer.LEVEL_A_LEVELS_IB
    assert EducationNormalizer.normalize_degree_level("DAE Mechanical") == EducationNormalizer.LEVEL_ASSOCIATE
    assert EducationNormalizer.normalize_degree_level("ACCA Member") == EducationNormalizer.LEVEL_PROFESSIONAL
    assert EducationNormalizer.normalize_degree_level("Middle School 8th Grade") == EducationNormalizer.LEVEL_MIDDLE_SCHOOL
    assert EducationNormalizer.normalize_degree_level("Primary School 5th Grade") == EducationNormalizer.LEVEL_PRIMARY
    assert EducationNormalizer.normalize_degree_level("Self-Taught Developer") == EducationNormalizer.LEVEL_NO_FORMAL


def test_education_normalizer_field_taxonomy() -> None:
    field, broad = EducationNormalizer.normalize_field_of_study("Machine Learning")
    assert field == "Machine Learning"
    assert broad == "Computing & Information Technology"

    field, broad = EducationNormalizer.normalize_field_of_study("AI")
    assert field == "Artificial Intelligence"
    assert broad == "Computing & Information Technology"

    field, broad = EducationNormalizer.normalize_field_of_study("Software Engineering")
    assert field == "Software Engineering"
    assert broad == "Computing & Information Technology"


def test_education_normalizer_gpa_conversions() -> None:
    # 4.0 scale
    assert EducationNormalizer.normalize_gpa(3.8, "4.0") == 3.8
    # 5.0 scale
    assert EducationNormalizer.normalize_gpa(4.5, "5.0") == 3.6
    # 10.0 scale
    assert EducationNormalizer.normalize_gpa(8.5, "10.0") == 3.4
    # Percentage
    assert EducationNormalizer.normalize_gpa(None, percentage=85.0) == 3.4


def test_skills_normalizer() -> None:
    res1 = SkillsNormalizer.normalize_skill(
        "python programming", proficiency="Expert", years_of_experience=4.0
    )
    assert res1.normalized_name == "Python"
    assert res1.category == "Programming Languages"
    assert res1.proficiency == "Expert"
    assert res1.years_of_experience == 4.0

    res2 = SkillsNormalizer.normalize_skill("PyTorch", proficiency="Advanced")
    assert res2.normalized_name == "PyTorch"
    assert res2.category == "AI/ML Frameworks"


def test_test_normalizer_validity_and_unknown() -> None:
    today = datetime.now(UTC).date()

    # Valid IELTS (taken 6 months ago)
    valid_ielts = TestNormalizer.normalize_test(
        test_name="IELTS Academic",
        score="7.5",
        test_date=today - timedelta(days=180),
        as_of_date=today,
    )
    assert valid_ielts.status == TestStatus.VALID
    assert valid_ielts.canonical_test_name == "IELTS"

    # Expired IELTS (taken 3 years ago, validity 2 years)
    expired_ielts = TestNormalizer.normalize_test(
        test_name="IELTS",
        score="7.5",
        test_date=today - timedelta(days=800),
        as_of_date=today,
    )
    assert expired_ielts.status == TestStatus.EXPIRED

    # Missing test: MUST be UNKNOWN, NEVER "No"
    missing = TestNormalizer.get_test_status_for_missing("IELTS")
    assert missing.status == TestStatus.UNKNOWN
    assert missing.status != TestStatus.NOT_TAKEN
    assert missing.score is None
