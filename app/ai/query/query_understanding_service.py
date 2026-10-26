import calendar
import re
from datetime import UTC, date, datetime, timedelta
from typing import Any

from app.ai.interfaces.specialized import QueryUnderstandingModel as IQueryUnderstandingModel
from app.ai.query.intent_schemas import (
    FundingConstraint,
    FundingConstraintType,
    LanguageTestConstraint,
    SearchIntent,
    TemporalConstraint,
    TemporalConstraintType,
    TestRequirementType,
    UserIntentType,
)
from app.services.normalization.education_normalizer import EducationNormalizer
from app.services.normalization.geo_normalizer import GeoNormalizer


class QueryUnderstandingService(IQueryUnderstandingModel):
    """Deterministic, rule-based NLP query understanding service.

    Extracts user intent, opportunity categories, constraints, geography, funding,
    tests, and deadlines without requiring external AI APIs or hallucinating facts.
    """

    EXPLAIN_PATTERNS = [
        r"^what\s+(is|are|does|means)\b",
        r"\b(meaning\s+of|explain|tell\s+me\s+about|what\s+does\s+.+\s+mean)\b",
        r"\b(how\s+does\s+.+\s+work)\b",
    ]

    COMPARE_PATTERNS = [
        r"\b(compare|difference\s+between|vs\.?|versus)\b",
    ]

    ELIGIBILITY_PATTERNS = [
        r"\b(can\s+i\s+apply|am\s+i\s+eligible|eligibility\s+for|do\s+i\s+qualify)\b",
    ]

    DEADLINE_PATTERNS = [
        r"\b(deadline|closing\s+date|last\s+date|when\s+is\s+the\s+deadline|due\s+date)\b",
    ]

    CATEGORY_PATTERNS = [
        (r"\b(scholarships?|scholar)\b", "Scholarship"),
        (r"\b(fellowships?|fellow)\b", "Fellowship"),
        (r"\b(grants?|grant\s+funding)\b", "Grant"),
        (r"\b(internships?|interns?)\b", "Internship"),
        (r"\b(exchange\s+programs?|student\s+exchange)\b", "Exchange Program"),
        (
            r"\b(research\s+(positions?|fellowships?|opportunities|grants?)|lab\s+positions?)\b",
            "Research",
        ),
        (r"\b(competitions?|hackathons?|contests?)\b", "Competition"),
        (r"\b(conferences?|symposiums?)\b", "Conference"),
        (
            r"\b(startup\s+funding|venture\s+capital|angel\s+funding|seed\s+fund)\b",
            "Startup Funding",
        ),
        (r"\b(government\s+programs?|gov\s+scholarships?)\b", "Government Program"),
    ]

    FUNDING_PATTERNS = [
        (
            r"\b(fully[- ]funded|full\s+funding|100%\s+funded)\b",
            FundingConstraintType.FULLY_FUNDED,
            True,
        ),
        (r"\b(partial\s+funding|partially[- ]funded)\b", FundingConstraintType.PARTIAL, False),
        (
            r"\b(tuition\s+waiver|tuition\s+free|free\s+tuition|tuition\s+covered)\b",
            FundingConstraintType.TUITION_WAIVER,
            False,
        ),
        (
            r"\b(monthly\s+stipend|stipend|living\s+allowance)\b",
            FundingConstraintType.STIPEND,
            False,
        ),
        (
            r"\b(travel\s+grant|travel\s+allowance|flight\s+covered)\b",
            FundingConstraintType.TRAVEL_ALLOWANCE,
            False,
        ),
        (
            r"\b(no\s+application\s+fee|fee\s+waiver)\b",
            FundingConstraintType.NO_APPLICATION_FEE,
            False,
        ),
        (r"\b(funded|financial\s+aid|funding)\b", FundingConstraintType.ANY_FUNDED, False),
    ]

    TEST_PATTERNS = [
        # IELTS
        (
            r"\b(without\s+ielts|no\s+ielts|ielts\s+(not\s+required|waived|exempt))\b",
            "IELTS",
            TestRequirementType.NOT_REQUIRED,
        ),
        (r"\b(ielts\s+(required|mandatory|needed))\b", "IELTS", TestRequirementType.REQUIRED),
        (r"\b(ielts\s+accepted)\b", "IELTS", TestRequirementType.ACCEPTED),
        # TOEFL
        (
            r"\b(without\s+toefl|no\s+toefl|toefl\s+(not\s+required|waived|exempt))\b",
            "TOEFL",
            TestRequirementType.NOT_REQUIRED,
        ),
        (r"\b(toefl\s+(required|mandatory|needed))\b", "TOEFL", TestRequirementType.REQUIRED),
        (r"\b(toefl\s+accepted)\b", "TOEFL", TestRequirementType.ACCEPTED),
        # GRE
        (
            r"\b(without\s+gre|no\s+gre|gre\s+(not\s+required|waived|exempt))\b",
            "GRE",
            TestRequirementType.NOT_REQUIRED,
        ),
        (r"\b(gre\s+(required|mandatory|needed))\b", "GRE", TestRequirementType.REQUIRED),
        (r"\b(gre\s+accepted)\b", "GRE", TestRequirementType.ACCEPTED),
        # Generic English test
        (
            r"\b(without\s+english\s+test|no\s+english\s+test|english\s+test\s+not\s+required)\b",
            "English Proficiency",
            TestRequirementType.NOT_REQUIRED,
        ),
    ]

    DEGREE_PATTERNS = [
        (r"\b(postdoc|postdoctoral(\s+research)?)\b", "Postdoctoral Research"),
        (r"\b(ph\.?d|doctorate|doctoral|dphil)\b", "PhD / Doctorate"),
        (r"\b(master'?s?|m\.?sc?|postgraduate|graduate|mba|m\.?eng|m\.?phil)\b", "Master's / Postgraduate"),
        (r"\b(bachelor'?s?|b\.?sc?|undergraduate|b\.?eng|bba)\b", "Bachelor's / Undergraduate"),
        (r"\b(associate'?s?(\s+degree)?|dae|diploma)\b", "Diploma / Associate Degree"),
        (r"\b(vocational|trade\s+school|apprenticeship|technical\s+training|certificate)\b", "Certificate / Vocational Training"),
        (r"\b(intermediate|hssc|f\.?sc|f\.?a|ics|i\.?com|higher\s+secondary)\b", "Intermediate / Higher Secondary"),
        (r"\b(a-?levels?|ib\s+diploma|ibdp|international\s+baccalaureate)\b", "A-Levels / IB Diploma / Equivalent"),
        (r"\b(matric(ulation)?|ssc|gcse|o-?levels?|secondary\s+school)\b", "Matriculation / Secondary School"),
        (r"\b(high\s*school)\b", "High School"),
        (r"\b(middle\s+school|junior\s+high|lower\s+secondary)\b", "Middle School / Lower Secondary"),
        (r"\b(primary\s+school|elementary\s+school)\b", "Primary / Elementary School"),
        (r"\b(professional\s+qualification|acca|cpa|cfa|chartered)\b", "Professional Qualification"),
        (r"\b(no\s+degree|without\s+degree|no\s+formal\s+qualification|any\s+education)\b", "No Formal Qualification / Other"),
    ]

    AUDIENCE_PATTERNS = [
        (r"\b(international\s+students?)\b", "international students"),
        (r"\b(women\s+founders?|female\s+founders?)\b", "women founders"),
        (r"\b(women|female\s+students?)\b", "women"),
        (r"\b(underrepresented\s+minorities?)\b", "underrepresented minorities"),
        (r"\b(developing\s+countries?)\b", "developing country nationals"),
    ]

    async def analyze_intent(self, query: str, **kwargs: Any) -> Any:
        """Implements abstract QueryUnderstandingModel.analyze_intent."""
        as_of_date = kwargs.get("as_of_date")
        return self.understand_query(query, as_of_date=as_of_date)

    def understand_query(self, query: str, as_of_date: date | None = None) -> SearchIntent:
        """Parses natural language query into a structured SearchIntent."""
        cleaned_query = query.strip()
        lowered = cleaned_query.lower()
        now_date = as_of_date or datetime.now(UTC).date()

        # 1. Intent Classification
        is_search = True
        intent_type = UserIntentType.DISCOVER_OPPORTUNITIES

        for p in self.EXPLAIN_PATTERNS:
            if re.search(p, lowered):
                intent_type = UserIntentType.EXPLAIN_OPPORTUNITY
                is_search = False
                break

        if is_search:
            for p in self.COMPARE_PATTERNS:
                if re.search(p, lowered):
                    intent_type = UserIntentType.COMPARE_OPPORTUNITIES
                    break

        is_discovery_question = bool(
            re.search(
                r"\bwhich\s+(scholarships?|opportunities|programs?|internships?|fellowships?|grants?)\b",
                lowered,
            )
        )

        if (
            is_search
            and not is_discovery_question
            and intent_type == UserIntentType.DISCOVER_OPPORTUNITIES
        ):
            for p in self.ELIGIBILITY_PATTERNS:
                if re.search(p, lowered):
                    intent_type = UserIntentType.CHECK_ELIGIBILITY
                    break

        if is_search and intent_type == UserIntentType.DISCOVER_OPPORTUNITIES:
            for p in self.DEADLINE_PATTERNS:
                if re.search(p, lowered):
                    intent_type = UserIntentType.FIND_DEADLINES
                    break

        # 2. Category Extraction
        categories: list[str] = []
        for pat, cat_name in self.CATEGORY_PATTERNS:
            if re.search(pat, lowered):
                if cat_name not in categories:
                    categories.append(cat_name)

        # Refine specific search intent based on primary category
        if is_search and intent_type == UserIntentType.DISCOVER_OPPORTUNITIES:
            if "Scholarship" in categories:
                intent_type = UserIntentType.FIND_SCHOLARSHIPS
            elif "Internship" in categories:
                intent_type = UserIntentType.FIND_INTERNSHIPS
            elif "Research" in categories or "Fellowship" in categories:
                intent_type = UserIntentType.FIND_RESEARCH_OPPORTUNITIES
            elif "Startup Funding" in categories or "Grant" in categories:
                intent_type = UserIntentType.FIND_FUNDING

        # 3. Geographic Extraction
        countries: list[str] = []
        regions: list[str] = []
        remote: bool | None = None

        if re.search(r"\b(remote|work\s+from\s+home|online)\b", lowered):
            remote = True

        # Check for regions
        for reg in (
            "europe",
            "european",
            "north america",
            "asia",
            "middle east",
            "scandinavia",
            "latin america",
            "global",
        ):
            if re.search(rf"\b(in|across|around|anywhere\s+in)?\s*{reg}\b", lowered):
                norm_reg = GeoNormalizer.normalize_region(reg)
                if norm_reg and norm_reg not in regions:
                    regions.append(norm_reg)

        # Check for countries
        for c_info in GeoNormalizer.COUNTRIES.values():
            for alias in (c_info.name.lower(), c_info.code.lower(), *c_info.aliases):
                # Ensure word boundary
                if len(alias) <= 2:
                    pattern = rf"\bin\s+{re.escape(alias)}\b"
                else:
                    pattern = rf"\b{re.escape(alias)}\b"

                if re.search(pattern, lowered):
                    if c_info.name not in countries:
                        countries.append(c_info.name)
                    break

        # 4. Degree Level Extraction
        degree_levels: list[str] = []
        for pat, deg_name in self.DEGREE_PATTERNS:
            if re.search(pat, lowered):
                if deg_name not in degree_levels:
                    degree_levels.append(deg_name)

        # 5. Field of Study Extraction
        fields: list[str] = []
        for f_key in sorted(EducationNormalizer.FIELD_TAXONOMY.keys(), key=len, reverse=True):
            if len(f_key) >= 2 and re.search(rf"\b{re.escape(f_key)}\b", lowered):
                norm_f, _ = EducationNormalizer.normalize_field_of_study(f_key)
                if norm_f and norm_f not in fields:
                    fields.append(norm_f)

        # 6. Funding Constraints Extraction
        funding_constraints: list[FundingConstraint] = []
        seen_funding_types: set[FundingConstraintType] = set()

        for pat, f_type, is_full in self.FUNDING_PATTERNS:
            match = re.search(pat, lowered)
            if match:
                # If fully funded is matched, skip generic 'any_funded'
                if f_type == FundingConstraintType.ANY_FUNDED and (
                    FundingConstraintType.FULLY_FUNDED in seen_funding_types
                ):
                    continue
                if f_type not in seen_funding_types:
                    seen_funding_types.add(f_type)
                    funding_constraints.append(
                        FundingConstraint(
                            constraint_type=f_type,
                            raw_mention=match.group(0),
                            is_fully_funded=is_full,
                        )
                    )

        # 7. Language / Test Constraints
        test_constraints: list[LanguageTestConstraint] = []
        for pat, t_name, r_type in self.TEST_PATTERNS:
            match = re.search(pat, lowered)
            if match:
                test_constraints.append(
                    LanguageTestConstraint(
                        test_name=t_name,
                        requirement_type=r_type,
                        raw_mention=match.group(0),
                    )
                )

        # 8. Audience / Target Demographics
        audience_constraints: list[str] = []
        for pat, aud_name in self.AUDIENCE_PATTERNS:
            if re.search(pat, lowered):
                if aud_name not in audience_constraints:
                    audience_constraints.append(aud_name)

        # 9. Temporal / Deadline Understanding (Dynamic)
        temporal_constraints: list[TemporalConstraint] = []

        if re.search(r"\bthis\s+month\b", lowered):
            _, last_day = calendar.monthrange(now_date.year, now_date.month)
            temporal_constraints.append(
                TemporalConstraint(
                    constraint_type=TemporalConstraintType.THIS_MONTH,
                    raw_mention="this month",
                    window_start=now_date,
                    window_end=date(now_date.year, now_date.month, last_day),
                )
            )
        elif re.search(r"\bnext\s+month\b", lowered):
            next_month = now_date.month + 1 if now_date.month < 12 else 1
            next_year = now_date.year if now_date.month < 12 else now_date.year + 1
            _, last_day = calendar.monthrange(next_year, next_month)
            temporal_constraints.append(
                TemporalConstraint(
                    constraint_type=TemporalConstraintType.NEXT_MONTH,
                    raw_mention="next month",
                    window_start=date(next_year, next_month, 1),
                    window_end=date(next_year, next_month, last_day),
                )
            )

        if re.search(r"\b(open\s+now|currently\s+open)\b", lowered):
            temporal_constraints.append(
                TemporalConstraint(
                    constraint_type=TemporalConstraintType.CURRENTLY_OPEN,
                    raw_mention="currently open",
                    window_start=now_date,
                )
            )

        if re.search(r"\b(closing\s+soon)\b", lowered):
            temporal_constraints.append(
                TemporalConstraint(
                    constraint_type=TemporalConstraintType.CLOSING_SOON,
                    raw_mention="closing soon",
                    window_start=now_date,
                    window_end=now_date + timedelta(days=14),
                    days_window=14,
                )
            )

        days_match = re.search(r"\b(within|in)\s+(\d{1,3})\s+days\b", lowered)
        if days_match:
            days_count = int(days_match.group(2))
            temporal_constraints.append(
                TemporalConstraint(
                    constraint_type=TemporalConstraintType.WITHIN_DAYS,
                    raw_mention=days_match.group(0),
                    window_start=now_date,
                    window_end=now_date + timedelta(days=days_count),
                    days_window=days_count,
                )
            )

        # 10. Keyword extraction (terms not captured by structured constraints)
        stopwords = {
            "find",
            "show",
            "me",
            "which",
            "what",
            "where",
            "can",
            "i",
            "apply",
            "for",
            "the",
            "a",
            "an",
            "in",
            "to",
            "of",
            "and",
            "or",
            "is",
            "are",
            "tell",
            "about",
            "opportunities",
            "opportunity",
        }
        tokens = re.findall(r"\b[a-zA-Z]{3,}\b", lowered)
        keywords = [t for t in tokens if t not in stopwords]

        # 11. Explicit vs Unknown Tracking
        explicit: dict[str, Any] = {}
        if categories:
            explicit["categories"] = categories
        if countries:
            explicit["countries"] = countries
        if regions:
            explicit["regions"] = regions
        if degree_levels:
            explicit["degree_levels"] = degree_levels
        if fields:
            explicit["fields"] = fields
        if funding_constraints:
            explicit["funding"] = [fc.constraint_type.value for fc in funding_constraints]
        if test_constraints:
            explicit["tests"] = [
                f"{tc.test_name}:{tc.requirement_type.value}" for tc in test_constraints
            ]
        if audience_constraints:
            explicit["audience"] = audience_constraints
        if temporal_constraints:
            explicit["deadlines"] = [tc.constraint_type.value for tc in temporal_constraints]

        unknowns: list[str] = []
        if not degree_levels:
            unknowns.append("degree_level")
        if not countries and not regions:
            unknowns.append("target_location")
        if not fields:
            unknowns.append("field_of_study")
        if not funding_constraints:
            unknowns.append("funding_preference")

        return SearchIntent(
            original_query=cleaned_query,
            intent_type=intent_type,
            is_search_intent=is_search,
            opportunity_categories=categories,
            countries=countries,
            regions=regions,
            fields=fields,
            degree_levels=degree_levels,
            funding_constraints=funding_constraints,
            language_test_constraints=test_constraints,
            experience_constraints=[],
            nationality_constraints=audience_constraints,
            deadline_constraints=temporal_constraints,
            remote_preference=remote,
            keywords=keywords,
            explicit_constraints=explicit,
            implicit_context={},
            unknown_constraints=unknowns,
            confidence=0.95 if is_search else 0.90,
        )
