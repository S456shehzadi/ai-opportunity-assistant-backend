"""Confidence calculation and profile completeness analysis for eligibility."""

from __future__ import annotations

from typing import Any

from app.opportunities.eligibility.schemas import (
    EligibilityConfidence,
    RequirementEvaluation,
    RequirementPriority,
    RequirementStatus,
)


class EligibilityConfidenceCalculator:
    """Calculates objective confidence for requirements and overall evaluation."""

    @classmethod
    def calculate_requirement_confidence(
        cls,
        status: RequirementStatus,
        has_user_evidence: bool,
        has_opportunity_evidence: bool,
        is_deterministic: bool = True,
        is_conflicting: bool = False,
    ) -> EligibilityConfidence:
        """Determines confidence based on evidence grounding and evaluation determinism."""
        if is_conflicting or status == RequirementStatus.CONFLICTING:
            return EligibilityConfidence.LOW

        if status == RequirementStatus.UNKNOWN:
            # High confidence that the fact is indeed unknown, but decision confidence is low/medium
            return (
                EligibilityConfidence.MEDIUM
                if has_opportunity_evidence
                else EligibilityConfidence.LOW
            )

        if is_deterministic and has_user_evidence and has_opportunity_evidence:
            return EligibilityConfidence.HIGH

        if is_deterministic and (has_user_evidence or has_opportunity_evidence):
            return EligibilityConfidence.MEDIUM

        return EligibilityConfidence.LOW


class ProfileCompletenessAnalyzer:
    """Identifies and prioritizes missing profile information relative to target opportunities."""

    REQUIREMENT_FIELD_MAP = {
        "cgpa": "academic_performance.cgpa",
        "minimum_cgpa": "academic_performance.cgpa",
        "percentage": "academic_performance.percentage",
        "minimum_percentage": "academic_performance.percentage",
        "degree_level": "education.degree_level",
        "field_of_study": "education.field_of_study",
        "nationality": "identity_context.nationality",
        "country_of_residence": "identity_context.country_of_residence",
        "age": "identity_context.date_of_birth",
        "date_of_birth": "identity_context.date_of_birth",
        "ielts": "tests.ielts",
        "toefl": "tests.toefl",
        "pte": "tests.pte",
        "english_requirement": "tests.english_proficiency",
        "work_experience": "work_experience.total_years",
        "research_experience": "research_experience.has_research_experience",
        "publication": "publications.publication_count",
    }

    HUMAN_READABLE_NAMES = {
        "academic_performance.cgpa": "CGPA / GPA",
        "academic_performance.percentage": "Grade Percentage",
        "education.degree_level": "Degree Level / Qualification",
        "education.field_of_study": "Field of Study / Major",
        "identity_context.nationality": "Nationality / Citizenship",
        "identity_context.country_of_residence": "Country of Residence",
        "identity_context.date_of_birth": "Date of Birth",
        "tests.ielts": "IELTS Test Score",
        "tests.toefl": "TOEFL Test Score",
        "tests.pte": "PTE Test Score",
        "tests.english_proficiency": "English Proficiency Details",
        "work_experience.total_years": "Work Experience",
        "research_experience.has_research_experience": "Research Experience",
        "publications.publication_count": "Publications Record",
    }

    @classmethod
    def analyze_missing_information(
        cls,
        evaluations: list[RequirementEvaluation],
        user_facts: dict[str, Any],
    ) -> tuple[list[str], list[str]]:
        """Identifies all missing fields and prioritizes those blocking UNKNOWN requirements.

        Returns:
            tuple[missing_fields, prioritized_missing_information]
        """
        all_missing: set[str] = set()
        prioritized: list[str] = []

        # Find requirements that evaluated to UNKNOWN or CONDITIONAL
        for eval_item in evaluations:
            if eval_item.status in (RequirementStatus.UNKNOWN, RequirementStatus.CONDITIONAL):
                req_type = eval_item.requirement_type.lower()
                profile_field = cls.REQUIREMENT_FIELD_MAP.get(req_type)
                if profile_field:
                    human_name = cls.HUMAN_READABLE_NAMES.get(profile_field, profile_field)
                    all_missing.add(human_name)
                    # Mandatory UNKNOWNs have highest priority
                    if eval_item.priority == RequirementPriority.MANDATORY:
                        if human_name not in prioritized:
                            prioritized.append(human_name)

        # Append important UNKNOWNs
        for eval_item in evaluations:
            if (
                eval_item.status in (RequirementStatus.UNKNOWN, RequirementStatus.CONDITIONAL)
                and eval_item.priority == RequirementPriority.IMPORTANT
            ):
                req_type = eval_item.requirement_type.lower()
                profile_field = cls.REQUIREMENT_FIELD_MAP.get(req_type)
                if profile_field:
                    human_name = cls.HUMAN_READABLE_NAMES.get(profile_field, profile_field)
                    all_missing.add(human_name)
                    if human_name not in prioritized:
                        prioritized.append(human_name)

        return sorted(all_missing), prioritized
