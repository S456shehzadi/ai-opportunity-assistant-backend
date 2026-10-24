"""Synthetic user profiles and opportunities for eligibility testing.

Covers Scenarios A through F:
- Scenario A: Clearly matching profile and opportunity (CLEARLY_ELIGIBLE).
- Scenario B: Clear mismatch (e.g. CGPA 2.50 < 3.00 -> CLEARLY_NOT_ELIGIBLE).
- Scenario C: Unknown requirement (IELTS required, not provided -> POTENTIALLY_ELIGIBLE, never NO_MATCH).
- Scenario D: Conditional waiver (IELTS required unless EMI, user has EMI verified -> MATCH via waiver).
- Scenario E: Conflicting information (contradictory records / sources -> CONFLICTING_INFORMATION).
- Scenario F: Missing demographic facts (restricted nationality, user unmentioned -> UNKNOWN).
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from app.opportunities.extraction.evidence import Evidence
from app.opportunities.extraction.schemas import (
    ExtractedField,
    ExtractedLanguageRequirement,
    ExtractedOpportunity,
    OpportunityCategory,
    SourceTrustType,
)
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

FIXED_NOW = datetime(2026, 9, 24, 0, 0, 0, tzinfo=UTC)

# ---------------------------------------------------------------------------
# Synthetic User Profiles
# ---------------------------------------------------------------------------

USER_PROFILE_A_DICT = {
    "user_id": str(uuid.uuid4()),
    "email": "ahmed.cs@example.com",
    "nationality": "Pakistan",
    "nationality_country_code": "PK",
    "country_of_residence": "Pakistan",
    "residence_country_code": "PK",
    "city": "Lahore",
    "date_of_birth": "2001-05-15",
    "highest_degree_level": "Bachelor's",
    "highest_cgpa": 3.65,
    "normalized_gpa_4_scale": 3.65,
    "highest_percentage": 88.0,
    "has_english_medium_degree": True,
    "work_experience_years": 2.5,
    "has_research_experience": True,
    "publication_count": 1,
    "skills": ["Python", "FastAPI", "Machine Learning"],
    "languages": {"English": "Fluent", "Urdu": "Native/Bilingual"},
    "academic_records": [
        {
            "degree_title": "Bachelor of Science in Computer Science",
            "normalized_degree_level": "Bachelor's",
            "field_of_study": "Computer Science",
            "normalized_field": "Computer Science",
            "institution": "National University of Sciences and Technology",
            "cgpa": 3.65,
            "grading_scale": "4.0",
            "medium_of_instruction": "English",
        }
    ],
    "tests": {
        "IELTS": {
            "test_name": "IELTS",
            "score": "7.5",
            "test_date": "2025-06-10",
            "is_valid": True,
        }
    },
}

USER_PROFILE_B_LOW_CGPA_DICT = {
    "user_id": str(uuid.uuid4()),
    "email": "low.cgpa@example.com",
    "nationality": "Pakistan",
    "nationality_country_code": "PK",
    "country_of_residence": "Pakistan",
    "residence_country_code": "PK",
    "highest_degree_level": "Bachelor's",
    "highest_cgpa": 2.50,
    "normalized_gpa_4_scale": 2.50,
    "academic_records": [
        {
            "degree_title": "Bachelor of Science in Computer Science",
            "normalized_degree_level": "Bachelor's",
            "field_of_study": "Computer Science",
            "cgpa": 2.50,
            "grading_scale": "4.0",
        }
    ],
    "tests": {
        "IELTS": {
            "test_name": "IELTS",
            "score": "6.0",
        }
    },
}

USER_PROFILE_C_MISSING_TEST_DICT = {
    "user_id": str(uuid.uuid4()),
    "email": "notest@example.com",
    "nationality": "Pakistan",
    "country_of_residence": "Pakistan",
    "highest_degree_level": "Bachelor's",
    "highest_cgpa": 3.75,
    "normalized_gpa_4_scale": 3.75,
    "academic_records": [
        {
            "degree_title": "Bachelor of Science in Electrical Engineering",
            "normalized_degree_level": "Bachelor's",
            "field_of_study": "Electrical Engineering",
            "cgpa": 3.75,
        }
    ],
    # No test scores provided
    "tests": {},
    "has_english_medium_degree": False,
}

USER_PROFILE_D_CONDITIONAL_EMI_DICT = {
    "user_id": str(uuid.uuid4()),
    "email": "emi.user@example.com",
    "nationality": "Pakistan",
    "country_of_residence": "Pakistan",
    "highest_degree_level": "Bachelor's",
    "highest_cgpa": 3.40,
    "normalized_gpa_4_scale": 3.40,
    "academic_records": [
        {
            "degree_title": "Bachelor of Science in Software Engineering",
            "normalized_degree_level": "Bachelor's",
            "field_of_study": "Software Engineering",
            "cgpa": 3.40,
            "medium_of_instruction": "English",
        }
    ],
    "tests": {},  # No IELTS test taken
    "has_english_medium_degree": True,  # English-medium degree verified
}

USER_PROFILE_E_CONFLICTING_DICT = {
    "user_id": str(uuid.uuid4()),
    "email": "conflicting@example.com",
    "nationality": "Pakistan",
    "country_of_residence": "Pakistan",
    "highest_degree_level": "Bachelor's",
    "highest_cgpa": 3.80,
    "academic_records": [
        {
            "degree_title": "Bachelor of Science in CS",
            "normalized_degree_level": "Bachelor's",
            "field_of_study": "Computer Science",
            "cgpa": 3.80,
        },
        {
            "degree_title": "Bachelor of Science in CS",
            "normalized_degree_level": "Bachelor's",
            "field_of_study": "Computer Science",
            "cgpa": 2.10,  # Same degree level and field with conflicting GPA!
        },
    ],
}

USER_PROFILE_F_UNKNOWN_NATIONALITY_DICT = {
    "user_id": str(uuid.uuid4()),
    "email": "unknown.nat@example.com",
    "nationality": None,  # Nationality unmentioned
    "nationality_country_code": None,
    "highest_degree_level": "Bachelor's",
    "highest_cgpa": 3.90,
    "normalized_gpa_4_scale": 3.90,
    "academic_records": [
        {
            "degree_title": "Bachelor of Arts in Economics",
            "normalized_degree_level": "Bachelor's",
            "field_of_study": "Economics",
            "cgpa": 3.90,
        }
    ],
    "tests": {
        "IELTS": {
            "test_name": "IELTS",
            "score": "7.5",
        }
    },
}

# ---------------------------------------------------------------------------
# Synthetic Opportunities
# ---------------------------------------------------------------------------

OPPORTUNITY_A_STANDARD_DICT = {
    "id": str(uuid.uuid4()),
    "title": "Global Excellence Master Scholarship 2027",
    "degree_levels": ["Master's"],
    "minimum_cgpa": 3.0,
    "fields_of_study": ["Computer Science", "Software Engineering", "Data Science"],
    "eligible_nationalities": ["Pakistan", "India", "Bangladesh"],
    "ielts": 6.5,
    "ielts_waiver_allowed": False,
    "deadline": "2027-08-31",
}

OPPORTUNITY_B_STRICT_CGPA_DICT = {
    "id": str(uuid.uuid4()),
    "title": "High Honor Fellowship",
    "degree_levels": ["Master's"],
    "minimum_cgpa": 3.2,
    "fields_of_study": ["Computer Science"],
    "deadline": "2027-09-30",
}

OPPORTUNITY_C_MANDATORY_IELTS_DICT = {
    "id": str(uuid.uuid4()),
    "title": "Oxford Advanced Research Award",
    "degree_levels": ["Master's", "PhD"],
    "minimum_cgpa": 3.5,
    "ielts": 7.0,
    "ielts_waiver_allowed": False,
    "deadline": "2027-10-15",
}

OPPORTUNITY_D_WAIVER_ALLOWED_DICT = {
    "id": str(uuid.uuid4()),
    "title": "Technical University Master Grant",
    "degree_levels": ["Master's"],
    "minimum_cgpa": 3.0,
    "ielts": 6.5,
    "ielts_waiver_allowed": True,
    "ielts_waiver_conditions": "Applicants with a prior degree instructed in English are exempt.",
    "deadline": "2027-11-01",
}

OPPORTUNITY_E_CONFLICTING_DICT = {
    "id": str(uuid.uuid4()),
    "title": "Disputed Grant Program",
    "degree_levels": ["Master's"],
    "minimum_cgpa": 3.0,
    "conflicts": ["Discrepancy in minimum CGPA: Source A states 3.0 while Source B states 3.5."],
    "deadline": "2027-12-01",
}

OPPORTUNITY_F_RESTRICTED_NATIONALITY_DICT = {
    "id": str(uuid.uuid4()),
    "title": "EU Citizens Fellowship",
    "degree_levels": ["Master's"],
    "eligible_nationalities": ["Germany", "France", "Spain", "Italy"],
    "deadline": "2027-12-15",
}


def build_normalized_profile_a() -> NormalizedAIProfile:
    """Builds a full NormalizedAIProfile model matching Scenario A."""
    uid = uuid.uuid4()
    return NormalizedAIProfile(
        user_id=uid,
        email="ahmed.cs@example.com",
        identity_context=IdentityContext(
            nationality="Pakistan",
            nationality_country_code="PK",
            country_of_residence="Pakistan",
            residence_country_code="PK",
            city="Lahore",
            is_known=True,
        ),
        education=[
            EducationRecordItem(
                institution="National University of Sciences and Technology",
                raw_degree="Bachelor of Science in Computer Science",
                normalized_degree_level="Bachelor's",
                raw_field="Computer Science",
                normalized_field="Computer Science",
                grade="3.65",
                grading_scale="4.0",
            )
        ],
        academic_performance=AcademicPerformance(
            raw_cgpa=3.65,
            normalized_gpa_4_scale=3.65,
            highest_degree_level="Bachelor's",
        ),
        tests={
            "IELTS": NormalizedTestItem(
                raw_test_name="IELTS Academic",
                canonical_test_name="IELTS",
                test_type="Language",
                score="7.5",
                test_date=date(2025, 6, 10),
            )
        },
        skills=[
            NormalizedSkillItem(
                raw_skill="Python",
                normalized_name="Python",
                category="Programming",
            )
        ],
        languages={"English": "Fluent", "Urdu": "Native/Bilingual"},
        work_experience=WorkExperienceSummary(total_years=2.5),
        research_experience=ResearchExperienceSummary(has_research_experience=True),
        publications=PublicationSummary(publication_count=1),
        projects=ProjectSummary(project_count=2),
        geographic_preferences=GeographicPreferences(),
        opportunity_preferences=OpportunityPreferences(),
        funding_preferences=FundingPreferences(),
        completeness=InformationCompleteness(is_profile_complete=True),
        matching_signals={"english_medium_education": True},
    )


def build_extracted_opportunity_a() -> ExtractedOpportunity:
    """Builds ExtractedOpportunity instance for Scenario A."""
    source_url = "https://scholarships.example.org/global-2027"
    return ExtractedOpportunity(
        canonical_key="example:global-excellence-scholarship-2027",
        title="Global Excellence Master Scholarship 2027",
        organization="Global Education Trust",
        category=OpportunityCategory.SCHOLARSHIP,
        source_type=SourceTrustType.OFFICIAL,
        source_trust_score=0.98,
        source_documents=[source_url],
        degree_levels=["Master's"],
        minimum_cgpa=ExtractedField.found(
            3.0,
            evidence=Evidence(
                source_url=source_url,
                field_name="minimum_cgpa",
                evidence_text="Applicants must have a minimum CGPA of 3.0 on a 4.0 scale.",
                confidence=0.95,
            ),
        ),
        eligible_nationalities=ExtractedField.found(
            ["Pakistan", "India", "Bangladesh"],
            evidence=Evidence(
                source_url=source_url,
                field_name="eligible_nationalities",
                evidence_text="Open to citizens of Pakistan, India, Bangladesh.",
                confidence=0.98,
            ),
        ),
        language_requirements=[
            ExtractedLanguageRequirement(
                test_name="IELTS",
                minimum_score="6.5",
                is_required=True,
                waiver_allowed=False,
                evidence=Evidence(
                    source_url=source_url,
                    field_name="language_requirements",
                    evidence_text="Minimum IELTS 6.5 band score required.",
                    confidence=0.95,
                ),
            )
        ],
        deadline=ExtractedField.found(
            "2027-08-31",
            evidence=Evidence(
                source_url=source_url,
                field_name="deadline",
                evidence_text="The application deadline is August 31, 2027.",
                confidence=0.99,
            ),
        ),
        official_source_url=source_url,
    )
