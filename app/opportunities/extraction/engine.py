"""AI Opportunity Extraction Engine.

Orchestrates the conversion of clean WebDocument instances into source-grounded,
verified ExtractedOpportunity records using deterministic rules or LLMs.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Any

from app.opportunities.extraction.aggregation import OpportunityAggregator
from app.opportunities.extraction.confidence import ConfidenceCalculator
from app.opportunities.extraction.deduplication import OpportunityDeduplicator
from app.opportunities.extraction.evidence import Evidence, EvidenceType
from app.opportunities.extraction.extractors import (
    AcademicRequirementExtractor,
    ApplicationInfoExtractor,
    DeadlineExtractor,
    FundingExtractor,
    LanguageRequirementExtractor,
    SourceTrustAssessor,
)
from app.opportunities.extraction.normalization import OrganizationNormalizer
from app.opportunities.extraction.schemas import (
    ExtractedField,
    ExtractedOpportunity,
    FieldStatus,
    OpportunityCategory,
)
from app.opportunities.extraction.validators import ExtractionValidator
from app.web.models.document import WebDocument


class OpportunityExtractionModel(ABC):
    """Abstract interface for opportunity extraction models."""

    @abstractmethod
    async def extract_opportunity(self, document: WebDocument) -> ExtractedOpportunity:
        """Extracts structured opportunity facts from a single WebDocument."""
        ...


class RuleBasedOpportunityExtractor(OpportunityExtractionModel):
    """Deterministic, zero-hallucination opportunity extractor."""

    async def extract_opportunity(self, document: WebDocument) -> ExtractedOpportunity:
        """Extracts an ExtractedOpportunity using deterministic rules and verified evidence."""
        source_text = document.clean_text or ""
        doc_url = document.final_url or document.original_url
        doc_domain = document.domain

        # 1. Title Extraction
        title_val = document.title.strip() if document.title else "Untitled Opportunity"
        if document.headings:
            # First h1 if present often has better title
            h1s = [h.text for h in document.headings if h.level == 1 and h.text]
            if h1s:
                title_val = h1s[0].strip()

        # Evidence for title: verify in text or fallback to exact title
        title_evidence = None
        if title_val in source_text:
            title_evidence = Evidence(
                source_document_id=document.id,
                source_url=doc_url,
                field_name="title",
                evidence_text=title_val,
                evidence_type=EvidenceType.DIRECT_TEXT,
                confidence=1.0,
            )
        elif source_text:
            snippet = source_text[: min(100, len(source_text))]
            title_evidence = Evidence(
                source_document_id=document.id,
                source_url=doc_url,
                field_name="title",
                evidence_text=snippet,
                evidence_type=EvidenceType.METADATA,
                confidence=0.9,
            )

        # 2. Organization Extraction
        org_norm = OrganizationNormalizer.normalize(
            raw_org=document.metadata.get("organization") or "",
            source_domain=doc_domain,
        )
        # Search for institution name in headings or text if metadata missing
        raw_org_name = org_norm.display_name
        org_evidence = None
        if raw_org_name in source_text:
            org_evidence = Evidence(
                source_document_id=document.id,
                source_url=doc_url,
                field_name="organization",
                evidence_text=raw_org_name,
                evidence_type=EvidenceType.DIRECT_TEXT,
                confidence=0.95,
            )
        elif doc_domain in source_text:
            org_evidence = Evidence(
                source_document_id=document.id,
                source_url=doc_url,
                field_name="organization",
                evidence_text=doc_domain,
                evidence_type=EvidenceType.METADATA,
                confidence=0.9,
            )

        # 3. Category Detection
        category = self._detect_category(title_val, source_text)
        cat_evidence = None
        cat_match = re.search(rf"\b{re.escape(category.value)}\b", source_text, re.IGNORECASE)
        if cat_match:
            cat_evidence = Evidence(
                source_document_id=document.id,
                source_url=doc_url,
                field_name="category",
                evidence_text=cat_match.group(0),
                evidence_type=EvidenceType.DIRECT_TEXT,
                confidence=0.9,
            )

        # 4. Description Excerpt
        desc_snippet = ""
        desc_evidence = None
        if source_text:
            desc_snippet = source_text[: min(400, len(source_text))].strip()
            desc_evidence = Evidence(
                source_document_id=document.id,
                source_url=doc_url,
                field_name="description",
                evidence_text=desc_snippet,
                evidence_type=EvidenceType.DIRECT_TEXT,
                confidence=0.9,
            )

        # 5. Host Country Extraction
        host_country, country_evidence = self._detect_host_country(
            source_text, document.id, doc_url
        )
        country_field = ExtractedField[str](
            value=host_country,
            status=FieldStatus.FOUND if host_country else FieldStatus.NOT_FOUND,
            confidence=0.85 if host_country else 0.0,
            evidence=country_evidence,
        )

        # 6. Deterministic Component Extractors
        deadlines, primary_deadline, opening_date, is_rolling = DeadlineExtractor.extract_deadlines(
            document
        )
        funding_type, funding_amount, benefits = FundingExtractor.extract_funding(document)
        (
            academic_requirements,
            degree_req,
            gpa_field,
            pct_field,
            degree_levels,
            fields_of_study,
        ) = AcademicRequirementExtractor.extract_academic_requirements(document)
        (
            language_requirements,
            english_overview,
            accepted_tests,
            waiver_allowed_field,
            waiver_conditions_field,
        ) = LanguageRequirementExtractor.extract_language_requirements(document)
        app_url, app_method, is_free, fee_amount = (
            ApplicationInfoExtractor.extract_application_info(document)
        )
        source_trust_type, source_trust_score = SourceTrustAssessor.assess_trust(
            doc_url, doc_domain
        )

        # Official Source URL
        url_evidence = Evidence(
            source_document_id=document.id,
            source_url=doc_url,
            field_name="official_source_url",
            evidence_text=doc_url,
            evidence_type=EvidenceType.URL,
            confidence=1.0,
        )

        # Application fee field
        if is_free.status == FieldStatus.FOUND:
            app_fee_field = ExtractedField[bool].found(
                value=not bool(is_free.value),
                evidence=is_free.evidence,
                confidence=is_free.confidence,
            )
        else:
            app_fee_field = ExtractedField[bool].not_found()

        # Canonical key
        canonical_key = OpportunityDeduplicator.generate_canonical_key(
            title=title_val,
            organization=raw_org_name,
            category=category.value,
            official_url=doc_url,
        )

        opportunity = ExtractedOpportunity(
            canonical_key=canonical_key,
            title=title_val,
            organization=raw_org_name,
            category=category,
            description=desc_snippet,
            countries=[host_country] if host_country else [],
            host_country=country_field,
            funding_type=funding_type.value or "Unknown",
            funding_amount=funding_amount.value if funding_amount.value else None,
            funding_currency=funding_amount.value.currency if funding_amount.value else None,
            stipend=funding_amount,
            deadline=primary_deadline,
            opening_date=opening_date,
            is_rolling=is_rolling,
            deadlines=deadlines,
            academic_requirements=academic_requirements,
            minimum_cgpa=gpa_field,
            minimum_percentage=pct_field,
            degree_requirement=degree_req,
            degree_levels=degree_levels,
            fields_of_study=fields_of_study,
            language_requirements=language_requirements,
            english_requirement=english_overview,
            english_tests=accepted_tests,
            other_benefits=benefits,
            application_url=app_url.value,
            application_method=app_method,
            application_fee=app_fee_field,
            application_fee_amount=fee_amount,
            official_source_url=doc_url,
            source_type=source_trust_type,
            source_trust_score=source_trust_score,
            source_documents=[doc_url],
        )

        # Collect atomic evidences
        all_evidences = []
        if title_evidence:
            all_evidences.append(title_evidence)
        if org_evidence:
            all_evidences.append(org_evidence)
        if cat_evidence:
            all_evidences.append(cat_evidence)
        if desc_evidence:
            all_evidences.append(desc_evidence)
        if country_evidence:
            all_evidences.append(country_evidence)
        if funding_type.evidence:
            all_evidences.append(funding_type.evidence)
        if funding_amount.evidence:
            all_evidences.append(funding_amount.evidence)
        if primary_deadline.evidence:
            all_evidences.append(primary_deadline.evidence)
        if opening_date.evidence:
            all_evidences.append(opening_date.evidence)
        for d in deadlines:
            if d.evidence:
                all_evidences.append(d.evidence)
        for ar in academic_requirements:
            if ar.evidence:
                all_evidences.append(ar.evidence)
        for lr in language_requirements:
            if lr.evidence:
                all_evidences.append(lr.evidence)
        if app_url.evidence:
            all_evidences.append(app_url.evidence)
        if is_free.evidence:
            all_evidences.append(is_free.evidence)
        all_evidences.append(url_evidence)

        opportunity.all_evidence = all_evidences

        # Guard against unevidenced extractions
        opportunity = ExtractionValidator.validate_and_guard(opportunity, document)

        # Calculate extraction confidence
        opportunity.confidence = ConfidenceCalculator.calculate(opportunity)

        return opportunity

    def _detect_category(self, title: str, text: str) -> OpportunityCategory:
        combined = f"{title} {text[:1000]}".lower()
        if "fellowship" in combined:
            return OpportunityCategory.FELLOWSHIP
        if "internship" in combined:
            return OpportunityCategory.INTERNSHIP
        if "grant" in combined or "research grant" in combined:
            return OpportunityCategory.GRANT
        if "exchange" in combined:
            return OpportunityCategory.EXCHANGE_PROGRAM
        if "conference" in combined:
            return OpportunityCategory.CONFERENCE
        if "competition" in combined or "contest" in combined:
            return OpportunityCategory.COMPETITION
        if "scholarship" in combined or "scholarships" in combined:
            return OpportunityCategory.SCHOLARSHIP
        return OpportunityCategory.OTHER

    def _detect_host_country(
        self, text: str, doc_id: Any, doc_url: str
    ) -> tuple[str | None, Evidence | None]:
        country_patterns = [
            r"\b(United States|USA|Germany|United Kingdom|UK|Canada|"
            r"Australia|Switzerland|France|Japan|Sweden|Singapore|Netherlands)\b"
        ]
        for pat in country_patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                country_name = match.group(1)
                evidence = Evidence(
                    source_document_id=doc_id,
                    source_url=doc_url,
                    field_name="host_country",
                    evidence_text=match.group(0),
                    evidence_type=EvidenceType.DIRECT_TEXT,
                    confidence=0.85,
                )
                return country_name, evidence
        return None, None


class OpportunityExtractionEngine:
    """High-level orchestration engine for single and multi-page opportunity extraction."""

    def __init__(self, model: OpportunityExtractionModel | None = None):
        self.model = model or RuleBasedOpportunityExtractor()

    async def extract(self, document: WebDocument) -> ExtractedOpportunity:
        """Extracts structured opportunity facts from a single WebDocument."""
        return await self.model.extract_opportunity(document)

    async def extract_batch(self, documents: list[WebDocument]) -> ExtractedOpportunity:
        """Extracts and consolidates opportunities across multiple related web pages."""
        if not documents:
            raise ValueError("No documents provided for batch extraction")

        extracted_list: list[ExtractedOpportunity] = []
        for doc in documents:
            extracted = await self.extract(doc)
            extracted_list.append(extracted)

        return OpportunityAggregator.merge(extracted_list)
