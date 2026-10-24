"""Deterministic extractors for dates, funding, academics, tests, and application info."""

import re
from urllib.parse import urlparse

from app.opportunities.extraction.evidence import Evidence, EvidenceType
from app.opportunities.extraction.schemas import (
    ApplicationMethod,
    DeadlineType,
    ExtractedAcademicRequirement,
    ExtractedDeadline,
    ExtractedField,
    ExtractedLanguageRequirement,
    FundingPeriod,
    SourceTrustType,
    StructuredFundingAmount,
)
from app.web.models.document import ExtractedTable, LinkType, WebDocument

# Currency symbols & codes
CURRENCY_MAP = {
    "€": "EUR",
    "eur": "EUR",
    "euro": "EUR",
    "euros": "EUR",
    "$": "USD",
    "usd": "USD",
    "dollar": "USD",
    "dollars": "USD",
    "£": "GBP",
    "gbp": "GBP",
    "pound": "GBP",
    "pounds": "GBP",
    "¥": "JPY",
    "jpy": "JPY",
    "cad": "CAD",
    "aud": "AUD",
    "chf": "CHF",
    "sgd": "SGD",
}

STIPEND_RE = re.compile(
    r"(?:stipend|allowance|grant|funding)\s*(?:of|is|:)?\s*(?:exact\s+monthly\s+stipend\s+of\s+)?"
    r"(?P<curr>[€$£¥₹]|eur|usd|gbp|sgd|chf|jpy|aud|cad|[A-Za-z]{3})?\s*"
    r"(?P<amount>[\d,]+(?:\.\d+)?)\s*"
    r"(?P<curr2>[€$£¥₹]|eur|usd|gbp|sgd|chf|jpy|aud|cad|[A-Za-z]{3})?"
    r"(?:\s*(?:per|/|a)\s*(?P<period>month|year|annum|annual|term|semester|week|day))?",
    re.IGNORECASE,
)

ALT_STIPEND_RE = re.compile(
    r"(?P<curr>[€$£¥₹]|eur|usd|gbp|sgd|chf|jpy|aud|cad|[A-Za-z]{3})\s*(?P<amount>[\d,]+(?:\.\d+)?)\s*"
    r"(?:per|/|a)\s*(?P<period>month|year|annum|annual|term|semester)?",
    re.IGNORECASE,
)

IELTS_RE = re.compile(
    r"\bielts\b[^\d\n.]{0,25}(?:minimum|score|band|overall)?\s*(?:of|:)?\s*(?P<score>\d(?:\.\d)?)\b",
    re.IGNORECASE,
)

TOEFL_RE = re.compile(
    r"\btoefl\b[^\d\n.]{0,25}(?:ibt|pbt|minimum|score)?\s*(?:of|:)?\s*(?P<score>\d{2,3})\b",
    re.IGNORECASE,
)

GPA_RE = re.compile(
    r"\b(?:gpa|cgpa)\b[^\d\n]{0,25}(?:of|:|\s)?\s*(?P<gpa>\d(?:\.\d+)?)(?:\s*(?:out\s+of|/)\s*(?P<scale>\d(?:\.\d+)?))?",
    re.IGNORECASE,
)

PERCENTAGE_RE = re.compile(
    r"(?:(?:minimum|at\s+least|equivalent)\s+)?(?P<pct>\d{1,2}(?:\.\d+)?)\s*%",
    re.IGNORECASE,
)


class DeadlineExtractor:
    """Extracts explicit date milestones, distinguishing rolling from fixed deadlines."""

    @classmethod
    def extract_deadlines(
        cls, doc: WebDocument
    ) -> tuple[
        list[ExtractedDeadline],
        ExtractedField[str],
        ExtractedField[str],
        ExtractedField[bool],
    ]:
        deadlines: list[ExtractedDeadline] = []
        seen_dates: set[str] = set()

        is_rolling_field = ExtractedField[bool].found(False)
        rolling_match = re.search(
            r"\b(?:rolling\s+(?:basis|admissions|applications?)|open\s+until\s+filled)\b",
            doc.clean_text,
            re.IGNORECASE,
        )
        if rolling_match:
            snippet = doc.clean_text[
                max(0, rolling_match.start() - 30) : min(
                    len(doc.clean_text), rolling_match.end() + 30
                )
            ].strip()
            ev = Evidence(
                source_document_id=doc.id,
                source_url=doc.final_url,
                field_name="is_rolling",
                evidence_text=snippet,
                evidence_type=EvidenceType.DIRECT_TEXT,
            )
            is_rolling_field = ExtractedField[bool].found(True, evidence=ev)
            deadlines.append(
                ExtractedDeadline(
                    deadline_date=None,
                    deadline_type=DeadlineType.ROLLING,
                    is_rolling=True,
                    raw_text=rolling_match.group(0),
                    evidence=ev,
                )
            )

        # 2. Extract from structured tables (high reliability)
        for table in doc.tables:
            cls._extract_deadlines_from_table(table, doc, deadlines, seen_dates)

        # 3. Extract from text with date candidates
        opening_field = ExtractedField[str].not_found()
        primary_deadline = ExtractedField[str].not_found()

        for date_item in doc.extracted_dates:
            context_lower = date_item.context.lower()
            if any(
                term in context_lower
                for term in ("opening date", "open from", "opens on", "opening")
            ):
                if date_item.parsed_iso:
                    ev_open = Evidence(
                        source_document_id=doc.id,
                        source_url=doc.final_url,
                        field_name="opening_date",
                        evidence_text=date_item.context,
                        evidence_type=EvidenceType.DIRECT_TEXT,
                    )
                    opening_field = ExtractedField[str].found(
                        value=date_item.parsed_iso, evidence=ev_open
                    )
                    deadlines.append(
                        ExtractedDeadline(
                            deadline_date=date_item.parsed_iso,
                            deadline_type=DeadlineType.OPENING_DATE,
                            is_rolling=False,
                            raw_text=date_item.raw_text,
                            evidence=ev_open,
                        )
                    )

            if any(
                term in context_lower
                for term in ("deadline", "apply before", "closing date", "submission")
            ):
                if date_item.parsed_iso and date_item.parsed_iso not in seen_dates:
                    seen_dates.add(date_item.parsed_iso)
                    ev_dl = Evidence(
                        source_document_id=doc.id,
                        source_url=doc.final_url,
                        field_name="deadline",
                        evidence_text=date_item.context,
                        evidence_type=EvidenceType.DIRECT_TEXT,
                    )
                    deadlines.append(
                        ExtractedDeadline(
                            deadline_date=date_item.parsed_iso,
                            deadline_type=DeadlineType.APPLICATION_DEADLINE,
                            is_rolling=False,
                            raw_text=date_item.raw_text,
                            evidence=ev_dl,
                        )
                    )

        # Also search text regex directly for Application Deadline: YYYY-MM-DD
        if primary_deadline.value is None:
            dl_match = re.search(
                r"\b(?:application\s+deadline|deadline)\s*:\s*(?P<date>\d{4}-\d{2}-\d{2})\b",
                doc.clean_text,
                re.IGNORECASE,
            )
            if dl_match:
                date_str = dl_match.group("date")
                snippet = doc.clean_text[
                    max(0, dl_match.start() - 15) : min(len(doc.clean_text), dl_match.end() + 15)
                ].strip()
                ev = Evidence(
                    source_document_id=doc.id,
                    source_url=doc.final_url,
                    field_name="deadline",
                    evidence_text=snippet,
                    evidence_type=EvidenceType.DIRECT_TEXT,
                )
                primary_deadline = ExtractedField[str].found(value=date_str, evidence=ev)
                if date_str not in seen_dates:
                    seen_dates.add(date_str)
                    deadlines.append(
                        ExtractedDeadline(
                            deadline_date=date_str,
                            deadline_type=DeadlineType.APPLICATION_DEADLINE,
                            is_rolling=False,
                            raw_text=date_str,
                            evidence=ev,
                        )
                    )

        # If primary_deadline not yet resolved, pick first application deadline
        if primary_deadline.value is None:
            for d in deadlines:
                if d.deadline_type == DeadlineType.APPLICATION_DEADLINE and d.deadline_date:
                    primary_deadline = ExtractedField[str].found(
                        value=d.deadline_date, evidence=d.evidence
                    )
                    break

        # Also search text regex directly for Opening Date: YYYY-MM-DD
        if opening_field.value is None:
            open_match = re.search(
                r"\b(?:opening\s+date|opens\s+on)\s*:\s*(?P<date>\d{4}-\d{2}-\d{2})\b",
                doc.clean_text,
                re.IGNORECASE,
            )
            if open_match:
                open_str = open_match.group("date")
                start_idx = max(0, open_match.start() - 15)
                end_idx = min(len(doc.clean_text), open_match.end() + 15)
                snippet = doc.clean_text[start_idx:end_idx].strip()
                ev = Evidence(
                    source_document_id=doc.id,
                    source_url=doc.final_url,
                    field_name="opening_date",
                    evidence_text=snippet,
                    evidence_type=EvidenceType.DIRECT_TEXT,
                )
                opening_field = ExtractedField[str].found(value=open_str, evidence=ev)

        return (deadlines, primary_deadline, opening_field, is_rolling_field)

    @classmethod
    def _extract_deadlines_from_table(
        cls,
        table: ExtractedTable,
        doc: WebDocument,
        deadlines: list[ExtractedDeadline],
        seen_dates: set[str],
    ) -> None:
        # Check column headers for deadline or date indicators
        deadline_col_idx = -1
        for i, col in enumerate(table.columns):
            if any(
                term in col.lower()
                for term in ("deadline", "closing", "submission date", "target date")
            ):
                deadline_col_idx = i
                break

        if deadline_col_idx >= 0:
            for row in table.rows:
                if deadline_col_idx < len(row):
                    cell_text = row[deadline_col_idx].strip()
                    # Check if cell has a parseable date
                    for date_item in doc.extracted_dates:
                        if date_item.raw_text in cell_text and date_item.parsed_iso:
                            if date_item.parsed_iso not in seen_dates:
                                seen_dates.add(date_item.parsed_iso)
                                round_name = row[0] if len(row) > 1 else "Application Round"
                                evidence_text = (
                                    f"{table.caption or 'Table'} - {round_name}: {cell_text}"
                                )
                                deadlines.append(
                                    ExtractedDeadline(
                                        deadline_date=date_item.parsed_iso,
                                        deadline_type=DeadlineType.APPLICATION_DEADLINE,
                                        is_rolling=False,
                                        raw_text=cell_text,
                                        evidence=Evidence(
                                            source_document_id=doc.id,
                                            source_url=doc.final_url,
                                            field_name="deadline",
                                            evidence_text=evidence_text,
                                            evidence_type=EvidenceType.TABLE,
                                            location=table.caption,
                                        ),
                                    )
                                )


class FundingExtractor:
    """Extracts funding tier, tuition coverage, stipends, and allowances with source citations."""

    @classmethod
    def extract_funding(
        cls, doc: WebDocument
    ) -> tuple[
        str,
        StructuredFundingAmount | None,
        ExtractedField[str],
        ExtractedField[StructuredFundingAmount],
        ExtractedField[bool],
        ExtractedField[bool],
        ExtractedField[bool],
        list[str],
    ]:
        text = doc.clean_text
        text_lower = text.lower()
        other_benefits: list[str] = []

        # 1. Funding Type & Tuition Coverage
        funding_type = "Unknown"
        tuition_coverage = ExtractedField[str].not_found()

        if (
            "fully funded" in text_lower
            or "full scholarship" in text_lower
            or "full tuition coverage" in text_lower
        ):
            funding_type = "Fully Funded"
            match = re.search(
                r"\b(fully funded|full scholarship|full tuition coverage)\b", text, re.I
            )
            if match:
                snippet = text[
                    max(0, match.start() - 30) : min(len(text), match.end() + 30)
                ].strip()
                tuition_coverage = ExtractedField[str].found(
                    value="Full",
                    evidence=Evidence(
                        source_document_id=doc.id,
                        source_url=doc.final_url,
                        field_name="tuition_coverage",
                        evidence_text=snippet,
                        evidence_type=EvidenceType.DIRECT_TEXT,
                    ),
                    confidence=1.0,
                )
        elif (
            "partially funded" in text_lower
            or "partial scholarship" in text_lower
            or "tuition waiver" in text_lower
        ):
            funding_type = "Partially Funded"
            match = re.search(
                r"\b(partially funded|partial scholarship|tuition waiver)\b", text, re.I
            )
            if match:
                snippet = text[
                    max(0, match.start() - 30) : min(len(text), match.end() + 30)
                ].strip()
                tuition_coverage = ExtractedField[str].found(
                    value="Partial",
                    evidence=Evidence(
                        source_document_id=doc.id,
                        source_url=doc.final_url,
                        field_name="tuition_coverage",
                        evidence_text=snippet,
                        evidence_type=EvidenceType.DIRECT_TEXT,
                    ),
                    confidence=0.9,
                )

        # 2. Stipend & Amounts
        funding_amount: StructuredFundingAmount | None = None
        stipend_field = ExtractedField[StructuredFundingAmount].not_found()

        stipend_match = STIPEND_RE.search(text) or ALT_STIPEND_RE.search(text)
        if stipend_match:
            gd = stipend_match.groupdict()
            amt_str = gd.get("amount", "").replace(",", "")
            try:
                amt_val = float(amt_str)
                curr_symbol = (gd.get("curr") or gd.get("curr2") or "").lower()
                currency = CURRENCY_MAP.get(curr_symbol, curr_symbol.upper() or "USD")

                period_str = (gd.get("period") or "").lower()
                if "month" in period_str:
                    period = FundingPeriod.MONTHLY
                elif any(p in period_str for p in ("year", "annum", "annual")):
                    period = FundingPeriod.ANNUAL
                elif "term" in period_str or "semester" in period_str:
                    period = FundingPeriod.PER_TERM
                else:
                    period = FundingPeriod.MONTHLY if amt_val < 6000 else FundingPeriod.ANNUAL

                funding_amount = StructuredFundingAmount(
                    amount=amt_val,
                    currency=currency,
                    period=period,
                    amount_type="EXACT",
                )
                snippet = text[
                    max(0, stipend_match.start() - 25) : min(len(text), stipend_match.end() + 25)
                ].strip()
                stipend_field = ExtractedField[StructuredFundingAmount].found(
                    value=funding_amount,
                    evidence=Evidence(
                        source_document_id=doc.id,
                        source_url=doc.final_url,
                        field_name="stipend",
                        evidence_text=snippet,
                        evidence_type=EvidenceType.DIRECT_TEXT,
                    ),
                    confidence=0.95,
                )
            except ValueError:
                pass

        # 3. Auxiliary Allowances: Travel, Housing, Health Insurance
        travel_field = cls._extract_benefit_flag(
            doc, r"\b(?:travel\s+(?:grant|allowance|costs)|flight\s+ticket)\b", "travel_support"
        )
        accommodation_field = cls._extract_benefit_flag(
            doc,
            r"\b(?:accommodation|free\s+(?:student\s+)?housing|dormitory)\b",
            "accommodation_support",
        )
        insurance_field = cls._extract_benefit_flag(
            doc, r"\b(?:health\s+insurance|medical\s+coverage)\b", "insurance_support"
        )

        funding_type_field = ExtractedField[str].not_found()
        if funding_type != "Unknown":
            funding_type_field = ExtractedField[str].found(
                value=funding_type,
                evidence=tuition_coverage.evidence,
                confidence=tuition_coverage.confidence or 0.9,
            )

        if "tuition waiver" in text_lower:
            other_benefits.append("Tuition Waiver")
        if travel_field.value:
            other_benefits.append("Travel Allowance")
        if accommodation_field.value:
            other_benefits.append("Housing Allowance")
        if insurance_field.value:
            other_benefits.append("Health Insurance")

        return (
            funding_type_field,
            stipend_field,
            other_benefits,
        )

    @classmethod
    def _extract_benefit_flag(
        cls, doc: WebDocument, pattern_str: str, field_name: str
    ) -> ExtractedField[bool]:
        match = re.search(pattern_str, doc.clean_text, re.IGNORECASE)
        if match:
            snippet = doc.clean_text[
                max(0, match.start() - 30) : min(len(doc.clean_text), match.end() + 30)
            ].strip()
            return ExtractedField[bool].found(
                value=True,
                evidence=Evidence(
                    source_document_id=doc.id,
                    source_url=doc.final_url,
                    field_name=field_name,
                    evidence_text=snippet,
                    evidence_type=EvidenceType.DIRECT_TEXT,
                ),
                confidence=0.9,
            )
        return ExtractedField[bool].not_found()


class AcademicRequirementExtractor:
    """Extracts degree prerequisites, GPA thresholds, and field restrictions with evidence."""

    @classmethod
    def extract_academic_requirements(
        cls, doc: WebDocument
    ) -> tuple[
        list[ExtractedAcademicRequirement],
        ExtractedField[str],
        ExtractedField[float],
        ExtractedField[float],
        list[str],
        list[str],
    ]:
        text = doc.clean_text
        text_lower = text.lower()
        academics: list[ExtractedAcademicRequirement] = []
        degree_levels: list[str] = []
        fields_of_study: list[str] = []

        # 1. Degree levels
        if "bachelor" in text_lower or "undergraduate" in text_lower:
            degree_levels.append("Bachelor's")
        if "master" in text_lower or "postgraduate" in text_lower:
            degree_levels.append("Master's")
        if "phd" in text_lower or "doctoral" in text_lower or "doctorate" in text_lower:
            degree_levels.append("PhD")
        if "postdoctoral" in text_lower or "postdoc" in text_lower:
            degree_levels.append("Postdoc")

        # 2. Degree requirement string & evidence
        degree_req = ExtractedField[str].not_found()
        deg_match = re.search(
            r"\b(?:must\s+hold|completed|possess|hold\s+an?\s+accredited)\s+"
            r"(?:an?\s+)?(?P<deg>[A-Za-z' ]{3,30}(?:degree|diploma))\b",
            text,
            re.IGNORECASE,
        )
        if deg_match:
            deg_val = deg_match.group("deg").strip()
            snippet = text[
                max(0, deg_match.start() - 25) : min(len(text), deg_match.end() + 25)
            ].strip()
            degree_req = ExtractedField[str].found(
                value=deg_val,
                evidence=Evidence(
                    source_document_id=doc.id,
                    source_url=doc.final_url,
                    field_name="degree_requirement",
                    evidence_text=snippet,
                    evidence_type=EvidenceType.DIRECT_TEXT,
                ),
                confidence=0.9,
            )
            academics.append(
                ExtractedAcademicRequirement(
                    degree_level=deg_val,
                    minimum_cgpa=None,
                    minimum_percentage=None,
                    degree_subject=None,
                    raw_text=snippet,
                    evidence=degree_req.evidence,  # type: ignore
                )
            )

        # 3. Minimum GPA / CGPA
        gpa_field = ExtractedField[float].not_found()
        gpa_match = GPA_RE.search(text)
        if gpa_match:
            gpa_str = gpa_match.group("gpa")
            try:
                gpa_val = float(gpa_str)
                snippet = text[
                    max(0, gpa_match.start() - 25) : min(len(text), gpa_match.end() + 25)
                ].strip()
                gpa_field = ExtractedField[float].found(
                    value=gpa_val,
                    evidence=Evidence(
                        source_document_id=doc.id,
                        source_url=doc.final_url,
                        field_name="minimum_gpa",
                        evidence_text=snippet,
                        evidence_type=EvidenceType.DIRECT_TEXT,
                    ),
                    confidence=0.95,
                )
            except ValueError:
                pass

        # 4. Minimum Percentage
        pct_field = ExtractedField[float].not_found()
        pct_match = PERCENTAGE_RE.search(text)
        if pct_match:
            pct_str = pct_match.group("pct")
            try:
                pct_val = float(pct_str)
                snippet = text[
                    max(0, pct_match.start() - 25) : min(len(text), pct_match.end() + 25)
                ].strip()
                pct_field = ExtractedField[float].found(
                    value=pct_val,
                    evidence=Evidence(
                        source_document_id=doc.id,
                        source_url=doc.final_url,
                        field_name="minimum_percentage",
                        evidence_text=snippet,
                        evidence_type=EvidenceType.DIRECT_TEXT,
                    ),
                    confidence=0.95,
                )
            except ValueError:
                pass

        # 5. Fields of study
        field_keywords = [
            "Computer Science",
            "Artificial Intelligence",
            "Data Science",
            "Mathematics",
            "Physics",
            "Engineering",
            "Medicine",
            "Biotechnology",
            "Business",
            "Economics",
        ]
        for fk in field_keywords:
            if fk.lower() in text_lower:
                fields_of_study.append(fk)

        return (academics, degree_req, gpa_field, pct_field, degree_levels, fields_of_study)

    extract_requirements = extract_academic_requirements


class LanguageRequirementExtractor:
    """Extracts language test requirements and scores while preserving unknown status."""

    @classmethod
    def extract_language_requirements(
        cls, doc: WebDocument
    ) -> tuple[
        list[ExtractedLanguageRequirement],
        ExtractedField[str],
        list[str],
        ExtractedField[str],
        ExtractedField[str],
    ]:
        text = doc.clean_text
        text_lower = text.lower()
        reqs: list[ExtractedLanguageRequirement] = []
        accepted_tests: list[str] = []

        # 1. Explicit exemption check ("No IELTS required" / "without IELTS")
        exempt_match = re.search(
            r"\b(?:no\s+(?:ielts|toefl)\s+required|(?:ielts|toefl)\s+(?:is\s+)?not\s+required|without\s+ielts)\b",
            text,
            re.IGNORECASE,
        )
        if exempt_match:
            snippet = text[
                max(0, exempt_match.start() - 25) : min(len(text), exempt_match.end() + 25)
            ].strip()
            ev = Evidence(
                source_document_id=doc.id,
                source_url=doc.final_url,
                field_name="minimum_ielts",
                evidence_text=snippet,
                evidence_type=EvidenceType.DIRECT_TEXT,
            )
            reqs.append(
                ExtractedLanguageRequirement(
                    language="English",
                    test_name="IELTS",
                    minimum_score=None,
                    is_required=False,
                    waiver_allowed=True,
                    waiver_conditions="Explicitly not required by program.",
                    evidence=ev,
                )
            )
            return (
                reqs,
                ExtractedField[str].found("English proficiency exempt", ev),
                ["Exempt"],
                ExtractedField[bool].found(True, ev),
                ExtractedField[str].found("Explicitly not required by program.", ev),
            )

        # 2. Waiver conditions ("English medium of instruction" / "taught in English")
        waiver_allowed = False
        waiver_conditions = None
        waiver_match = re.search(
            r"\b(?:taught\s+(?:entirely\s+)?in\s+english|english\s+medium(?:\s+of\s+instruction)?|previous\s+degree\s+in\s+english)\b",
            text,
            re.IGNORECASE,
        )
        if waiver_match:
            waiver_allowed = True
            waiver_conditions = text[
                max(0, waiver_match.start() - 20) : min(len(text), waiver_match.end() + 25)
            ].strip()

        # 3. IELTS score
        ielts_match = IELTS_RE.search(text)
        if ielts_match:
            score = ielts_match.group("score")
            snippet = text[
                max(0, ielts_match.start() - 25) : min(len(text), ielts_match.end() + 25)
            ].strip()
            ev = Evidence(
                source_document_id=doc.id,
                source_url=doc.final_url,
                field_name="minimum_ielts",
                evidence_text=snippet,
                evidence_type=EvidenceType.DIRECT_TEXT,
            )
            accepted_tests.append("IELTS")
            reqs.append(
                ExtractedLanguageRequirement(
                    language="English",
                    test_name="IELTS",
                    minimum_score=score,
                    is_required=True,
                    waiver_allowed=waiver_allowed,
                    waiver_conditions=waiver_conditions,
                    evidence=ev,
                )
            )

        # 4. TOEFL score
        toefl_match = TOEFL_RE.search(text)
        if toefl_match:
            score = toefl_match.group("score")
            snippet = text[
                max(0, toefl_match.start() - 25) : min(len(text), toefl_match.end() + 25)
            ].strip()
            ev = Evidence(
                source_document_id=doc.id,
                source_url=doc.final_url,
                field_name="minimum_toefl",
                evidence_text=snippet,
                evidence_type=EvidenceType.DIRECT_TEXT,
            )
            accepted_tests.append("TOEFL")
            reqs.append(
                ExtractedLanguageRequirement(
                    language="English",
                    test_name="TOEFL",
                    minimum_score=score,
                    is_required=True,
                    waiver_allowed=waiver_allowed,
                    waiver_conditions=waiver_conditions,
                    evidence=ev,
                )
            )

        # 5. General English requirement overview
        english_overview = ExtractedField[str].not_found()
        if "english" in text_lower or accepted_tests:
            match = re.search(r"[^\n.]{0,70}(?:english|ielts|toefl)[^\n.]{0,70}", text, re.I)
            if match:
                snippet = match.group(0).strip()
                english_overview = ExtractedField[str].found(
                    value=snippet,
                    evidence=Evidence(
                        source_document_id=doc.id,
                        source_url=doc.final_url,
                        field_name="english_requirement",
                        evidence_text=snippet,
                        evidence_type=EvidenceType.DIRECT_TEXT,
                    ),
                    confidence=0.9,
                )

        waiver_allowed_field = ExtractedField[bool].not_found()
        waiver_conditions_field = ExtractedField[str].not_found()
        if waiver_allowed:
            ev_w = Evidence(
                source_document_id=doc.id,
                source_url=doc.final_url,
                field_name="waiver_allowed",
                evidence_text=waiver_conditions or "Taught in English",
                evidence_type=EvidenceType.DIRECT_TEXT,
            )
            waiver_allowed_field = ExtractedField[bool].found(True, ev_w)
            waiver_conditions_field = ExtractedField[str].found(
                waiver_conditions or "Taught in English", ev_w
            )

        return (
            reqs,
            english_overview,
            accepted_tests,
            waiver_allowed_field,
            waiver_conditions_field,
        )

    extract_requirements = extract_language_requirements


class ApplicationInfoExtractor:
    """Extracts application links, portals, fees, and contacts."""

    @classmethod
    def extract_application_info(
        cls, doc: WebDocument
    ) -> tuple[
        ExtractedField[str],
        ApplicationMethod,
        ExtractedField[bool],
        float | None,
    ]:
        application_url = None
        method = ApplicationMethod.UNKNOWN

        # 1. Application URL from classified links or anchor text
        for link in doc.links:
            if link.link_type == LinkType.APPLICATION:
                application_url = link.url
                method = ApplicationMethod.ONLINE_PORTAL
                break
            elif "apply" in link.url.lower():
                application_url = link.url
                method = ApplicationMethod.ONLINE_PORTAL
                break

        app_url_field = ExtractedField[str].not_found()
        if application_url:
            ev_url = Evidence(
                source_document_id=doc.id,
                source_url=doc.final_url,
                field_name="application_url",
                evidence_text=application_url,
                evidence_type=EvidenceType.URL,
            )
            app_url_field = ExtractedField[str].found(application_url, ev_url)

        # 2. Application Free / Fee
        is_free_field = ExtractedField[bool].not_found()
        fee_amount = None

        text = doc.clean_text
        if (
            "no application fee" in text.lower()
            or "application is free" in text.lower()
            or "$0" in text
            or "free application" in text.lower()
        ):
            match = re.search(
                r"\b(no\s+application\s+fee|application\s+is\s+free|free\s+application|\$0)\b",
                text,
                re.I,
            )
            snippet = (
                text[max(0, match.start() - 25) : min(len(text), match.end() + 25)].strip()
                if match
                else "No fee"
            )
            is_free_field = ExtractedField[bool].found(
                value=True,
                evidence=Evidence(
                    source_document_id=doc.id,
                    source_url=doc.final_url,
                    field_name="is_application_free",
                    evidence_text=snippet,
                    evidence_type=EvidenceType.DIRECT_TEXT,
                ),
                confidence=1.0,
            )
            fee_amount = 0.0
        else:
            fee_match = re.search(
                r"\bapplication\s+fee\s*(?:of|:)?\s*(?P<curr>[€$£]|eur|usd)?\s*(?P<amt>\d+)\b",
                text,
                re.IGNORECASE,
            )
            if fee_match:
                amt = float(fee_match.group("amt"))
                snippet = text[
                    max(0, fee_match.start() - 25) : min(len(text), fee_match.end() + 25)
                ].strip()
                is_free_field = ExtractedField[bool].found(
                    value=False,
                    evidence=Evidence(
                        source_document_id=doc.id,
                        source_url=doc.final_url,
                        field_name="is_application_free",
                        evidence_text=snippet,
                        evidence_type=EvidenceType.DIRECT_TEXT,
                    ),
                    confidence=0.95,
                )
                fee_amount = amt

        return (app_url_field, method, is_free_field, fee_amount)


class SourceTrustAssessor:
    """Assesses host domain credibility independently from extraction confidence."""

    @classmethod
    def assess_trust(cls, url: str, domain: str | None = None) -> tuple[SourceTrustType, float]:
        """Alias for assess_source with domain parameter."""
        return cls.assess_source(url)

    @classmethod
    def assess_source(cls, url: str) -> tuple[SourceTrustType, float]:
        parsed = urlparse(url)
        domain = (parsed.hostname or "").lower()

        # Official Government
        gov_domains = (
            ".gov",
            ".gov.uk",
            ".europa.eu",
            ".gov.au",
            ".gouv.fr",
            ".bund.de",
            ".go.jp",
        )
        if domain.endswith(gov_domains):
            return (SourceTrustType.OFFICIAL, 0.98)

        # Official Educational Institutions
        edu_domains = (
            ".edu",
            ".ac.uk",
            ".edu.au",
            ".ac.jp",
            ".uni-muenchen.de",
            ".tum.de",
        )
        if domain.endswith(edu_domains):
            return (SourceTrustType.OFFICIAL, 0.95)

        # Recognized major international scholarship foundations
        known_orgs = (
            "daad.de",
            "fulbright",
            "chevening",
            "campusfrance",
            "erc.europa",
            "cern.ch",
            "rotary.org",
        )
        if any(d in domain for d in known_orgs):
            return (SourceTrustType.OFFICIAL, 0.92)

        # Aggregators / Directories
        agg_domains = (
            "scholarshipsads",
            "scholarships.com",
            "findamasters",
            "mastersportal",
            "fastweb",
            "scholarshipsportal",
        )
        if any(d in domain for d in agg_domains):
            return (SourceTrustType.DIRECTORY, 0.50)

        # News & Blogs
        if any(d in domain for d in ("news", "medium.com", "wordpress", "blogspot")):
            return (SourceTrustType.BLOG, 0.40)

        return (SourceTrustType.SECONDARY, 0.65)
