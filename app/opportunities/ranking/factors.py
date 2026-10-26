"""Individual ranking factor calculators for evaluating opportunity fit and relevance."""

from __future__ import annotations

import re
from datetime import UTC, date, datetime
from typing import Any

from app.ai.query.intent_schemas import SearchIntent
from app.opportunities.eligibility.profile_adapter import UnifiedUserFacts
from app.opportunities.eligibility.schemas import EligibilityResult, OverallEligibilityStatus
from app.opportunities.ranking.schemas import (
    RankingFactorDetail,
    RankingFactorType,
    RecommendationConfidence,
    UserPreference,
)
from app.services.normalization.education_normalizer import EducationNormalizer
from app.services.normalization.geo_normalizer import GeoNormalizer

# ---------------------------------------------------------------------------
# Candidate Attribute Extraction Helpers
# ---------------------------------------------------------------------------


def get_opp_title(opp: Any) -> str:
    val = getattr(opp, "title", "")
    if hasattr(val, "value"):
        return str(val.value or "")
    return str(val or "")


def get_opp_org(opp: Any) -> str:
    val = getattr(opp, "organization", "")
    if hasattr(val, "value"):
        return str(val.value or "")
    return str(val or "")


def get_opp_description(opp: Any) -> str:
    val = getattr(opp, "description", "")
    if hasattr(val, "value"):
        return str(val.value or "")
    return str(val or "")


def get_opp_category(opp: Any) -> str:
    cat = getattr(opp, "category", "scholarship")
    if hasattr(cat, "value"):
        return str(cat.value or "").lower()
    return str(cat or "scholarship").lower()


def get_opp_host_country(opp: Any) -> str:
    hc = getattr(opp, "host_country", None)
    if hasattr(hc, "value"):
        return str(hc.value or "Global")
    if hc:
        return str(hc)
    countries = getattr(opp, "countries", [])
    if countries:
        return countries[0]
    return "Global"


def get_opp_funding_type(opp: Any) -> str:
    ft = getattr(opp, "funding_type", "unknown")
    if hasattr(ft, "value"):
        return str(ft.value or "").lower()
    return str(ft or "unknown").lower()


def get_opp_deadline(opp: Any) -> date | datetime | None:
    dl = getattr(opp, "deadline", None)
    if hasattr(dl, "value"):
        val = dl.value
        if isinstance(val, (date, datetime)):
            return val
        if isinstance(val, str) and val:
            try:
                return date.fromisoformat(val)
            except ValueError:
                return None
        return None
    if isinstance(dl, (date, datetime)):
        return dl
    if isinstance(dl, str) and dl:
        try:
            return date.fromisoformat(dl)
        except ValueError:
            return None
    return None


def get_opp_is_rolling(opp: Any) -> bool:
    is_roll = getattr(opp, "is_rolling", None)
    if hasattr(is_roll, "value"):
        return bool(is_roll.value)
    if is_roll is not None:
        return bool(is_roll)
    title = get_opp_title(opp).lower()
    desc = get_opp_description(opp).lower()
    return "rolling" in title or "rolling" in desc


def get_opp_min_gpa(opp: Any) -> float | None:
    min_gpa = getattr(opp, "minimum_gpa", None)
    if hasattr(min_gpa, "value") and min_gpa.value is not None:
        try:
            return float(min_gpa.value)
        except (ValueError, TypeError):
            pass
    min_cgpa = getattr(opp, "minimum_cgpa", None)
    if hasattr(min_cgpa, "value") and min_cgpa.value is not None:
        try:
            return float(min_cgpa.value)
        except (ValueError, TypeError):
            pass
    elig = getattr(opp, "eligibility", None)
    if elig:
        return getattr(elig, "min_gpa", None)
    return None


def get_opp_degree_levels(opp: Any) -> list[str]:
    levels = getattr(opp, "degree_levels", None)
    if levels:
        return levels
    elig = getattr(opp, "eligibility", None)
    if elig:
        return getattr(elig, "degree_levels", []) or []
    return []


def get_opp_fields(opp: Any) -> list[str]:
    fields = getattr(opp, "fields_of_study", None) or getattr(opp, "fields", None)
    if fields:
        return fields
    elig = getattr(opp, "eligibility", None)
    if elig:
        return getattr(elig, "fields_of_study", []) or []
    return []


def get_opp_source_domain(opp: Any) -> str:
    domain = getattr(opp, "source_domain", None)
    if domain:
        return str(domain)
    prov = getattr(opp, "provenance", None)
    if prov:
        return getattr(prov, "source_domain", "") or ""
    return ""


def get_opp_trust_score(opp: Any) -> float:
    score = getattr(opp, "source_trust_score", None) or getattr(opp, "trust_score", None)
    if score is not None:
        return float(score)
    prov = getattr(opp, "provenance", None)
    if prov:
        return float(getattr(prov, "source_trust_score", 0.70))
    return 0.70


def get_opp_last_verified(opp: Any) -> datetime | None:
    dt = (
        getattr(opp, "last_verified_at", None)
        or getattr(opp, "last_verified", None)
        or getattr(opp, "extracted_at", None)
    )
    if isinstance(dt, datetime):
        return dt
    return None


# ---------------------------------------------------------------------------
# Factor Calculators
# ---------------------------------------------------------------------------


class AcademicFitCalculator:
    """Evaluates GPA alignment and academic prerequisite fulfillment."""

    @classmethod
    def calculate(
        cls,
        opp: Any,
        user_facts: UnifiedUserFacts | None,
        eligibility: EligibilityResult | None = None,
    ) -> RankingFactorDetail:
        req_gpa = get_opp_min_gpa(opp)
        if user_facts is None or (not user_facts.highest_cgpa and not user_facts.academic_records):
            # Incomplete academic profile -> preserve discoverability with neutral score
            return RankingFactorDetail(
                factor_type=RankingFactorType.ACADEMIC_FIT,
                score=0.50,
                status="UNKNOWN",
                reason="User academic profile incomplete; academic fit cannot be fully verified.",
                confidence=RecommendationConfidence.LOW,
            )

        user_gpa = user_facts.highest_cgpa or user_facts.normalized_gpa_4_scale or 0.0

        if req_gpa is None or req_gpa <= 0:
            return RankingFactorDetail(
                factor_type=RankingFactorType.ACADEMIC_FIT,
                score=1.0,
                status="HIGH",
                reason="No minimum GPA requirement specified.",
                confidence=RecommendationConfidence.HIGH,
            )

        if user_gpa >= req_gpa:
            return RankingFactorDetail(
                factor_type=RankingFactorType.ACADEMIC_FIT,
                score=1.0,
                status="HIGH",
                reason=f"User GPA ({user_gpa:.2f}) meets or exceeds requirement ({req_gpa:.2f}).",
                confidence=RecommendationConfidence.HIGH,
            )
        elif user_gpa >= req_gpa - 0.2:
            return RankingFactorDetail(
                factor_type=RankingFactorType.ACADEMIC_FIT,
                score=0.75,
                status="MEDIUM",
                reason=f"User GPA ({user_gpa:.2f}) is slightly below requirement ({req_gpa:.2f}).",
                confidence=RecommendationConfidence.MEDIUM,
            )
        else:
            return RankingFactorDetail(
                factor_type=RankingFactorType.ACADEMIC_FIT,
                score=0.20,
                status="LOW",
                reason=f"User GPA ({user_gpa:.2f}) does not meet requirement ({req_gpa:.2f}).",
                confidence=RecommendationConfidence.HIGH,
            )


class FieldFitCalculator:
    """Compares user's field of study with program disciplines via taxonomy matching."""

    @classmethod
    def calculate(
        cls,
        opp: Any,
        user_facts: UnifiedUserFacts | None,
        preferences: list[UserPreference] | None = None,
    ) -> RankingFactorDetail:
        opp_fields = get_opp_fields(opp)
        title = get_opp_title(opp).lower()
        desc = get_opp_description(opp).lower()

        # Gather user fields
        user_fields: list[str] = []
        if user_facts:
            for rec in user_facts.academic_records:
                if rec.get("field_of_study"):
                    user_fields.append(str(rec["field_of_study"]).strip().lower())
        if preferences:
            for p in preferences:
                if p.category.upper() == "FIELD" and p.value:
                    if isinstance(p.value, list):
                        user_fields.extend(str(v).lower() for v in p.value)
                    else:
                        user_fields.append(str(p.value).lower())

        if not user_fields:
            return RankingFactorDetail(
                factor_type=RankingFactorType.FIELD_FIT,
                score=0.60,
                status="UNKNOWN",
                reason="User field not specified; field fit treated neutrally.",
                confidence=RecommendationConfidence.LOW,
            )

        if not opp_fields:
            # Broad opportunity open to all fields, or field not restricted
            return RankingFactorDetail(
                factor_type=RankingFactorType.FIELD_FIT,
                score=0.85,
                status="HIGH",
                reason="Opportunity is open to multiple or all disciplines.",
                confidence=RecommendationConfidence.MEDIUM,
            )

        # Check for exact or normalized taxonomic match
        best_score = 0.0
        best_reason = "Discipline mismatch."

        for u_f in user_fields:
            u_norm_field, u_broad = EducationNormalizer.normalize_field_of_study(u_f)
            for o_f in opp_fields:
                o_f_lower = o_f.lower()
                o_norm_field, o_broad = EducationNormalizer.normalize_field_of_study(o_f_lower)

                # Exact string or normalized concept match
                if u_f == o_f_lower or (
                    u_norm_field and o_norm_field and u_norm_field.lower() == o_norm_field.lower()
                ):
                    return RankingFactorDetail(
                        factor_type=RankingFactorType.FIELD_FIT,
                        score=1.0,
                        status="HIGH",
                        reason=f"Field directly matches: {o_f}.",
                        confidence=RecommendationConfidence.HIGH,
                    )

                # Broad discipline match (e.g. Computing & Information Technology)
                if (
                    u_broad
                    and o_broad
                    and u_broad.lower() != "general & interdisciplinary"
                    and u_broad.lower() == o_broad.lower()
                ):
                    if 0.80 > best_score:
                        best_score = 0.80
                        best_reason = f"Related field in same discipline ({u_broad}): {o_f}."

                # Substring overlap
                if u_f in o_f_lower or o_f_lower in u_f:
                    if 0.85 > best_score:
                        best_score = 0.85
                        best_reason = f"Close field alignment: {o_f}."

        # Check title / desc keyword occurrence if explicit field list had no direct match
        for u_f in user_fields:
            if u_f and re.search(r"\b" + re.escape(u_f) + r"\b", title + " " + desc):
                if 0.75 > best_score:
                    best_score = 0.75
                    best_reason = f"Field mentioned in program overview: {u_f}."

        if best_score > 0.0:
            return RankingFactorDetail(
                factor_type=RankingFactorType.FIELD_FIT,
                score=best_score,
                status="HIGH" if best_score >= 0.8 else "MEDIUM",
                reason=best_reason,
                confidence=RecommendationConfidence.HIGH,
            )

        return RankingFactorDetail(
            factor_type=RankingFactorType.FIELD_FIT,
            score=0.15,
            status="LOW",
            reason=(
                f"Target disciplines ({', '.join(opp_fields[:3])}) do not match user's background."
            ),
            confidence=RecommendationConfidence.HIGH,
        )


class FundingFitCalculator:
    """Evaluates opportunity funding level against user financial preferences."""

    @classmethod
    def calculate(
        cls, opp: Any, preferences: list[UserPreference] | None = None
    ) -> RankingFactorDetail:
        funding_type = get_opp_funding_type(opp)

        user_wants_full = False
        if preferences:
            for p in preferences:
                if p.category.upper() == "FUNDING":
                    val = str(p.value).upper()
                    if "FULL" in val:
                        user_wants_full = True

        if funding_type in ("fully_funded", "full_funding", "fully funded"):
            return RankingFactorDetail(
                factor_type=RankingFactorType.FUNDING_FIT,
                score=1.0,
                status="HIGH",
                reason="Fully funded opportunity (covers tuition and living costs).",
                confidence=RecommendationConfidence.HIGH,
            )
        elif funding_type in ("partially_funded", "partial"):
            score = 0.50 if user_wants_full else 0.75
            status = "MEDIUM"
            reason = (
                "Partially funded opportunity; user preferred full funding."
                if user_wants_full
                else "Partially funded opportunity."
            )
            return RankingFactorDetail(
                factor_type=RankingFactorType.FUNDING_FIT,
                score=score,
                status=status,
                reason=reason,
                confidence=RecommendationConfidence.HIGH,
            )
        elif funding_type in ("tuition_waiver", "stipend", "paid"):
            score = 0.40 if user_wants_full else 0.70
            return RankingFactorDetail(
                factor_type=RankingFactorType.FUNDING_FIT,
                score=score,
                status="MEDIUM",
                reason=f"Funding type: {funding_type.replace('_', ' ').title()}.",
                confidence=RecommendationConfidence.HIGH,
            )
        elif funding_type in ("unpaid", "self_funded", "no_funding"):
            score = 0.05 if user_wants_full else 0.20
            return RankingFactorDetail(
                factor_type=RankingFactorType.FUNDING_FIT,
                score=score,
                status="LOW",
                reason="Self-funded or unpaid program.",
                confidence=RecommendationConfidence.HIGH,
            )
        else:
            return RankingFactorDetail(
                factor_type=RankingFactorType.FUNDING_FIT,
                score=0.45,
                status="UNKNOWN",
                reason="Funding details are unverified or not explicitly stated.",
                confidence=RecommendationConfidence.LOW,
            )


class LocationFitCalculator:
    """Matches host country/region with user geographic preferences."""

    @classmethod
    def calculate(
        cls, opp: Any, preferences: list[UserPreference] | None = None
    ) -> RankingFactorDetail:
        host_country = get_opp_host_country(opp)
        host_norm = GeoNormalizer.normalize_country(host_country)
        host_code = host_norm.code if host_norm else ""

        preferred_locations: list[str] = []
        excluded_locations: list[str] = []

        if preferences:
            for p in preferences:
                cat = p.category.upper()
                if cat in ("LOCATION", "COUNTRY", "REGION"):
                    vals = p.value if isinstance(p.value, list) else [p.value]
                    for v in vals:
                        cleaned = str(v).strip().lower()
                        if p.priority.name == "REQUIRED" and cleaned.startswith("no "):
                            excluded_locations.append(cleaned[3:])
                        else:
                            preferred_locations.append(cleaned)
                elif cat == "EXCLUDE_COUNTRY":
                    vals = p.value if isinstance(p.value, list) else [p.value]
                    excluded_locations.extend(str(v).strip().lower() for v in vals)

        # Check exclusion first
        for ex in excluded_locations:
            if (host_norm and ex in (host_norm.name.lower(), host_norm.code.lower())) or (
                ex == host_country.lower()
            ):
                return RankingFactorDetail(
                    factor_type=RankingFactorType.LOCATION_FIT,
                    score=0.0,
                    status="MISMATCH",
                    reason=f"Location ({host_country}) is in excluded destinations.",
                    confidence=RecommendationConfidence.HIGH,
                )

        # If user has no specific geographic preferences
        if not preferred_locations:
            return RankingFactorDetail(
                factor_type=RankingFactorType.LOCATION_FIT,
                score=0.80,
                status="HIGH",
                reason=f"Location ({host_country}) - no geographical restrictions active.",
                confidence=RecommendationConfidence.MEDIUM,
            )

        # Check preferred locations
        is_matched = False
        matched_dest = ""
        for pref in preferred_locations:
            # Check if preference is a region like "europe"
            norm_region = GeoNormalizer.normalize_region(pref)
            if norm_region and host_code and GeoNormalizer.is_in_region(host_code, norm_region):
                is_matched = True
                matched_dest = norm_region
                break

            pref_country = GeoNormalizer.normalize_country(pref)
            if pref_country and host_norm and pref_country.code == host_norm.code:
                is_matched = True
                matched_dest = pref_country.name
                break
            if pref.lower() in host_country.lower() or host_country.lower() in pref.lower():
                is_matched = True
                matched_dest = pref
                break

        if is_matched:
            return RankingFactorDetail(
                factor_type=RankingFactorType.LOCATION_FIT,
                score=1.0,
                status="HIGH",
                reason=f"Location matches preferred destination: {matched_dest}.",
                confidence=RecommendationConfidence.HIGH,
            )

        if host_country.lower() in ("global", "worldwide", "international", "anywhere"):
            return RankingFactorDetail(
                factor_type=RankingFactorType.LOCATION_FIT,
                score=0.85,
                status="HIGH",
                reason="Global opportunity open across countries.",
                confidence=RecommendationConfidence.HIGH,
            )

        return RankingFactorDetail(
            factor_type=RankingFactorType.LOCATION_FIT,
            score=0.40,
            status="LOW",
            reason=f"Located in {host_country}, which is outside preferred locations.",
            confidence=RecommendationConfidence.HIGH,
        )


class DegreeLevelFitCalculator:
    """Matches desired academic qualification tier with program scope."""

    @classmethod
    def calculate(
        cls,
        opp: Any,
        user_facts: UnifiedUserFacts | None,
        preferences: list[UserPreference] | None = None,
    ) -> RankingFactorDetail:
        opp_levels = [lvl.lower() for lvl in get_opp_degree_levels(opp)]
        title = get_opp_title(opp).lower()

        # Desired level from preferences or user profile
        desired_levels: list[str] = []
        if preferences:
            for p in preferences:
                if p.category.upper() in ("DEGREE_LEVEL", "DEGREE"):
                    val = p.value if isinstance(p.value, list) else [p.value]
                    desired_levels.extend(str(v).lower() for v in val)

        if not desired_levels and user_facts:
            # Check current and past qualifications across records
            current = (user_facts.highest_degree_level or "").lower()
            if any(rec.get("normalized_degree_level") for rec in user_facts.academic_records):
                for rec in user_facts.academic_records:
                    deg = (rec.get("normalized_degree_level") or rec.get("degree_title") or "").lower()
                    if deg and deg not in desired_levels:
                        desired_levels.append(deg)

            if "bachelor" in current or "undergraduate" in current:
                desired_levels.extend(["bachelor", "master"])
            elif "master" in current or "postgraduate" in current:
                desired_levels.extend(["master", "phd", "doctorate"])
            elif "phd" in current or "doctorate" in current:
                desired_levels.extend(["phd", "postdoc", "postdoctoral"])
            elif "intermediate" in current or "fsc" in current or "ics" in current or "12th" in current:
                desired_levels.extend(["intermediate", "higher secondary", "bachelor", "undergraduate"])
            elif "matric" in current or "ssc" in current or "10th" in current or "gcse" in current or "o-level" in current:
                desired_levels.extend(["matriculation", "secondary", "intermediate", "high school"])
            elif "vocational" in current or "trade" in current:
                desired_levels.extend(["vocational", "certificate", "associate", "diploma"])
            elif "associate" in current or "dae" in current or "diploma" in current:
                desired_levels.extend(["associate", "diploma", "bachelor"])
            elif "middle" in current:
                desired_levels.extend(["middle school", "secondary", "matriculation"])
            elif "primary" in current or "elementary" in current:
                desired_levels.extend(["primary", "elementary", "middle school"])
            elif "high school" in current:
                desired_levels.extend(["high school", "intermediate", "bachelor"])

        if not desired_levels:
            return RankingFactorDetail(
                factor_type=RankingFactorType.DEGREE_LEVEL_FIT,
                score=0.75,
                status="UNKNOWN",
                reason="Target degree level not specified; treated neutrally.",
                confidence=RecommendationConfidence.LOW,
            )

        for d in desired_levels:
            norm_d = EducationNormalizer.normalize_degree_level(d)
            for o_lvl in opp_levels:
                norm_o = EducationNormalizer.normalize_degree_level(o_lvl)
                if norm_d == norm_o:
                    return RankingFactorDetail(
                        factor_type=RankingFactorType.DEGREE_LEVEL_FIT,
                        score=1.0,
                        status="HIGH",
                        reason=f"Degree level matches requested tier: {norm_o}.",
                        confidence=RecommendationConfidence.HIGH,
                    )
            # Check title
            if d in title or norm_d.lower() in title:
                return RankingFactorDetail(
                    factor_type=RankingFactorType.DEGREE_LEVEL_FIT,
                    score=0.95,
                    status="HIGH",
                    reason=f"Degree level matches program title ({norm_d}).",
                    confidence=RecommendationConfidence.HIGH,
                )

        if not opp_levels:
            return RankingFactorDetail(
                factor_type=RankingFactorType.DEGREE_LEVEL_FIT,
                score=0.70,
                status="MEDIUM",
                reason="Program does not restrict specific degree levels.",
                confidence=RecommendationConfidence.MEDIUM,
            )

        return RankingFactorDetail(
            factor_type=RankingFactorType.DEGREE_LEVEL_FIT,
            score=0.15,
            status="LOW",
            reason=f"Degree level mismatch: opportunity is for {', '.join(opp_levels)}.",
            confidence=RecommendationConfidence.HIGH,
        )


class DeadlineRelevanceCalculator:
    """Evaluates time remaining before application closes."""

    @classmethod
    def calculate(cls, opp: Any, now: datetime | None = None) -> RankingFactorDetail:
        if get_opp_is_rolling(opp):
            return RankingFactorDetail(
                factor_type=RankingFactorType.DEADLINE_RELEVANCE,
                score=0.90,
                status="HIGH",
                reason="Rolling admissions; applications reviewed on an ongoing basis.",
                confidence=RecommendationConfidence.HIGH,
            )

        deadline_val = get_opp_deadline(opp)
        if deadline_val is None:
            return RankingFactorDetail(
                factor_type=RankingFactorType.DEADLINE_RELEVANCE,
                score=0.50,
                status="UNKNOWN",
                reason="Application deadline not specified or pending verification.",
                confidence=RecommendationConfidence.LOW,
            )

        current_dt = now or datetime.now(UTC)
        if isinstance(deadline_val, datetime):
            d_dt = deadline_val if deadline_val.tzinfo else deadline_val.replace(tzinfo=UTC)
        else:
            d_dt = datetime(deadline_val.year, deadline_val.month, deadline_val.day, tzinfo=UTC)

        days_left = (d_dt - current_dt).days

        if days_left < 0:
            return RankingFactorDetail(
                factor_type=RankingFactorType.DEADLINE_RELEVANCE,
                score=0.0,
                status="MISMATCH",
                reason=f"Application closed {abs(days_left)} days ago.",
                confidence=RecommendationConfidence.HIGH,
            )
        elif days_left <= 3:
            return RankingFactorDetail(
                factor_type=RankingFactorType.DEADLINE_RELEVANCE,
                score=0.70,
                status="MEDIUM",
                reason=f"Approaching deadline: closes in {days_left} days.",
                confidence=RecommendationConfidence.HIGH,
            )
        elif days_left <= 14:
            return RankingFactorDetail(
                factor_type=RankingFactorType.DEADLINE_RELEVANCE,
                score=0.90,
                status="HIGH",
                reason=f"Deadline approaching in {days_left} days.",
                confidence=RecommendationConfidence.HIGH,
            )
        elif days_left <= 90:
            return RankingFactorDetail(
                factor_type=RankingFactorType.DEADLINE_RELEVANCE,
                score=1.0,
                status="HIGH",
                reason=f"Currently open (closes in {days_left} days; ample preparation time).",
                confidence=RecommendationConfidence.HIGH,
            )
        else:
            return RankingFactorDetail(
                factor_type=RankingFactorType.DEADLINE_RELEVANCE,
                score=0.95,
                status="HIGH",
                reason=f"Long-term opportunity (deadline in {days_left} days).",
                confidence=RecommendationConfidence.HIGH,
            )


class QueryRelevanceCalculator:
    """Measures lexical and intent alignment between search query and opportunity."""

    @classmethod
    def calculate(cls, opp: Any, search_intent: SearchIntent | None) -> RankingFactorDetail:
        if not search_intent or not search_intent.original_query:
            return RankingFactorDetail(
                factor_type=RankingFactorType.QUERY_RELEVANCE,
                score=0.80,
                status="HIGH",
                reason="No active query filter; general discovery mode.",
                confidence=RecommendationConfidence.MEDIUM,
            )

        title = get_opp_title(opp).lower()
        desc = get_opp_description(opp).lower()
        cat = get_opp_category(opp)
        country = get_opp_host_country(opp).lower()

        text_corpus = f"{title} {desc} {cat} {country}"

        # Match explicit search intent constraints
        matched_constraints = 0
        total_constraints = 0

        if search_intent.opportunity_categories:
            total_constraints += 1
            if any(c.lower() in text_corpus for c in search_intent.opportunity_categories):
                matched_constraints += 1

        if search_intent.countries or search_intent.regions:
            total_constraints += 1
            matched_loc = False
            for loc in search_intent.countries:
                if loc.lower() in text_corpus:
                    matched_loc = True
                    break
            if not matched_loc:
                host_norm = GeoNormalizer.normalize_country(country)
                host_code = host_norm.code if host_norm else ""
                for reg in search_intent.regions:
                    if reg.lower() in text_corpus:
                        matched_loc = True
                        break
                    if host_code and GeoNormalizer.is_in_region(host_code, reg):
                        matched_loc = True
                        break
            if matched_loc:
                matched_constraints += 1

        if search_intent.fields:
            total_constraints += 1
            if any(
                re.search(r"\b" + re.escape(f.lower()) + r"\b", text_corpus)
                for f in search_intent.fields
            ):
                matched_constraints += 1

        # Match keywords
        tokens = [
            t.lower()
            for t in re.findall(r"\w+", search_intent.original_query)
            if len(t) > 2 and t.lower() not in ("for", "and", "the", "with", "any", "all")
        ]
        if tokens:
            keyword_matches = sum(1 for t in tokens if t in text_corpus)
            keyword_ratio = keyword_matches / len(tokens)
        else:
            keyword_ratio = 1.0

        if total_constraints > 0:
            constraint_ratio = matched_constraints / total_constraints
            score = 0.6 * constraint_ratio + 0.4 * keyword_ratio
        else:
            score = keyword_ratio

        score = max(0.1, min(1.0, score))
        status = "HIGH" if score >= 0.75 else ("MEDIUM" if score >= 0.45 else "LOW")
        return RankingFactorDetail(
            factor_type=RankingFactorType.QUERY_RELEVANCE,
            score=score,
            status=status,
            reason=f"Matches search query intent ({int(score * 100)}% query relevance).",
            confidence=RecommendationConfidence.HIGH,
        )


class SourceQualityCalculator:
    """Evaluates domain authority and extraction trust score."""

    @classmethod
    def calculate(cls, opp: Any) -> RankingFactorDetail:
        domain = get_opp_source_domain(opp).lower()
        trust = get_opp_trust_score(opp)

        is_official = any(
            domain.endswith(ext)
            for ext in (".edu", ".ac.uk", ".edu.pk", ".gov", ".org", ".europa.eu")
        )

        if is_official or trust >= 0.85:
            score = 1.0
            status = "HIGH"
            reason = f"Verified official source ({domain or 'primary institution'})."
        elif trust >= 0.65:
            score = 0.80
            status = "HIGH"
            reason = f"Reputable publisher domain ({domain})."
        elif trust >= 0.45:
            score = 0.60
            status = "MEDIUM"
            reason = f"Secondary source ({domain}); secondary verification recommended."
        else:
            score = 0.35
            status = "LOW"
            reason = "Unverified directory or unknown domain."

        return RankingFactorDetail(
            factor_type=RankingFactorType.SOURCE_QUALITY,
            score=score,
            status=status,
            reason=reason,
            confidence=RecommendationConfidence.HIGH,
        )


class EligibilityCompletenessCalculator:
    """Evaluates clarity and completeness of requirement evaluations."""

    @classmethod
    def calculate(cls, eligibility_result: EligibilityResult | None) -> RankingFactorDetail:
        if eligibility_result is None:
            return RankingFactorDetail(
                factor_type=RankingFactorType.ELIGIBILITY_COMPLETENESS,
                score=0.60,
                status="UNKNOWN",
                reason="Eligibility has not been formally evaluated.",
                confidence=RecommendationConfidence.LOW,
            )

        status = eligibility_result.overall_status
        if status == OverallEligibilityStatus.CLEARLY_ELIGIBLE:
            return RankingFactorDetail(
                factor_type=RankingFactorType.ELIGIBILITY_COMPLETENESS,
                score=1.0,
                status="HIGH",
                reason="All mandatory eligibility criteria are satisfied.",
                confidence=RecommendationConfidence.HIGH,
            )
        elif status == OverallEligibilityStatus.POTENTIALLY_ELIGIBLE:
            return RankingFactorDetail(
                factor_type=RankingFactorType.ELIGIBILITY_COMPLETENESS,
                score=0.75,
                status="MEDIUM",
                reason="Potentially eligible; some criteria require additional user details.",
                confidence=RecommendationConfidence.MEDIUM,
            )
        elif status == OverallEligibilityStatus.NEEDS_VERIFICATION:
            return RankingFactorDetail(
                factor_type=RankingFactorType.ELIGIBILITY_COMPLETENESS,
                score=0.65,
                status="MEDIUM",
                reason="Key requirements (e.g. test scores or waivers) need user verification.",
                confidence=RecommendationConfidence.MEDIUM,
            )
        elif status == OverallEligibilityStatus.CONFLICTING_INFORMATION:
            return RankingFactorDetail(
                factor_type=RankingFactorType.ELIGIBILITY_COMPLETENESS,
                score=0.40,
                status="LOW",
                reason="Conflicting eligibility criteria detected across sources.",
                confidence=RecommendationConfidence.LOW,
            )
        else:  # CLEARLY_NOT_ELIGIBLE
            return RankingFactorDetail(
                factor_type=RankingFactorType.ELIGIBILITY_COMPLETENESS,
                score=0.05,
                status="MISMATCH",
                reason="One or more mandatory eligibility requirements are not satisfied.",
                confidence=RecommendationConfidence.HIGH,
            )
