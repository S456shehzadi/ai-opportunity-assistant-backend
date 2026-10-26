import uuid
from typing import Any

from pydantic import BaseModel, Field

from app.models.user import User
from app.schemas.ai_profile import (
    AcademicPerformance,
    EducationRecordItem,
    FundingPreferences,
    GeographicPreferences,
    IdentityContext,
    InformationCompleteness,
    NormalizedAIProfile,
    NormalizedSkillItem,
    NormalizedTestItem,
    OpportunityPreferences,
    ProjectSummary,
    PublicationSummary,
    ResearchExperienceSummary,
    WorkExperienceSummary,
)
from app.services.normalization.education_normalizer import EducationNormalizer
from app.services.normalization.geo_normalizer import GeoNormalizer
from app.services.normalization.skills_normalizer import SkillsNormalizer
from app.services.normalization.test_normalizer import TestNormalizer, TestStatus


class DemographicsSummary(BaseModel):
    nationality: str | None = None
    country_of_residence: str | None = None
    city: str | None = None
    age: int | None = None


class AcademicSummary(BaseModel):
    highest_education_level: str | None = None
    degree_titles: list[str] = Field(default_factory=list)
    fields_of_study: list[str] = Field(default_factory=list)
    institutions: list[str] = Field(default_factory=list)
    normalized_cgpa: float | None = None
    percentage: float | None = None
    all_degrees: list[dict[str, Any]] = Field(default_factory=list)


class StandardizedTestsSummary(BaseModel):
    test_scores: dict[str, str] = Field(default_factory=dict)
    detailed_scores: dict[str, dict[str, Any]] = Field(default_factory=dict)


class ExperienceSummary(BaseModel):
    total_work_years_estimated: float = 0.0
    roles: list[str] = Field(default_factory=list)
    organizations: list[str] = Field(default_factory=list)
    research_areas: list[str] = Field(default_factory=list)
    publication_count: int = 0
    project_count: int = 0


class PreferencesSummary(BaseModel):
    preferred_countries: list[str] = Field(default_factory=list)
    preferred_categories: list[str] = Field(default_factory=list)
    preferred_fields: list[str] = Field(default_factory=list)
    funding_preference: str | None = None


class AIProfileContext(BaseModel):
    """Normalized structured representation consumed by downstream AI orchestration."""

    user_id: uuid.UUID
    email: str
    is_profile_complete: bool = False

    demographics: DemographicsSummary
    academics: AcademicSummary
    standardized_tests: StandardizedTestsSummary
    skills: list[str] = Field(default_factory=list)
    skills_have: list[str] = Field(default_factory=list)
    skills_learning: list[str] = Field(default_factory=list)
    skills_desired: list[str] = Field(default_factory=list)
    primary_field: str | None = None
    secondary_fields: list[str] = Field(default_factory=list)
    specializations: list[str] = Field(default_factory=list)
    career_goals: list[str] = Field(default_factory=list)
    learning_goals: list[str] = Field(default_factory=list)
    headline: str | None = None
    summary: str | None = None
    certifications: list[dict[str, Any]] = Field(default_factory=list)
    languages: dict[str, str] = Field(default_factory=dict)
    experience: ExperienceSummary
    preferences: PreferencesSummary

    # Quick matching lookup signals
    matching_signals: dict[str, Any] = Field(default_factory=dict)


class ProfileNormalizer:
    """Transforms relational user profile entities into an AI-ready context object."""

    @classmethod
    def normalize_ai_profile(cls, user: User) -> NormalizedAIProfile:
        """Transforms relational user profile into a rich NormalizedAIProfile.

        Follows strict accuracy rules:
        - Never invents user information.
        - Never interprets missing info as 'No' (e.g. missing IELTS -> UNKNOWN).
        - Preserves raw user input alongside canonical normalized values.
        """
        profile = user.profile
        prefs = user.preferences

        known_fields: list[str] = ["email"]
        unknown_fields: list[str] = []

        # 1. Identity Context
        nat_info = GeoNormalizer.normalize_country(profile.nationality) if profile else None
        res_info = (
            GeoNormalizer.normalize_country(profile.country_of_residence) if profile else None
        )

        identity = IdentityContext(
            nationality=profile.nationality if profile and profile.nationality else None,
            nationality_country_code=nat_info.code if nat_info else None,
            country_of_residence=(
                profile.country_of_residence if profile and profile.country_of_residence else None
            ),
            residence_country_code=res_info.code if res_info else None,
            city=profile.city if profile and profile.city else None,
            is_known=bool(profile and (profile.nationality or profile.country_of_residence)),
        )
        if identity.nationality:
            known_fields.append("nationality")
        else:
            unknown_fields.append("nationality")

        if identity.country_of_residence:
            known_fields.append("country_of_residence")
        else:
            unknown_fields.append("country_of_residence")

        # 2. Education & Academic Performance
        education_items: list[EducationRecordItem] = []
        highest_level = "Other"

        # If base profile has degree / field
        if profile and (profile.degree_title or profile.field_of_study):
            norm_edu = EducationNormalizer.normalize_education(
                profile.degree_title, profile.field_of_study
            )
            highest_level = norm_edu.normalized_degree_level
            education_items.append(
                EducationRecordItem(
                    raw_degree=profile.degree_title,
                    normalized_degree_level=norm_edu.normalized_degree_level,
                    raw_field=profile.field_of_study,
                    normalized_field=norm_edu.normalized_field,
                    broad_discipline=norm_edu.broad_discipline,
                    institution=profile.university,
                    is_current=False,
                )
            )

        for rec in user.academic_records:
            norm_edu = EducationNormalizer.normalize_education(rec.degree, rec.field_of_study)
            # Prioritize higher level if detected
            if highest_level == "Other" or (
                norm_edu.normalized_degree_level in ("Master's", "Doctorate", "Postdoc")
            ):
                highest_level = norm_edu.normalized_degree_level

            education_items.append(
                EducationRecordItem(
                    raw_degree=rec.degree,
                    normalized_degree_level=norm_edu.normalized_degree_level,
                    raw_field=rec.field_of_study,
                    normalized_field=norm_edu.normalized_field,
                    broad_discipline=norm_edu.broad_discipline,
                    institution=rec.institution,
                    start_year=rec.start_year,
                    end_year=rec.end_year,
                    grade=rec.grade,
                    grading_scale=rec.grading_scale,
                    is_current=bool(rec.is_current),
                )
            )

        if education_items:
            known_fields.append("education")
        else:
            unknown_fields.append("education")

        normalized_gpa = None
        if profile:
            normalized_gpa = EducationNormalizer.normalize_gpa(
                grade=profile.cgpa,
                grading_scale="4.0",
                percentage=profile.percentage,
            )

        academic_perf = AcademicPerformance(
            highest_degree_level=highest_level if highest_level != "Other" else None,
            normalized_gpa_4_scale=normalized_gpa,
            raw_cgpa=profile.cgpa if profile else None,
            raw_percentage=profile.percentage if profile else None,
            academic_achievements=[
                rec.honors_awards
                for rec in user.academic_records
                if getattr(rec, "honors_awards", None)
            ],
        )

        # 3. Standardized Tests (Known vs Unknown - Never "No")
        normalized_tests: dict[str, NormalizedTestItem] = {}
        for test in user.test_results:
            norm_res = TestNormalizer.normalize_test(
                test_name=test.test_name,
                score=test.score,
                score_details=test.score_details,
                test_date=test.test_date,
                expiry_date=test.expiry_date,
            )
            key = norm_res.canonical_test_name.lower().replace(" ", "_")
            normalized_tests[key] = NormalizedTestItem(
                raw_test_name=test.test_name,
                canonical_test_name=norm_res.canonical_test_name,
                test_type=norm_res.test_type,
                score=norm_res.score,
                sub_scores=norm_res.sub_scores,
                test_date=norm_res.test_date,
                expiry_date=norm_res.expiry_date,
                status=norm_res.status,
            )

        # Explicitly check key tests: if not present in user.test_results, record as UNKNOWN
        for _test_key, (canon_name, t_type, _) in TestNormalizer.KNOWN_TESTS.items():
            slug = canon_name.lower().replace(" ", "_")
            if slug not in normalized_tests:
                # Strictly unknown, NEVER "no"
                normalized_tests[slug] = NormalizedTestItem(
                    raw_test_name=canon_name,
                    canonical_test_name=canon_name,
                    test_type=t_type,
                    score=None,
                    status=TestStatus.UNKNOWN,
                )

        if user.test_results:
            known_fields.append("tests")
        else:
            unknown_fields.append("tests")

        # 4. Skills
        normalized_skills: list[NormalizedSkillItem] = []
        skills_have: list[str] = []
        skills_learning: list[str] = []
        skills_desired: list[str] = []
        for s in user.skills:
            status_val = s.status.value if hasattr(s.status, "value") else str(s.status or "have")
            norm_s = SkillsNormalizer.normalize_skill(
                raw_skill=s.name,
                proficiency=s.proficiency.value if s.proficiency else None,
                years_of_experience=s.years_of_experience,
                user_category=s.category,
                status=status_val,
                acquisition_source=getattr(s, "acquisition_source", None),
            )
            normalized_skills.append(
                NormalizedSkillItem(
                    raw_skill=norm_s.raw_skill,
                    normalized_name=norm_s.normalized_name,
                    category=norm_s.category,
                    proficiency=norm_s.proficiency,
                    years_of_experience=norm_s.years_of_experience,
                    status=norm_s.status,
                    acquisition_source=norm_s.acquisition_source,
                )
            )
            if norm_s.status == "have":
                skills_have.append(norm_s.normalized_name)
            elif norm_s.status == "learning":
                skills_learning.append(norm_s.normalized_name)
            elif norm_s.status == "desired":
                skills_desired.append(norm_s.normalized_name)

        # 5. Work & Professional Experience (covering all 12 categories)
        total_work_years = (
            sum(
                ((w.end_date.year - w.start_date.year) if w.end_date and w.start_date else 1.0)
                for w in user.work_experiences
            )
            if user.work_experiences
            else 0.0
        )

        categories_found = list({
            str(getattr(w, "category", "Employment") or "Employment").strip()
            for w in user.work_experiences
        })

        has_intern = any(
            "intern" in getattr(w, "category", "").lower() or "intern" in w.job_title.lower()
            for w in user.work_experiences
        )
        has_volun = any(
            "volunteer" in getattr(w, "category", "").lower()
            or "community" in getattr(w, "category", "").lower()
            for w in user.work_experiences
        )
        has_leader = any(
            "leader" in getattr(w, "category", "").lower()
            or "student" in getattr(w, "category", "").lower()
            or any(term in w.job_title.lower() for term in ("lead", "president", "founder", "head"))
            for w in user.work_experiences
        )
        has_freelance = any(
            cat in getattr(w, "category", "").lower()
            for cat in ("freelance", "entrepreneur", "startup", "contract", "self-employed")
            for w in user.work_experiences
        )
        has_comp = any(
            "competition" in getattr(w, "category", "").lower()
            or "hackathon" in getattr(w, "category", "").lower()
            or any(
                term in str(ach).lower()
                for ach in (getattr(w, "achievements", []) or [])
                for term in ("won", "winner", "award", "hackathon", "competition", "1st place", "first place", "challenge")
            )
            for w in user.work_experiences
        )

        skills_applied = list({
            s for w in user.work_experiences for s in (getattr(w, "skills_used", []) or []) if s
        })

        exp_items = [
            {
                "id": str(w.id),
                "category": getattr(w, "category", "Employment"),
                "job_title": w.job_title,
                "organization": w.organization,
                "employment_type": w.employment_type,
                "industry": getattr(w, "industry", None),
                "city": getattr(w, "city", None),
                "country": w.country,
                "work_arrangement": getattr(w, "work_arrangement", None),
                "start_date": w.start_date.isoformat() if w.start_date else None,
                "end_date": w.end_date.isoformat() if w.end_date else None,
                "is_current": w.is_current,
                "description": w.description,
                "skills_used": getattr(w, "skills_used", []) or [],
                "achievements": getattr(w, "achievements", []) or [],
                "metadata_json": getattr(w, "metadata_json", {}) or {},
            }
            for w in user.work_experiences
        ]

        headline = getattr(profile, "headline", None) if profile else None
        summary = getattr(profile, "summary", None) if profile else None

        work_summary = WorkExperienceSummary(
            total_years=round(max(total_work_years, len(user.work_experiences) * 1.0), 1),
            roles=[w.job_title for w in user.work_experiences],
            organizations=[w.organization for w in user.work_experiences],
            current_role=(next((w.job_title for w in user.work_experiences if w.is_current), None)),
            categories=categories_found,
            has_internship=has_intern,
            has_volunteering=has_volun,
            has_leadership=has_leader,
            has_freelance_or_entrepreneurship=has_freelance,
            has_competition_or_award=has_comp,
            skills_applied=skills_applied,
            experience_items=exp_items,
            headline=headline,
            summary=summary,
        )

        research_summary = ResearchExperienceSummary(
            has_research_experience=len(user.research_experiences) > 0,
            research_areas=[r.research_area for r in user.research_experiences],
            lab_institutions=[r.institution for r in user.research_experiences if r.institution],
        )

        pub_summary = PublicationSummary(
            publication_count=len(user.publications),
            recent_venues=[p.venue for p in user.publications if p.venue],
            doi_list=[p.doi for p in user.publications if p.doi],
        )

        proj_summary = ProjectSummary(
            project_count=len(user.projects),
            technologies_used=[tech for p in user.projects for tech in (p.technologies or [])],
            project_titles=[p.title for p in user.projects],
        )

        # 6. Preferences
        pref_countries = prefs.preferred_countries if prefs else []
        pref_country_codes = []
        pref_regions = []
        for c in pref_countries:
            c_info = GeoNormalizer.normalize_country(c)
            if c_info:
                pref_country_codes.append(c_info.code)
            reg = GeoNormalizer.normalize_region(c)
            if reg:
                pref_regions.append(reg)

        geo_prefs = GeographicPreferences(
            preferred_countries=pref_countries,
            preferred_country_codes=pref_country_codes,
            preferred_regions=pref_regions,
        )

        pref_cats = (prefs.preferred_opportunity_categories if prefs else []) or []
        pref_fields = (prefs.preferred_fields if prefs else []) or []
        opp_prefs = OpportunityPreferences(
            preferred_categories=pref_cats,
            preferred_fields=pref_fields,
            study_levels=getattr(prefs, "study_levels", []) or [],
        )

        fund_prefs = FundingPreferences(
            funding_requirement=prefs.funding_preference if prefs else None,
            requires_visa_sponsorship=getattr(prefs, "requires_visa_sponsorship", None),
        )

        # Completeness Audit
        missing_critical: list[str] = []
        if not identity.nationality:
            missing_critical.append("nationality")
        if not academic_perf.highest_degree_level:
            missing_critical.append("degree_level")

        completeness = InformationCompleteness(
            is_profile_complete=len(missing_critical) == 0,
            known_fields=known_fields,
            unknown_fields=unknown_fields,
            missing_critical_signals=missing_critical,
        )

        # Certifications
        cert_items: list[dict[str, Any]] = []
        for c in getattr(user, "certifications", []):
            cert_items.append({
                "id": str(c.id),
                "title": c.title,
                "issuing_organization": c.issuing_organization,
                "category": c.category,
                "status": c.status,
                "credential_id": c.credential_id,
                "skills": c.skills or [],
            })

        primary_field = getattr(profile, "primary_field", None) if profile else None
        secondary_fields = (getattr(profile, "secondary_fields", None) or []) if profile else []
        specializations = (getattr(profile, "specializations", None) or []) if profile else []
        career_goals = (getattr(profile, "career_goals", None) or []) if profile else []
        learning_goals = (getattr(profile, "learning_goals", None) or []) if profile else []

        # Quick matching lookup signals
        matching_signals = {
            "eligible_nationalities": [nat for nat in [identity.nationality, "Global"] if nat],
            "residence": identity.country_of_residence,
            "residence_code": identity.residence_country_code,
            "highest_degree": academic_perf.highest_degree_level,
            "fields": [e.normalized_field for e in education_items if e.normalized_field],
            "primary_field": primary_field,
            "specializations": specializations,
            "career_goals": career_goals,
            "headline": headline,
            "summary": summary,
            "gpa_4_scale": academic_perf.normalized_gpa_4_scale,
            "has_publications": pub_summary.publication_count > 0,
            "skills": [s.normalized_name for s in normalized_skills],
            "skills_have": skills_have,
            "skills_learning": skills_learning,
            "skills_desired": skills_desired,
            "experience_categories": work_summary.categories,
            "has_internship": work_summary.has_internship,
            "has_volunteering": work_summary.has_volunteering,
            "has_leadership": work_summary.has_leadership,
            "has_freelance": work_summary.has_freelance_or_entrepreneurship,
            "skills_applied": work_summary.skills_applied,
            "valid_tests": [
                t.canonical_test_name
                for t in normalized_tests.values()
                if t.status in (TestStatus.VALID, TestStatus.TAKEN)
            ],
            "preferred_countries": geo_prefs.preferred_countries,
            "acceptable_countries": getattr(prefs, "acceptable_countries", []) or [],
            "preferred_regions": geo_prefs.preferred_regions,
            "discovery_mode": getattr(prefs, "discovery_mode", "flexible") or "flexible",
            "citizenships": getattr(profile, "citizenships", []) or ([identity.nationality] if identity.nationality else []),
            "previous_education_country": getattr(profile, "previous_education_country", None),
            "willing_to_travel": getattr(prefs, "willing_to_travel", True),
            "open_to_remote": getattr(prefs, "open_to_remote", True),
            "preferred_categories": pref_cats,
            "target_degree_levels": getattr(prefs, "target_degree_levels", []) or [],
            "excluded_countries": getattr(prefs, "excluded_countries", []) or [],
            "willing_to_relocate": getattr(prefs, "willing_to_relocate", True),
            "funding_types": getattr(prefs, "funding_types", []) or [],
            "funding_priorities": getattr(prefs, "funding_priorities", []) or [],
            "max_annual_tuition": getattr(prefs, "max_annual_tuition", None),
            "financial_currency": getattr(prefs, "financial_currency", "USD"),
            "requires_no_application_fee": getattr(prefs, "requires_no_application_fee", False),
            "requires_no_ielts": getattr(prefs, "requires_no_ielts", False),
            "language_preferences": getattr(prefs, "language_preferences", []) or [],
            "language_test_status": getattr(prefs, "language_test_status", {}) or {},
            "admission_test_status": getattr(prefs, "admission_test_status", {}) or {},
            "study_formats": getattr(prefs, "study_formats", []) or [],
            "duration_preferences": getattr(prefs, "duration_preferences", []) or [],
            "preferred_start_terms": getattr(prefs, "preferred_start_terms", []) or [],
            "career_priorities": getattr(prefs, "career_priorities", []) or [],
            "hard_constraints": getattr(prefs, "hard_constraints", []) or [],
        }

        return NormalizedAIProfile(
            user_id=user.id or uuid.uuid4(),
            email=user.email,
            identity_context=identity,
            education=education_items,
            academic_performance=academic_perf,
            tests=normalized_tests,
            skills=normalized_skills,
            primary_field=primary_field,
            secondary_fields=secondary_fields,
            specializations=specializations,
            career_goals=career_goals,
            learning_goals=learning_goals,
            headline=headline,
            summary=summary,
            certifications=cert_items,
            skills_have=skills_have,
            skills_learning=skills_learning,
            skills_desired=skills_desired,
            languages={lang.language_name: lang.proficiency.value for lang in user.languages},
            work_experience=work_summary,
            research_experience=research_summary,
            publications=pub_summary,
            projects=proj_summary,
            geographic_preferences=geo_prefs,
            opportunity_preferences=opp_prefs,
            funding_preferences=fund_prefs,
            completeness=completeness,
            matching_signals=matching_signals,
        )

    @classmethod
    def normalize(cls, user: User) -> AIProfileContext:
        """Original compact context representation for existing orchestration endpoints."""
        rich_profile = cls.normalize_ai_profile(user)

        demographics = DemographicsSummary(
            nationality=rich_profile.identity_context.nationality,
            country_of_residence=rich_profile.identity_context.country_of_residence,
            city=rich_profile.identity_context.city,
        )

        fields = list({e.raw_field for e in rich_profile.education if e.raw_field})
        degrees = list({e.raw_degree for e in rich_profile.education if e.raw_degree})
        institutions = list({e.institution for e in rich_profile.education if e.institution})

        all_degrees_data = [
            {
                "institution": e.institution,
                "degree": e.raw_degree,
                "field_of_study": e.raw_field,
                "start_year": e.start_year,
                "end_year": e.end_year,
                "grade": e.grade,
                "grading_scale": e.grading_scale,
                "is_current": e.is_current,
            }
            for e in rich_profile.education
        ]

        academics = AcademicSummary(
            highest_education_level=rich_profile.academic_performance.highest_degree_level,
            degree_titles=degrees,
            fields_of_study=fields,
            institutions=institutions,
            normalized_cgpa=rich_profile.academic_performance.raw_cgpa,
            percentage=rich_profile.academic_performance.raw_percentage,
            all_degrees=all_degrees_data,
        )

        test_scores: dict[str, str] = {}
        detailed_scores: dict[str, dict[str, Any]] = {}
        for test in user.test_results:
            if test.score:
                test_scores[test.test_name] = test.score
                if test.score_details:
                    detailed_scores[test.test_name] = test.score_details
        for t in rich_profile.tests.values():
            if t.score is not None:
                test_scores[t.canonical_test_name] = t.score
                if t.sub_scores:
                    detailed_scores[t.canonical_test_name] = t.sub_scores

        standardized_tests = StandardizedTestsSummary(
            test_scores=test_scores,
            detailed_scores=detailed_scores,
        )

        experience = ExperienceSummary(
            total_work_years_estimated=rich_profile.work_experience.total_years,
            roles=rich_profile.work_experience.roles,
            organizations=rich_profile.work_experience.organizations,
            research_areas=rich_profile.research_experience.research_areas,
            publication_count=rich_profile.publications.publication_count,
            project_count=rich_profile.projects.project_count,
        )

        preferences = PreferencesSummary(
            preferred_countries=rich_profile.geographic_preferences.preferred_countries,
            preferred_categories=rich_profile.opportunity_preferences.preferred_categories,
            preferred_fields=rich_profile.opportunity_preferences.preferred_fields,
            funding_preference=rich_profile.funding_preferences.funding_requirement,
        )

        return AIProfileContext(
            user_id=rich_profile.user_id,
            email=rich_profile.email,
            is_profile_complete=rich_profile.completeness.is_profile_complete,
            demographics=demographics,
            academics=academics,
            standardized_tests=standardized_tests,
            skills=[s.normalized_name for s in rich_profile.skills],
            skills_have=rich_profile.skills_have,
            skills_learning=rich_profile.skills_learning,
            skills_desired=rich_profile.skills_desired,
            primary_field=rich_profile.primary_field,
            secondary_fields=rich_profile.secondary_fields,
            specializations=rich_profile.specializations,
            career_goals=rich_profile.career_goals,
            learning_goals=rich_profile.learning_goals,
            headline=rich_profile.headline,
            summary=rich_profile.summary,
            certifications=rich_profile.certifications,
            languages=rich_profile.languages,
            experience=experience,
            preferences=preferences,
            matching_signals=rich_profile.matching_signals,
        )
