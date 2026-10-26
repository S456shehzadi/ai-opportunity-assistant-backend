"""Hard filter evaluation and soft preference boost engines."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.opportunities.eligibility.schemas import EligibilityResult, OverallEligibilityStatus
from app.opportunities.ranking.factors import (
    get_opp_category,
    get_opp_deadline,
    get_opp_degree_levels,
    get_opp_funding_type,
    get_opp_host_country,
    get_opp_is_rolling,
)
from app.opportunities.ranking.schemas import PreferencePriority, UserPreference
from app.services.normalization.education_normalizer import EducationNormalizer
from app.services.normalization.geo_normalizer import GeoNormalizer


class FilterEvaluation(BaseModel):
    """Result of evaluating an opportunity against mandatory filters."""

    passed: bool
    rejection_reason: str | None = None
    filter_category: str | None = None


class HardFilterEngine:
    """Enforces non-negotiable constraints (e.g. REQUIRED preferences and ineligibility)."""

    @classmethod
    def evaluate(
        cls,
        opp: Any,
        preferences: list[UserPreference],
        eligibility: EligibilityResult | None = None,
        include_ineligible: bool = False,
        include_expired: bool = False,
    ) -> FilterEvaluation:
        # 1. Eligibility Guardrail: Exclude CLEARLY_NOT_ELIGIBLE unless explicitly requested
        if not include_ineligible and eligibility is not None:
            if eligibility.overall_status == OverallEligibilityStatus.CLEARLY_NOT_ELIGIBLE:
                reasons = [
                    r.explanation
                    if isinstance(r.explanation, str)
                    else getattr(r.explanation, "text", str(r.explanation))
                    for r in eligibility.blocking_requirements
                    if r.explanation
                ]
                reason_str = (
                    "; ".join(reasons)
                    if reasons
                    else "Does not satisfy mandatory eligibility criteria."
                )
                return FilterEvaluation(
                    passed=False,
                    rejection_reason=f"Ineligible: {reason_str}",
                    filter_category="ELIGIBILITY",
                )

        # 2. Expired / Closed Filter
        if not include_expired and not get_opp_is_rolling(opp):
            dl = get_opp_deadline(opp)
            if dl is not None:
                from datetime import UTC, datetime

                current_dt = datetime.now(UTC)
                if isinstance(dl, datetime):
                    dl_dt = dl if dl.tzinfo else dl.replace(tzinfo=UTC)
                else:
                    dl_dt = datetime(dl.year, dl.month, dl.day, tzinfo=UTC)
                if (dl_dt - current_dt).days < 0:
                    return FilterEvaluation(
                        passed=False,
                        rejection_reason="Application deadline has passed.",
                        filter_category="DEADLINE",
                    )

        # 3. REQUIRED Preferences
        for pref in preferences:
            if pref.priority != PreferencePriority.REQUIRED:
                continue

            cat = pref.category.upper()
            val = pref.value

            # Funding Hard Filter
            if cat == "FUNDING":
                opp_funding = get_opp_funding_type(opp)
                wanted = str(val).upper()
                if "FULL" in wanted and opp_funding not in (
                    "fully_funded",
                    "full_funding",
                    "fully funded",
                ):
                    return FilterEvaluation(
                        passed=False,
                        rejection_reason=(
                            f"Excludes non-fully funded programs (found: {opp_funding})."
                        ),
                        filter_category="FUNDING",
                    )

            # Degree Level Hard Filter
            elif cat in ("DEGREE_LEVEL", "DEGREE"):
                opp_levels = [
                    EducationNormalizer.normalize_degree_level(lvl)
                    for lvl in get_opp_degree_levels(opp)
                ]
                wanted_levels = val if isinstance(val, list) else [val]
                norm_wanted = [
                    EducationNormalizer.normalize_degree_level(str(w)) for w in wanted_levels
                ]

                if opp_levels and not any(w in opp_levels for w in norm_wanted):
                    return FilterEvaluation(
                        passed=False,
                        rejection_reason=(
                            f"Degree level mismatch (required: {', '.join(norm_wanted)}; "
                            f"opportunity: {', '.join(opp_levels)})."
                        ),
                        filter_category="DEGREE_LEVEL",
                    )

            # Location / Country Hard Filter
            elif cat in ("LOCATION", "COUNTRY", "DESTINATION"):
                host = get_opp_host_country(opp)
                host_norm = GeoNormalizer.normalize_country(host)
                host_code = host_norm.code if host_norm else ""
                is_remote = getattr(opp, "is_remote", False) or "remote" in host.lower() or "online" in host.lower()

                wanted_locs = val if isinstance(val, list) else [val]
                is_loc_pass = False

                if is_remote or host.lower() in ("global", "worldwide", "international", "anywhere"):
                    is_loc_pass = True
                elif any(str(w).lower() in ("worldwide", "global", "anywhere") for w in wanted_locs):
                    is_loc_pass = True
                else:
                    for loc_req in wanted_locs:
                        norm_reg = GeoNormalizer.normalize_region(str(loc_req))
                        if (
                            norm_reg
                            and host_code
                            and GeoNormalizer.is_in_region(host_code, norm_reg)
                        ):
                            is_loc_pass = True
                            break
                        norm_c = GeoNormalizer.normalize_country(str(loc_req))
                        if norm_c and host_norm and norm_c.code == host_norm.code:
                            is_loc_pass = True
                            break
                        if str(loc_req).lower() in host.lower():
                            is_loc_pass = True
                            break

                if not is_loc_pass:
                    req_str = ", ".join(str(w) for w in wanted_locs)
                    return FilterEvaluation(
                        passed=False,
                        rejection_reason=f"Outside required locations ({req_str}; found: {host}).",
                        filter_category="LOCATION",
                    )

            # Applicant Nationality Eligibility Hard Filter
            elif cat in ("CITIZENSHIP", "NATIONALITY", "APPLICANT_COUNTRY"):
                user_citizenships = [str(c).lower() for c in (val if isinstance(val, list) else [val])]
                restricted = [str(c).lower() for c in getattr(opp, "restricted_applicant_countries", [])]
                if any(c in restricted for c in user_citizenships if c):
                    return FilterEvaluation(
                        passed=False,
                        rejection_reason="Applicant nationality or citizenship is restricted by official program guidelines.",
                        filter_category="ELIGIBILITY",
                    )

            # Opportunity Category Hard Filter
            elif cat == "CATEGORY":
                opp_cat = get_opp_category(opp)
                wanted_cats = [str(c).lower() for c in (val if isinstance(val, list) else [val])]
                if opp_cat not in wanted_cats and not any(w in opp_cat for w in wanted_cats):
                    return FilterEvaluation(
                        passed=False,
                        rejection_reason=(
                            f"Category mismatch (required: {', '.join(wanted_cats)}; "
                            f"found: {opp_cat})."
                        ),
                        filter_category="CATEGORY",
                    )

            # Excluded Destinations Hard Filter
            elif cat in ("EXCLUDED_COUNTRIES", "EXCLUDE_COUNTRY"):
                host = get_opp_host_country(opp).lower()
                excluded = [str(x).lower() for x in (val if isinstance(val, list) else [val])]
                if any(ex in host for ex in excluded if ex and ex != "none"):
                    return FilterEvaluation(
                        passed=False,
                        rejection_reason=f"Located in excluded destination ({host}).",
                        filter_category="EXCLUDED_COUNTRY",
                    )

            # Application Fee Hard Filter (when strictly required zero fee)
            elif cat in ("FEE", "NO_APPLICATION_FEE", "APPLICATION_FEE"):
                fee = getattr(opp, "application_fee", None)
                if fee is not None:
                    try:
                        if float(fee) > 0.0:
                            return FilterEvaluation(
                                passed=False,
                                rejection_reason=f"Requires an application fee ({fee}).",
                                filter_category="APPLICATION_FEE",
                            )
                    except (ValueError, TypeError):
                        pass

            # Mandatory English Test Hard Filter
            elif cat in ("NO_IELTS", "NO_ENGLISH_TEST"):
                if getattr(opp, "is_ielts_mandatory", False) or getattr(opp, "requires_ielts", False):
                    return FilterEvaluation(
                        passed=False,
                        rejection_reason="Strictly requires an IELTS test with no waiver available.",
                        filter_category="LANGUAGE_TEST",
                    )

            # Study Format Hard Filter
            elif cat in ("STUDY_FORMAT", "FORMAT", "REMOTE"):
                wanted_formats = [str(f).lower() for f in (val if isinstance(val, list) else [val])]
                opp_format = getattr(opp, "study_format", None) or getattr(opp, "delivery_mode", None)
                if (
                    opp_format
                    and any("online" in f or "remote" in f for f in wanted_formats)
                    and "in_person" in str(opp_format).lower()
                    and "online" not in str(opp_format).lower()
                    and "remote" not in str(opp_format).lower()
                ):
                    return FilterEvaluation(
                        passed=False,
                        rejection_reason=f"Study format mismatch (required: online/remote; found: {opp_format}).",
                        filter_category="STUDY_FORMAT",
                    )

        return FilterEvaluation(passed=True)


class SoftPreferenceEngine:
    """Calculates additive and multiplier boosts for non-mandatory preferences."""

    BOOST_MAP = {
        PreferencePriority.HIGH: 1.30,
        PreferencePriority.MEDIUM: 1.15,
        PreferencePriority.LOW: 1.05,
    }

    @classmethod
    def get_boost_multiplier(cls, priority: PreferencePriority) -> float:
        """Returns the multiplier boost for a given preference priority."""
        return cls.BOOST_MAP.get(priority, 1.0)
