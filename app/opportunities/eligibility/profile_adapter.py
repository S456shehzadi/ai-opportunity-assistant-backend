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
    experience_categories: list[str] = Field(default_factory=list)
    has_internship: bool = False
    has_volunteering: bool = False
    has_leadership: bool = False
    has_freelance: bool = False
    has_competitions: bool = False
    skills_applied: list[str] = Field(default_factory=list)
    experience_items: list[dict[str, Any]] = Field(default_factory=list)
    headline: str | None = None
    summary: str | None = None

    # Skills & Languages
    skills: list[str] = Field(default_factory=list)
    skills_have: list[str] = Field(default_factory=list)
    skills_learning: list[str] = Field(default_factory=list)
    skills_desired: list[str] = Field(default_factory=list)
    primary_field: str | None = None
    secondary_fields: list[str] = Field(default_factory=list)
    specializations: list[str] = Field(default_factory=list)
    career_goals: list[str] = Field(default_factory=list)
    learning_goals: list[str] = Field(default_factory=list)
    certifications: list[dict[str, Any]] = Field(default_factory=list)
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

        we = profile.work_experience
        headline = profile.headline or getattr(we, "headline", None)
        summary = profile.summary or getattr(we, "summary", None)

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
            work_experience_years=we.total_years,
            has_research_experience=profile.research_experience.has_research_experience,
            publication_count=profile.publications.publication_count,
            experience_categories=getattr(we, "categories", []),
            has_internship=getattr(we, "has_internship", False),
            has_volunteering=getattr(we, "has_volunteering", False),
            has_leadership=getattr(we, "has_leadership", False),
            has_freelance=getattr(we, "has_freelance_or_entrepreneurship", False),
            has_competitions=getattr(we, "has_competition_or_award", False),
            skills_applied=getattr(we, "skills_applied", []),
            experience_items=getattr(we, "experience_items", []),
            headline=headline,
            summary=summary,
            skills=[s.normalized_name for s in profile.skills],
            skills_have=profile.skills_have,
            skills_learning=profile.skills_learning,
            skills_desired=profile.skills_desired,
            primary_field=profile.primary_field,
            secondary_fields=profile.secondary_fields,
            specializations=profile.specializations,
            career_goals=profile.career_goals,
            learning_goals=profile.learning_goals,
            certifications=profile.certifications,
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

        # Experience extraction
        raw_exp = data.get("work_experience") or data.get("experiences") or []
        exp_categories: list[str] = list(data.get("experience_categories") or [])
        skills_applied: list[str] = list(data.get("skills_applied") or [])
        exp_items: list[dict[str, Any]] = []

        if isinstance(raw_exp, list):
            for e in raw_exp:
                e_dict = e if isinstance(e, dict) else (e.model_dump() if hasattr(e, "model_dump") else {})
                exp_items.append(e_dict)
                cat = e_dict.get("category")
                if cat and cat not in exp_categories:
                    exp_categories.append(cat)
                for sk in e_dict.get("skills_used", []) or e_dict.get("skills", []):
                    if sk and sk not in skills_applied:
                        skills_applied.append(sk)
        elif isinstance(raw_exp, dict):
            exp_categories = raw_exp.get("categories", exp_categories)
            skills_applied = raw_exp.get("skills_applied", skills_applied)
            exp_items = raw_exp.get("experience_items", [])

        has_internship = data.get("has_internship", any("intern" in c.lower() for c in exp_categories))
        has_volunteering = data.get("has_volunteering", any("volunt" in c.lower() or "community" in c.lower() for c in exp_categories))
        has_leadership = data.get("has_leadership", any("lead" in c.lower() or "student" in c.lower() for c in exp_categories))
        has_freelance = data.get("has_freelance", any("freelance" in c.lower() or "startup" in c.lower() or "entrepreneur" in c.lower() for c in exp_categories))
        has_competitions = data.get("has_competitions", any("compet" in c.lower() or "hackathon" in c.lower() for c in exp_categories))

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
            experience_categories=exp_categories,
            has_internship=has_internship,
            has_volunteering=has_volunteering,
            has_leadership=has_leadership,
            has_freelance=has_freelance,
            has_competitions=has_competitions,
            skills_applied=skills_applied,
            experience_items=exp_items,
            headline=data.get("headline"),
            summary=data.get("summary"),
            skills=data.get("skills", []),
            skills_have=data.get("skills_have", []),
            skills_learning=data.get("skills_learning", []),
            skills_desired=data.get("skills_desired", []),
            primary_field=data.get("primary_field"),
            secondary_fields=data.get("secondary_fields", []),
            specializations=data.get("specializations", []),
            career_goals=data.get("career_goals", []),
            learning_goals=data.get("learning_goals", []),
            certifications=data.get("certifications", []),
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
            deg = (
                getattr(r, "education_level", None)
                or getattr(r, "degree_level", None)
                or getattr(r, "degree_title", None)
                or getattr(r, "degree", None)
            )
            records.append(
                {
                    "normalized_degree_level": deg,
                    "degree_title": getattr(r, "degree", None) or getattr(r, "degree_title", None),
                    "field_of_study": getattr(r, "field_of_study", None),
                    "academic_stream": getattr(r, "academic_stream", None),
                    "status": getattr(r, "status", None),
                    "cgpa": getattr(r, "cgpa", None) or getattr(r, "grade", None),
                    "percentage": getattr(r, "percentage", None),
                    "institution": getattr(r, "institution", None),
                    "country": getattr(r, "country", None),
                    "is_current": getattr(r, "is_current", False),
                    "is_highest": getattr(r, "is_highest", False),
                }
            )

        # Also add summary from user_profile itself if present
        if getattr(db_profile, "degree_title", None) or getattr(
            db_profile, "education_level", None
        ) or getattr(db_profile, "current_education_level", None):
            records.append(
                {
                    "normalized_degree_level": getattr(db_profile, "current_education_level", None)
                    or getattr(db_profile, "education_level", None),
                    "degree_title": getattr(db_profile, "degree_title", None),
                    "field_of_study": getattr(db_profile, "field_of_study", None),
                    "status": getattr(db_profile, "education_status", None),
                    "cgpa": getattr(db_profile, "cgpa", None),
                    "percentage": getattr(db_profile, "percentage", None),
                    "institution": getattr(db_profile, "university", None),
                }
            )

        # Extract skills if relationship exists on user
        db_user = getattr(db_profile, "user", None)
        skills_have: list[str] = []
        skills_learning: list[str] = []
        skills_desired: list[str] = []
        all_skills: list[str] = []
        if db_user and hasattr(db_user, "skills"):
            for s in db_user.skills:
                all_skills.append(s.name)
                st = s.status.value if hasattr(s.status, "value") else str(s.status or "have")
                if st == "have":
                    skills_have.append(s.name)
                elif st == "learning":
                    skills_learning.append(s.name)
                elif st == "desired":
                    skills_desired.append(s.name)

        # Extract work experiences
        work_exps = getattr(db_profile, "work_experiences", []) or (
            getattr(db_user, "work_experiences", []) if db_user else []
        )
        exp_categories: list[str] = []
        skills_applied: list[str] = []
        exp_items: list[dict[str, Any]] = []
        total_exp_years = 0.0

        for wexp in work_exps:
            cat = getattr(wexp, "category", "Employment") or "Employment"
            if cat not in exp_categories:
                exp_categories.append(cat)
            s_date = getattr(wexp, "start_date", None)
            e_date = getattr(wexp, "end_date", None)
            is_cur = getattr(wexp, "is_current", False)
            if s_date:
                end_calc = e_date or (datetime.now(UTC).date() if is_cur else s_date)
                dur_years = max(0.0, (end_calc.year - s_date.year) + (end_calc.month - s_date.month) / 12.0)
                total_exp_years += dur_years

            item_dict = {
                "id": str(getattr(wexp, "id", "")),
                "title": getattr(wexp, "job_title", ""),
                "organization": getattr(wexp, "organization", ""),
                "category": cat,
                "industry": getattr(wexp, "industry", None),
                "is_current": is_cur,
                "achievements": getattr(wexp, "achievements", []) or [],
            }
            exp_items.append(item_dict)

        has_intern = any("intern" in c.lower() for c in exp_categories)
        has_volun = any("volunt" in c.lower() or "community" in c.lower() for c in exp_categories)
        has_leader = any("lead" in c.lower() or "student" in c.lower() for c in exp_categories)
        has_freelance = any("freelance" in c.lower() or "startup" in c.lower() or "entrepreneur" in c.lower() for c in exp_categories)
        has_comp = any("compet" in c.lower() or "hackathon" in c.lower() for c in exp_categories)

        return UnifiedUserFacts(
            user_id=user_id,
            nationality=getattr(db_profile, "nationality", None),
            country_of_residence=getattr(db_profile, "country_of_residence", None),
            city=getattr(db_profile, "city", None),
            date_of_birth=dob,
            age=age,
            academic_records=records,
            work_experience_years=round(total_exp_years, 1),
            experience_categories=exp_categories,
            has_internship=has_intern,
            has_volunteering=has_volun,
            has_leadership=has_leader,
            has_freelance=has_freelance,
            has_competitions=has_comp,
            skills_applied=skills_applied,
            experience_items=exp_items,
            headline=getattr(db_profile, "headline", None),
            summary=getattr(db_profile, "summary", None),
            primary_field=getattr(db_profile, "primary_field", None),
            secondary_fields=getattr(db_profile, "secondary_fields", None) or [],
            specializations=getattr(db_profile, "specializations", None) or [],
            career_goals=getattr(db_profile, "career_goals", None) or [],
            learning_goals=getattr(db_profile, "learning_goals", None) or [],
            skills=all_skills,
            skills_have=skills_have,
            skills_learning=skills_learning,
            skills_desired=skills_desired,
            highest_cgpa=getattr(db_profile, "cgpa", None),
            highest_percentage=getattr(db_profile, "percentage", None),
            source_records={"model": "UserProfile"},
        )
