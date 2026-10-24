"""Validation and integrity guardrails for extracted opportunities.

Ensures every extracted opportunity meets strict zero-hallucination standards,
verifying that claims have valid, authentic evidence from the source document.
"""

from __future__ import annotations

from app.opportunities.extraction.evidence import EvidenceValidator
from app.opportunities.extraction.schemas import ExtractedField, ExtractedOpportunity, FieldStatus
from app.web.models.document import WebDocument


class ExtractionValidator:
    """Validates and enforces strict provenance on ExtractedOpportunity records."""

    @classmethod
    def validate_and_guard(
        cls, opp: ExtractedOpportunity, document: WebDocument
    ) -> ExtractedOpportunity:
        """Audits all extracted fields.

        Unevidenced claims or fabricated quotes are downgraded to NOT_FOUND with value None.
        """
        source_text = document.clean_text

        # Validate core scalar fields
        fields_to_check = [
            "title",
            "organization",
            "category",
            "description",
            "host_country",
            "funding_type",
            "funding_amount",
            "application_deadline",
            "opening_date",
            "application_url",
            "application_fee_amount",
        ]

        for field_name in fields_to_check:
            field = getattr(opp, field_name, None)
            if isinstance(field, ExtractedField) and field.status == FieldStatus.FOUND:
                if not field.evidence:
                    field.value = None
                    field.status = FieldStatus.NOT_FOUND
                    field.confidence = 0.0
                elif not EvidenceValidator.verify_evidence_in_text(field.evidence, source_text):
                    # Quote does not appear in source text - drop hallucinated claim
                    field.value = None
                    field.status = FieldStatus.NOT_FOUND
                    field.confidence = 0.0
                    field.evidence = None

        # Validate deadline items
        valid_deadlines = []
        for d in opp.deadlines:
            if EvidenceValidator.verify_evidence_in_text(d.evidence, source_text):
                valid_deadlines.append(d)
        opp.deadlines = valid_deadlines

        # Validate language requirement items
        valid_lang = []
        for lang_req in opp.language_requirements:
            if EvidenceValidator.verify_evidence_in_text(lang_req.evidence, source_text):
                valid_lang.append(lang_req)
        opp.language_requirements = valid_lang

        # Validate academic requirement items
        valid_acad = []
        for a in opp.academic_requirements:
            if EvidenceValidator.verify_evidence_in_text(a.evidence, source_text):
                valid_acad.append(a)
        opp.academic_requirements = valid_acad

        return opp
