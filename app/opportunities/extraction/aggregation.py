"""Multi-page opportunity aggregation engine.

Combines partial extractions across multiple web pages (overview, eligibility,
funding, application details) for a single opportunity into a complete, unified
ExtractedOpportunity record.
"""

from __future__ import annotations

from app.opportunities.extraction.confidence import ConfidenceCalculator
from app.opportunities.extraction.conflicts import ConflictDetector
from app.opportunities.extraction.schemas import (
    ExtractedField,
    ExtractedOpportunity,
    FieldStatus,
    SourceTrustType,
)


class OpportunityAggregator:
    """Merges multiple extracted records representing different pages of the same opportunity."""

    @classmethod
    def merge(cls, opportunities: list[ExtractedOpportunity]) -> ExtractedOpportunity:
        """Merges a list of ExtractedOpportunity records into a single consolidated record."""
        if not opportunities:
            raise ValueError("Cannot merge empty list of opportunities")

        if len(opportunities) == 1:
            return opportunities[0]

        # Sort opportunities by source trust score descending
        sorted_opps = sorted(opportunities, key=lambda o: o.source_trust_score, reverse=True)
        primary = sorted_opps[0]

        merged = primary.model_copy(deep=True)

        for secondary in sorted_opps[1:]:
            # Track conflicts between primary and secondary
            conflicts = ConflictDetector.detect_and_resolve_conflicts(merged, secondary)
            for c in conflicts:
                merged.notes.append(f"[Conflict] {c.reasoning}")
                merged.conflicts_detected.append(f"{c.field_name}: {c.reasoning}")

            # Merge primitive strings/scalars if primary is empty or secondary provides better value
            if not merged.title and secondary.title:
                merged.title = secondary.title
            if not merged.organization and secondary.organization:
                merged.organization = secondary.organization
            if not merged.description and secondary.description:
                merged.description = secondary.description
            if (
                not merged.funding_type or merged.funding_type == "Unknown"
            ) and secondary.funding_type != "Unknown":
                merged.funding_type = secondary.funding_type
            if merged.funding_amount is None and secondary.funding_amount is not None:
                merged.funding_amount = secondary.funding_amount
            if not merged.funding_currency and secondary.funding_currency:
                merged.funding_currency = secondary.funding_currency
            if not merged.application_url and secondary.application_url:
                merged.application_url = secondary.application_url
            if (
                merged.application_fee_amount is None
                and secondary.application_fee_amount is not None
            ):
                merged.application_fee_amount = secondary.application_fee_amount

            # Merge ExtractedField objects
            cls._merge_extracted_field(merged.deadline, secondary.deadline)
            cls._merge_extracted_field(merged.opening_date, secondary.opening_date)
            cls._merge_extracted_field(merged.is_rolling, secondary.is_rolling)
            cls._merge_extracted_field(merged.host_country, secondary.host_country)
            cls._merge_extracted_field(merged.stipend, secondary.stipend)
            cls._merge_extracted_field(merged.tuition_coverage, secondary.tuition_coverage)
            cls._merge_extracted_field(merged.minimum_cgpa, secondary.minimum_cgpa)
            cls._merge_extracted_field(merged.minimum_percentage, secondary.minimum_percentage)
            cls._merge_extracted_field(merged.degree_requirement, secondary.degree_requirement)
            cls._merge_extracted_field(merged.english_requirement, secondary.english_requirement)
            cls._merge_extracted_field(merged.application_fee, secondary.application_fee)

            # Merge lists
            cls._merge_deadlines(merged, secondary)
            cls._merge_language_requirements(merged, secondary)
            cls._merge_academic_requirements(merged, secondary)

            merged.locations = cls._merge_lists(merged.locations, secondary.locations)
            merged.countries = cls._merge_lists(merged.countries, secondary.countries)
            merged.eligible_countries = cls._merge_lists(
                merged.eligible_countries, secondary.eligible_countries
            )
            merged.degree_levels = cls._merge_lists(merged.degree_levels, secondary.degree_levels)
            merged.fields_of_study = cls._merge_lists(
                merged.fields_of_study, secondary.fields_of_study
            )
            merged.other_benefits = cls._merge_lists(
                merged.other_benefits, secondary.other_benefits
            )
            merged.required_documents = cls._merge_lists(
                merged.required_documents, secondary.required_documents
            )
            merged.english_tests = cls._merge_lists(merged.english_tests, secondary.english_tests)

            # Aggregate source documents
            for doc in secondary.source_documents:
                if doc not in merged.source_documents:
                    merged.source_documents.append(doc)

            # Aggregate all evidence
            existing_ev_texts = {e.evidence_text for e in merged.all_evidence}
            for ev in secondary.all_evidence:
                if ev.evidence_text not in existing_ev_texts:
                    merged.all_evidence.append(ev)
                    existing_ev_texts.add(ev.evidence_text)

            # Re-evaluate trust type (keep OFFICIAL if any source is official)
            if secondary.source_type == SourceTrustType.OFFICIAL:
                merged.source_type = SourceTrustType.OFFICIAL
                merged.source_trust_score = max(
                    merged.source_trust_score, secondary.source_trust_score
                )

        # Recalculate confidence for merged record
        merged.confidence = ConfidenceCalculator.calculate(merged)

        return merged

    @staticmethod
    def _merge_extracted_field(target: ExtractedField, source: ExtractedField) -> None:
        """Copies value and evidence from source if target is missing/not found."""
        if target.status in (FieldStatus.NOT_FOUND, FieldStatus.UNCLEAR) and source.status in (
            FieldStatus.FOUND,
            FieldStatus.INFERRED,
        ):
            target.value = source.value
            target.status = source.status
            target.confidence = source.confidence
            target.evidence = source.evidence
            target.normalized_value = source.normalized_value

    _merge_scalar_field = _merge_extracted_field

    @staticmethod
    def _merge_lists(list_a: list[str], list_b: list[str]) -> list[str]:
        """Merges two string lists maintaining order and uniqueness."""
        seen = set(list_a)
        res = list(list_a)
        for item in list_b:
            if item not in seen:
                seen.add(item)
                res.append(item)
        return res

    @staticmethod
    def _merge_deadlines(target: ExtractedOpportunity, source: ExtractedOpportunity) -> None:
        existing_dates = {d.deadline_date for d in target.deadlines if d.deadline_date}
        for d in source.deadlines:
            if d.deadline_date and d.deadline_date not in existing_dates:
                existing_dates.add(d.deadline_date)
                target.deadlines.append(d)

    @staticmethod
    def _merge_language_requirements(
        target: ExtractedOpportunity, source: ExtractedOpportunity
    ) -> None:
        existing_tests = {
            req.test_name.lower() for req in target.language_requirements if req.test_name
        }
        for req in source.language_requirements:
            if req.test_name and req.test_name.lower() not in existing_tests:
                existing_tests.add(req.test_name.lower())
                target.language_requirements.append(req)

    @staticmethod
    def _merge_academic_requirements(
        target: ExtractedOpportunity, source: ExtractedOpportunity
    ) -> None:
        existing_reqs = {
            (req.degree_level, req.minimum_cgpa) for req in target.academic_requirements
        }
        for req in source.academic_requirements:
            key = (req.degree_level, req.minimum_cgpa)
            if key not in existing_reqs:
                existing_reqs.add(key)
                target.academic_requirements.append(req)
