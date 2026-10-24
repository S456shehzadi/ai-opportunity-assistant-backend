"""Profile adapter translating various user profile representations into unified facts."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.ai_profile import NormalizedAIProfile


class UnifiedUserFacts(BaseModel):
    """Canonical facts extracted from a user profile for eligibility matching."""

    user_id: str
    email: str = ""
    nationality: str | None = None
    nationality_country_code: str | None = None
    country_of_residence: str | None = None
    residence_country_code: str | None = None
    city: str | None = None

    date_of_birth: date | None = None
    age: int | None = None

    # Education records (supports multiple degrees)
    academic_records: list[dict[str, Any]] = Field(default_factory=list)
    highest_degree_level: str | None = None
    normalized_gpa_4_scale: float | None = None
    highest_cgpa: float | None = None
    highest_percentage: float | None = None
    has_english_medium_degree: bool = False

    # Standardized tests
    tests: dict[str, dict[str, Any]] = Field(default_factory=dict)

    # Experience
    work_experience_years: float = 0.0
    has_research_experience: bool = False
    publication_count: int = 0

    # Skills & Languages
    skills: list[str] = Field(default_factory=list)
    languages: dict[str, str] = Field(default_factory=dict)

    # Raw sources for evidence
    source_records: dict[str, Any] = Field(default_factory=dict)


class ProfileAdapter:
    """Extracts unified, verifiable facts from NormalizedAIProfile or raw DB models."""

    @classmethod
    def adapt(cls, profile: NormalizedAIProfile | Any) -> UnifiedUserFacts:
        """Adapts any profile instance into UnifiedUserFacts."""
        if isinstance(profile, NormalizedAIProfile):
            return cls._from_normalized_ai_profile(profile)
        if isinstance(profile, dict):
            return cls._from_dict(profile)
        # Fallback for SQLAlchemy UserProfile model
        return cls._from_db_model(profile)

    @classmethod
    def _from_normalized_ai_profile(cls, profile: NormalizedAIProfile) -> UnifiedUserFacts:
        user_id = str(profile.user_id)
        email = profile.email
        ident = profile.identity_context

        # Calculate exact age if DOB is provided
        age = None
        dob = getattr(ident, "date_of_birth", None)
        if dob:
            today = datetime.now(UTC).date()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

        # Academic records
        academic_records: list[dict[str, Any]] = []
        has_emi = False
        gpas: list[float] = []
        percentages: list[float] = []

        for edu in profile.education:
            rec = edu.model_dump()
            # If specified in record or metadata
            if edu.grade:
                try:
                    val = float(edu.grade)
                    if (edu.grading_scale or "") == "4.0" or val <= 4.0:
                        gpas.append(val)
                    elif val > 10.0:
                        percentages.append(val)
                except ValueError:
                    pass
            academic_records.append(rec)

        # Check for English medium degree declared in languages or profile
        if "English" in profile.languages and profile.languages.get("English") in (
            "Native/Bilingual",
            "Fluent",
        ):
            # Check matching signals or education for explicit EMI
            has_emi = bool(profile.matching_signals.get("english_medium_education", False))
        if profile.matching_signals.get("english_medium_education"):
            has_emi = True

        # Tests
        test_dict: dict[str, dict[str, Any]] = {}
        for test_key, test_item in profile.tests.items():
            test_dict[test_key.upper()] = test_item.model_dump()

        perf = profile.academic_performance
        highest_cgpa = perf.raw_cgpa or (max(gpas) if gpas else None)
        highest_pct = perf.raw_percentage or (max(percentages) if percentages else None)

        return UnifiedUserFacts(
            user_id=user_id,
            email=email,
            nationality=ident.nationality,
            nationality_country_code=ident.nationality_country_code,
            country_of_residence=ident.country_of_residence,
            residence_country_code=ident.residence_country_code,
            city=ident.city,
            date_of_birth=dob,
            age=age,
            academic_records=academic_records,
            highest_degree_level=perf.highest_degree_level,
            normalized_gpa_4_scale=perf.normalized_gpa_4_scale,
            highest_cgpa=highest_cgpa,
            highest_percentage=highest_pct,
            has_english_medium_degree=has_emi,
            tests=test_dict,
            work_experience_years=profile.work_experience.total_years,
            has_research_experience=profile.research_experience.has_research_experience,
            publication_count=profile.publications.publication_count,
            skills=[s.normalized_name for s in profile.skills],
            languages=dict(profile.languages),
            source_records={"profile_type": "NormalizedAIProfile"},
        )

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> UnifiedUserFacts:
        user_id = str(data.get("user_id", uuid.uuid4()))
        email = data.get("email", "")
        ident = data.get("identity_context", {})

        dob = data.get("date_of_birth") or ident.get("date_of_birth")
        age = data.get("age")
        if dob and isinstance(dob, str):
            try:
                dob = datetime.strptime(dob, "%Y-%m-%d").date()
            except ValueError:
                dob = None
        if dob and age is None:
            today = datetime.now(UTC).date()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

        # Academic records
        raw_edu = data.get("academic_records") or data.get("education") or []
        records: list[dict[str, Any]] = []
        for item in raw_edu:
            if isinstance(item, dict):
                records.append(item)
            elif hasattr(item, "model_dump"):
                records.append(item.model_dump())

        # Test dictionary
        raw_tests = data.get("tests", {})
        tests_clean: dict[str, dict[str, Any]] = {}
        if isinstance(raw_tests, dict):
            for k, v in raw_tests.items():
                tests_clean[k.upper()] = v if isinstance(v, dict) else v.model_dump()
        elif isinstance(raw_tests, list):
            for t in raw_tests:
                t_dict = t if isinstance(t, dict) else t.model_dump()
                name = t_dict.get("test_name") or t_dict.get("canonical_test_name") or "UNKNOWN"
                tests_clean[name.upper()] = t_dict

        return UnifiedUserFacts(
            user_id=user_id,
            email=email,
            nationality=data.get("nationality") or ident.get("nationality"),
            nationality_country_code=data.get("nationality_country_code")
            or ident.get("nationality_country_code"),
            country_of_residence=data.get("country_of_residence")
            or ident.get("country_of_residence"),
            residence_country_code=data.get("residence_country_code")
            or ident.get("residence_country_code"),
            city=data.get("city") or ident.get("city"),
            date_of_birth=dob,
            age=age,
            academic_records=records,
            highest_degree_level=data.get("highest_degree_level"),
            normalized_gpa_4_scale=data.get("normalized_gpa_4_scale"),
            highest_cgpa=data.get("highest_cgpa") or data.get("cgpa"),
            highest_percentage=data.get("highest_percentage") or data.get("percentage"),
            has_english_medium_degree=data.get("has_english_medium_degree", False),
            tests=tests_clean,
            work_experience_years=data.get("work_experience_years", 0.0),
            has_research_experience=data.get("has_research_experience", False),
            publication_count=data.get("publication_count", 0),
            skills=data.get("skills", []),
            languages=data.get("languages", {}),
            source_records=data,
        )

    @classmethod
    def _from_db_model(cls, db_profile: Any) -> UnifiedUserFacts:
        """Adapts SQLAlchemy UserProfile."""
        user_id = str(getattr(db_profile, "user_id", getattr(db_profile, "id", uuid.uuid4())))
        dob = getattr(db_profile, "date_of_birth", None)
        age = None
        if dob:
            today = datetime.now(UTC).date()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

        records: list[dict[str, Any]] = []
        # If user has academic records relationship
        db_records = getattr(db_profile, "academic_records", []) or getattr(
            getattr(db_profile, "user", None), "academic_records", []
        )
        for r in db_records:
            records.append(
                {
                    "normalized_degree_level": getattr(r, "degree_level", None)
                    or getattr(r, "degree_title", None),
                    "degree_title": getattr(r, "degree_title", None),
                    "field_of_study": getattr(r, "field_of_study", None),
                    "cgpa": getattr(r, "cgpa", None),
                    "percentage": getattr(r, "percentage", None),
                    "institution": getattr(r, "institution", None),
                }
            )

        # Also add summary from user_profile itself if present
        if getattr(db_profile, "degree_title", None) or getattr(
            db_profile, "education_level", None
        ):
            records.append(
                {
                    "normalized_degree_level": getattr(db_profile, "education_level", None),
                    "degree_title": getattr(db_profile, "degree_title", None),
                    "field_of_study": getattr(db_profile, "field_of_study", None),
                    "cgpa": getattr(db_profile, "cgpa", None),
                    "percentage": getattr(db_profile, "percentage", None),
                    "institution": getattr(db_profile, "university", None),
                }
            )

        return UnifiedUserFacts(
            user_id=user_id,
            nationality=getattr(db_profile, "nationality", None),
            country_of_residence=getattr(db_profile, "country_of_residence", None),
            city=getattr(db_profile, "city", None),
            date_of_birth=dob,
            age=age,
            academic_records=records,
            highest_cgpa=getattr(db_profile, "cgpa", None),
            highest_percentage=getattr(db_profile, "percentage", None),
            source_records={"model": "UserProfile"},
        )
