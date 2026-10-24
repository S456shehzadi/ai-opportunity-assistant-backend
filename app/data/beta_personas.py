"""Realistic synthetic beta personas representing diverse user types and testing journeys."""

from __future__ import annotations

from pydantic import BaseModel


class BetaPersona(BaseModel):
    """Synthetic persona used for automated test scenarios and quality benchmarks."""

    id: str
    name: str
    persona_type: str
    education_level: str
    nationality: str
    residence_country: str
    cgpa: float | None = None
    disciplines: list[str]
    has_english_test: bool
    funding_preference: str  # FULLY_FUNDED, PARTIALLY_FUNDED, ANY
    requires_no_ielts: bool
    requires_no_fee: bool
    target_countries: list[str]
    sample_query: str
    expected_opportunity_types: list[str]
    notes: str


BETA_PERSONAS: list[BetaPersona] = [
    BetaPersona(
        id="persona-undergrad-intern",
        name="Amina Khan",
        persona_type="Undergraduate Internship Seeker",
        education_level="Undergraduate",
        nationality="Pakistan",
        residence_country="Pakistan",
        cgpa=3.85,
        disciplines=["Computer Science", "Software Engineering"],
        has_english_test=False,
        funding_preference="FULLY_FUNDED",
        requires_no_ielts=True,
        requires_no_fee=True,
        target_countries=["Germany", "Switzerland", "United States"],
        sample_query="Fully funded summer research internships in computer science without IELTS",
        expected_opportunity_types=["Internship", "Research Fellowship"],
        notes="Undergraduate seeking paid summer laboratory positions with travel grants.",
    ),
    BetaPersona(
        id="persona-masters-scholar",
        name="Tariq Mansoor",
        persona_type="Master's Applicant (Strict Funding)",
        education_level="Bachelor's",
        nationality="Egypt",
        residence_country="Egypt",
        cgpa=3.65,
        disciplines=["Renewable Energy", "Mechanical Engineering"],
        has_english_test=False,
        funding_preference="FULLY_FUNDED",
        requires_no_ielts=True,
        requires_no_fee=True,
        target_countries=["Germany", "Sweden", "Netherlands"],
        sample_query=(
            "Tuition-free master's scholarships in renewable energy accepting "
            "English medium of instruction"
        ),
        expected_opportunity_types=["Scholarship", "Master's Degree"],
        notes=(
            "Graduate applicant unable to pay tuition or IELTS test fee, requires living stipend."
        ),
    ),
    BetaPersona(
        id="persona-phd-researcher",
        name="Dr. Elena Rostova",
        persona_type="Doctoral / Postdoctoral Researcher",
        education_level="Master's",
        nationality="Kazakhstan",
        residence_country="Kazakhstan",
        cgpa=3.92,
        disciplines=["Machine Learning", "Computational Biology"],
        has_english_test=True,
        funding_preference="FULLY_FUNDED",
        requires_no_ielts=False,
        requires_no_fee=False,
        target_countries=["United Kingdom", "Canada", "Singapore"],
        sample_query="Funded PhD positions in machine learning for genomics with salary stipend",
        expected_opportunity_types=["PhD Fellowship", "Research Grant"],
        notes="Advanced researcher focusing on published laboratory tracks and supervisor match.",
    ),
    BetaPersona(
        id="persona-startup-founder",
        name="Mateo Silva",
        persona_type="Startup Founder / Entrepreneur",
        education_level="Bachelor's",
        nationality="Brazil",
        residence_country="Brazil",
        cgpa=None,
        disciplines=["Fintech", "Artificial Intelligence", "Business"],
        has_english_test=True,
        funding_preference="ANY",
        requires_no_ielts=False,
        requires_no_fee=False,
        target_countries=["United States", "Estonia", "United Kingdom"],
        sample_query="Non-dilutive seed grants and global accelerator programs for AI climate tech",
        expected_opportunity_types=["Grant", "Incubator", "Competition"],
        notes="Non-student entrepreneur looking for equity-free grants and global accelerators.",
    ),
    BetaPersona(
        id="persona-incomplete-profile",
        name="Zainab Al-Husseini",
        persona_type="Exploring Seeker (Incomplete Profile)",
        education_level="High School / Early College",
        nationality="Jordan",
        residence_country="Jordan",
        cgpa=None,
        disciplines=[],
        has_english_test=False,
        funding_preference="ANY",
        requires_no_ielts=False,
        requires_no_fee=False,
        target_countries=[],
        sample_query="Global youth exchange programs and leadership summits",
        expected_opportunity_types=["Exchange Program", "Fellowship"],
        notes="New user with minimal profile data exploring opportunities without clear major.",
    ),
]


def get_beta_personas() -> list[BetaPersona]:
    return list(BETA_PERSONAS)
