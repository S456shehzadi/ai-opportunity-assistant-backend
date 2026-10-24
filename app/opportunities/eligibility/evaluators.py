"""Deterministic eligibility evaluators for academic, demographic, test, and experience criteria."""

from __future__ import annotations

import re
from datetime import UTC, datetime

from app.opportunities.eligibility.evidence import EligibilityEvidenceLinker
from app.opportunities.eligibility.explanations import ExplanationBuilder
from app.opportunities.eligibility.profile_adapter import UnifiedUserFacts
from app.opportunities.eligibility.requirement_adapter import OpportunityRequirementItem
from app.opportunities.eligibility.schemas import (
    EligibilityConfidence,
    RequirementEvaluation,
    RequirementPriority,
    RequirementStatus,
)
from app.services.normalization.education_normalizer import EducationNormalizer
from app.services.normalization.geo_normalizer import GeoNormalizer


class AcademicEvaluator:
    """Evaluates academic performance, degree levels, and disciplines."""

    DEGREE_HIERARCHY = {
        "high school": 1,
        "associate": 2,
        "bachelor's": 3,
        "bachelor": 3,
        "undergraduate": 3,
        "master's": 4,
        "master": 4,
        "graduate": 4,
        "postgraduate": 4,
        "phd": 5,
        "doctorate": 5,
        "doctoral": 5,
        "postdoctoral": 6,
        "postdoc": 6,
    }

    @classmethod
    def evaluate_cgpa(
        cls, user_facts: UnifiedUserFacts, req: OpportunityRequirementItem
    ) -> RequirementEvaluation:
        """Evaluates user CGPA against the minimum cutoff."""
        user_cgpa = user_facts.highest_cgpa or user_facts.normalized_gpa_4_scale

        # Search across all academic records if specific degree is in requirement description
        record_context = None
        for rec in user_facts.academic_records:
            if rec.get("cgpa") is not None:
                user_cgpa = float(rec["cgpa"])
                record_context = rec.get("institution") or rec.get("degree_title")
                break

        if user_cgpa is None:
            return RequirementEvaluation(
                requirement_id=req.requirement_id,
                requirement_type="cgpa",
                requirement_description=req.description,
                status=RequirementStatus.UNKNOWN,
                priority=req.priority,
                user_value=None,
                required_value=req.required_value,
                comparison=f"? {req.operator} {req.required_value}",
                explanation=(
                    "CGPA requirement found, but your academic CGPA is not provided in profile."
                ),
                structured_explanation=ExplanationBuilder.unknown(
                    "CGPA information not provided in user profile."
                ),
                confidence=EligibilityConfidence.MEDIUM,
                opportunity_evidence=req.opportunity_evidence,
            )

        target_cgpa = float(req.required_value)
        comparison_str = f"{user_cgpa:.2f} {req.operator} {target_cgpa:.2f}"
        user_ev = EligibilityEvidenceLinker.create_user_evidence(
            source_section="academic_performance",
            field_name="cgpa",
            value=user_cgpa,
            context=record_context,
        )

        is_match = False
        if req.operator in (">=", "=>"):
            is_match = user_cgpa >= target_cgpa
        elif req.operator in ("<=", "=<"):
            is_match = user_cgpa <= target_cgpa
        elif req.operator in (">",):
            is_match = user_cgpa > target_cgpa
        elif req.operator in ("<",):
            is_match = user_cgpa < target_cgpa
        elif req.operator in ("==", "="):
            is_match = abs(user_cgpa - target_cgpa) < 0.01

        status = RequirementStatus.MATCH if is_match else RequirementStatus.NO_MATCH
        msg = (
            f"Your CGPA of {user_cgpa:.2f} meets the minimum requirement of {target_cgpa:.2f}."
            if is_match
            else (
                f"Your CGPA of {user_cgpa:.2f} does not meet the minimum requirement of "
                f"{target_cgpa:.2f}."
            )
        )

        return RequirementEvaluation(
            requirement_id=req.requirement_id,
            requirement_type="cgpa",
            requirement_description=req.description,
            status=status,
            priority=req.priority,
            user_value=user_cgpa,
            required_value=target_cgpa,
            comparison=comparison_str,
            user_evidence=user_ev,
            opportunity_evidence=req.opportunity_evidence,
            explanation=msg,
            structured_explanation=(
                ExplanationBuilder.match(msg) if is_match else ExplanationBuilder.no_match(msg)
            ),
            confidence=EligibilityConfidence.HIGH,
        )

    @classmethod
    def evaluate_percentage(
        cls, user_facts: UnifiedUserFacts, req: OpportunityRequirementItem
    ) -> RequirementEvaluation:
        """Evaluates academic percentage threshold."""
        user_pct = user_facts.highest_percentage

        if user_pct is None:
            return RequirementEvaluation(
                requirement_id=req.requirement_id,
                requirement_type="percentage",
                requirement_description=req.description,
                status=RequirementStatus.UNKNOWN,
                priority=req.priority,
                user_value=None,
                required_value=req.required_value,
                comparison=f"? {req.operator} {req.required_value}%",
                explanation=("Percentage requirement found, but your percentage is not provided."),
                structured_explanation=ExplanationBuilder.unknown(
                    "Percentage not provided in profile."
                ),
                confidence=EligibilityConfidence.MEDIUM,
                opportunity_evidence=req.opportunity_evidence,
            )

        target_pct = float(req.required_value)
        comparison_str = f"{user_pct:.1f}% {req.operator} {target_pct:.1f}%"
        is_match = (
            user_pct >= target_pct if req.operator in (">=", "=>") else user_pct == target_pct
        )
        status = RequirementStatus.MATCH if is_match else RequirementStatus.NO_MATCH

        msg = (
            f"Your percentage of {user_pct:.1f}% meets the requirement of {target_pct:.1f}%."
            if is_match
            else (
                f"Your percentage of {user_pct:.1f}% does not meet the required cutoff of "
                f"{target_pct:.1f}%."
            )
        )

        user_ev = EligibilityEvidenceLinker.create_user_evidence(
            source_section="academic_performance",
            field_name="percentage",
            value=user_pct,
        )

        return RequirementEvaluation(
            requirement_id=req.requirement_id,
            requirement_type="percentage",
            requirement_description=req.description,
            status=status,
            priority=req.priority,
            user_value=user_pct,
            required_value=target_pct,
            comparison=comparison_str,
            user_evidence=user_ev,
            opportunity_evidence=req.opportunity_evidence,
            explanation=msg,
            structured_explanation=(
                ExplanationBuilder.match(msg) if is_match else ExplanationBuilder.no_match(msg)
            ),
            confidence=EligibilityConfidence.HIGH,
        )

    @classmethod
    def evaluate_degree_level(
        cls, user_facts: UnifiedUserFacts, req: OpportunityRequirementItem
    ) -> RequirementEvaluation:
        """Evaluates whether user holds or pursues an eligible degree level."""
        allowed_degrees = (
            req.required_value
            if isinstance(req.required_value, list)
            else [str(req.required_value)]
        )
        allowed_normalized = [cls._normalize_degree(d) for d in allowed_degrees]

        # Scan all user degrees
        user_degrees: list[str] = []
        user_evidences = []
        for rec in user_facts.academic_records:
            deg = rec.get("normalized_degree_level") or rec.get("degree_title")
            if deg:
                norm_deg = cls._normalize_degree(deg)
                user_degrees.append(norm_deg)
                user_evidences.append(
                    EligibilityEvidenceLinker.create_user_evidence(
                        source_section="education",
                        field_name="degree_level",
                        value=deg,
                        context=rec.get("institution") or rec.get("field_of_study"),
                    )
                )

        if not user_degrees:
            return RequirementEvaluation(
                requirement_id=req.requirement_id,
                requirement_type="degree_level",
                requirement_description=req.description,
                status=RequirementStatus.UNKNOWN,
                priority=req.priority,
                user_value=None,
                required_value=allowed_degrees,
                explanation=(
                    "Degree level requirement found, but education history is not declared."
                ),
                structured_explanation=ExplanationBuilder.unknown(
                    "No education history declared in profile."
                ),
                confidence=EligibilityConfidence.MEDIUM,
                opportunity_evidence=req.opportunity_evidence,
            )

        # Check for intersection or hierarchy entry progression
        matched_degrees = [d for d in user_degrees if d in allowed_normalized]
        if not matched_degrees:
            # Check progression in degree hierarchy (e.g. Bachelor's qualifies for Master's program)
            user_ranks = [cls.DEGREE_HIERARCHY.get(d.lower(), 0) for d in user_degrees]
            req_ranks = [cls.DEGREE_HIERARCHY.get(d.lower(), 0) for d in allowed_normalized]
            max_user_rank = max(user_ranks) if user_ranks else 0
            min_req_rank = min(req_ranks) if req_ranks else 0

            # Direct entry progression: user has required degree or immediate prior degree
            if max_user_rank > 0 and (
                max_user_rank == min_req_rank or max_user_rank == min_req_rank - 1
            ):
                best_idx = user_ranks.index(max_user_rank)
                matched_degrees = [user_degrees[best_idx]]

        if matched_degrees:
            user_ev = user_evidences[user_degrees.index(matched_degrees[0])]
            deg_targets = ", ".join(allowed_degrees)
            msg = (
                f"Your degree level ({matched_degrees[0]}) satisfies the requirement "
                f"for {deg_targets}."
            )
            return RequirementEvaluation(
                requirement_id=req.requirement_id,
                requirement_type="degree_level",
                requirement_description=req.description,
                status=RequirementStatus.MATCH,
                priority=req.priority,
                user_value=matched_degrees[0],
                required_value=allowed_degrees,
                comparison=f"{matched_degrees[0]} qualifies for {allowed_normalized}",
                user_evidence=user_ev,
                opportunity_evidence=req.opportunity_evidence,
                explanation=msg,
                structured_explanation=ExplanationBuilder.match(msg),
                confidence=EligibilityConfidence.HIGH,
            )

        user_deg_str = ", ".join(set(user_degrees))
        req_deg_str = ", ".join(allowed_degrees)
        msg = f"Your degrees ({user_deg_str}) do not match required level(s): {req_deg_str}."
        return RequirementEvaluation(
            requirement_id=req.requirement_id,
            requirement_type="degree_level",
            requirement_description=req.description,
            status=RequirementStatus.NO_MATCH,
            priority=req.priority,
            user_value=user_degrees,
            required_value=allowed_degrees,
            comparison=f"{user_degrees} not in {allowed_normalized}",
            user_evidence=user_evidences[0] if user_evidences else None,
            opportunity_evidence=req.opportunity_evidence,
            explanation=msg,
            structured_explanation=ExplanationBuilder.no_match(msg),
            confidence=EligibilityConfidence.HIGH,
        )

    @classmethod
    def evaluate_field_of_study(
        cls, user_facts: UnifiedUserFacts, req: OpportunityRequirementItem
    ) -> RequirementEvaluation:
        """Evaluates academic discipline with taxonomy mapping and related field allowances."""
        target_fields = (
            req.required_value
            if isinstance(req.required_value, list)
            else [str(req.required_value)]
        )

        user_fields: list[str] = []
        for rec in user_facts.academic_records:
            f = rec.get("normalized_field") or rec.get("field_of_study") or rec.get("field")
            if f:
                user_fields.append(f)

        if not user_fields:
            return RequirementEvaluation(
                requirement_id=req.requirement_id,
                requirement_type="field_of_study",
                requirement_description=req.description,
                status=RequirementStatus.UNKNOWN,
                priority=req.priority,
                user_value=None,
                required_value=target_fields,
                explanation=(
                    "Field of study requirement found, but your major/field is not provided."
                ),
                structured_explanation=ExplanationBuilder.unknown(
                    "Field of study not declared in profile."
                ),
                confidence=EligibilityConfidence.MEDIUM,
                opportunity_evidence=req.opportunity_evidence,
            )

        # Check exact or taxonomic match
        for uf in user_fields:
            uf_norm, uf_broad = EducationNormalizer.normalize_field_of_study(uf)
            uf_norm_str = (uf_norm or uf).lower()
            for tf in target_fields:
                tf_norm, tf_broad = EducationNormalizer.normalize_field_of_study(tf)
                tf_norm_str = (tf_norm or tf).lower()
                if (
                    uf.lower() == tf.lower()
                    or uf_norm_str == tf_norm_str
                    or tf_norm_str in uf_norm_str
                    or (
                        uf_broad
                        and tf_broad
                        and uf_broad == tf_broad
                        and uf_broad != "General & Interdisciplinary"
                    )
                ):
                    user_ev = EligibilityEvidenceLinker.create_user_evidence(
                        source_section="education",
                        field_name="field_of_study",
                        value=uf,
                    )
                    msg = f"Your field of study '{uf}' matches eligible discipline '{tf}'."
                    return RequirementEvaluation(
                        requirement_id=req.requirement_id,
                        requirement_type="field_of_study",
                        requirement_description=req.description,
                        status=RequirementStatus.MATCH,
                        priority=req.priority,
                        user_value=uf,
                        required_value=target_fields,
                        comparison=f"'{uf}' matches '{tf}'",
                        user_evidence=user_ev,
                        opportunity_evidence=req.opportunity_evidence,
                        explanation=msg,
                        structured_explanation=ExplanationBuilder.match(msg),
                        confidence=EligibilityConfidence.HIGH,
                    )

        u_str = ", ".join(user_fields)
        t_str = ", ".join(target_fields)
        msg = f"Your field '{u_str}' does not match listed disciplines: {t_str}."
        return RequirementEvaluation(
            requirement_id=req.requirement_id,
            requirement_type="field_of_study",
            requirement_description=req.description,
            status=RequirementStatus.NO_MATCH,
            priority=req.priority,
            user_value=user_fields,
            required_value=target_fields,
            comparison=f"'{user_fields}' not in '{target_fields}'",
            opportunity_evidence=req.opportunity_evidence,
            explanation=msg,
            structured_explanation=ExplanationBuilder.no_match(msg),
            confidence=EligibilityConfidence.HIGH,
        )

    @classmethod
    def _normalize_degree(cls, deg: str) -> str:
        d = deg.lower().strip()
        for k, v in cls.DEGREE_HIERARCHY.items():
            if k in d:
                if v == 3:
                    return "Bachelor's"
                if v == 4:
                    return "Master's"
                if v == 5:
                    return "PhD"
                if v == 6:
                    return "Postdoctoral"
        return deg


class NationalityResidencyEvaluator:
    """Evaluates nationality and residency criteria strictly from explicit profile entries."""

    @classmethod
    def evaluate_nationality(
        cls, user_facts: UnifiedUserFacts, req: OpportunityRequirementItem
    ) -> RequirementEvaluation:
        """Matches user nationality without inferring from IP, location, or name."""
        user_nat = user_facts.nationality
        if not user_nat or user_nat.lower() in ("unknown", "unspecified"):
            return RequirementEvaluation(
                requirement_id=req.requirement_id,
                requirement_type="nationality",
                requirement_description=req.description,
                status=RequirementStatus.UNKNOWN,
                priority=req.priority,
                user_value=None,
                required_value=req.required_value,
                explanation=(
                    "Nationality requirement exists, but your nationality is not declared."
                ),
                structured_explanation=ExplanationBuilder.unknown(
                    "Nationality not declared in user profile."
                ),
                confidence=EligibilityConfidence.HIGH,
                opportunity_evidence=req.opportunity_evidence,
            )

        allowed = (
            req.required_value
            if isinstance(req.required_value, list)
            else [str(req.required_value)]
        )

        # Global or International
        if any(
            term in [a.lower() for a in allowed]
            for term in ("global", "all countries", "international")
        ):
            user_ev = EligibilityEvidenceLinker.create_user_evidence(
                source_section="identity_context",
                field_name="nationality",
                value=user_nat,
            )
            msg = f"Your nationality ({user_nat}) is eligible (open to global applicants)."
            return RequirementEvaluation(
                requirement_id=req.requirement_id,
                requirement_type="nationality",
                requirement_description=req.description,
                status=RequirementStatus.MATCH,
                priority=req.priority,
                user_value=user_nat,
                required_value=allowed,
                comparison=f"{user_nat} in Global",
                user_evidence=user_ev,
                opportunity_evidence=req.opportunity_evidence,
                explanation=msg,
                structured_explanation=ExplanationBuilder.match(msg),
                confidence=EligibilityConfidence.HIGH,
            )

        # Check membership via GeoNormalizer
        norm_user = GeoNormalizer.normalize_country(user_nat)
        user_code = norm_user.code if norm_user else None

        is_match = False
        matched_term = None
        for a in allowed:
            norm_a = GeoNormalizer.normalize_country(a)
            if (
                user_nat.lower() == a.lower()
                or (norm_a and user_code and norm_a.code == user_code)
                or (user_code and GeoNormalizer.is_in_region(user_code, a))
            ):
                is_match = True
                matched_term = a
                break

        user_ev = EligibilityEvidenceLinker.create_user_evidence(
            source_section="identity_context",
            field_name="nationality",
            value=user_nat,
        )

        if is_match:
            msg = f"Your nationality ({user_nat}) matches criteria ({matched_term})."
            return RequirementEvaluation(
                requirement_id=req.requirement_id,
                requirement_type="nationality",
                requirement_description=req.description,
                status=RequirementStatus.MATCH,
                priority=req.priority,
                user_value=user_nat,
                required_value=allowed,
                comparison=f"{user_nat} in {allowed}",
                user_evidence=user_ev,
                opportunity_evidence=req.opportunity_evidence,
                explanation=msg,
                structured_explanation=ExplanationBuilder.match(msg),
                confidence=EligibilityConfidence.HIGH,
            )

        allowed_str = ", ".join(allowed)
        msg = f"Your nationality ({user_nat}) is not included in: {allowed_str}."
        return RequirementEvaluation(
            requirement_id=req.requirement_id,
            requirement_type="nationality",
            requirement_description=req.description,
            status=RequirementStatus.NO_MATCH,
            priority=req.priority,
            user_value=user_nat,
            required_value=allowed,
            comparison=f"{user_nat} not in {allowed}",
            user_evidence=user_ev,
            opportunity_evidence=req.opportunity_evidence,
            explanation=msg,
            structured_explanation=ExplanationBuilder.no_match(msg),
            confidence=EligibilityConfidence.HIGH,
        )


class TestEvaluator:
    """Evaluates standardized tests and English-medium waiver exceptions."""

    @classmethod
    def evaluate_test(
        cls, user_facts: UnifiedUserFacts, req: OpportunityRequirementItem
    ) -> RequirementEvaluation:
        """Evaluates standardized language/academic test scores with conditional waiver logic."""
        test_key = req.requirement_type.upper()
        # Find test in user profile
        user_test = user_facts.tests.get(test_key)

        # 1. Check English-medium degree waiver first if permitted
        if req.waiver_allowed:
            if user_facts.has_english_medium_degree:
                msg = (
                    f"{req.requirement_type.upper()} requirement waived: Your profile shows a "
                    "verified degree taught in English."
                )
                user_ev = EligibilityEvidenceLinker.create_user_evidence(
                    source_section="education",
                    field_name="has_english_medium_degree",
                    value=True,
                    context="English-medium degree waiver verified",
                )
                return RequirementEvaluation(
                    requirement_id=req.requirement_id,
                    requirement_type=req.requirement_type,
                    requirement_description=req.description,
                    status=RequirementStatus.MATCH,
                    priority=req.priority,
                    user_value="English-Medium Degree Waiver",
                    required_value=req.required_value,
                    comparison="Waiver satisfied",
                    user_evidence=user_ev,
                    opportunity_evidence=req.opportunity_evidence,
                    explanation=msg,
                    structured_explanation=ExplanationBuilder.conditional(msg),
                    confidence=EligibilityConfidence.HIGH,
                )

        # 2. If user test score is missing
        if not user_test or not user_test.get("score"):
            # If waiver allowed but user EMI is unknown, mark CONDITIONAL
            if req.waiver_allowed:
                msg = (
                    f"{req.requirement_type.upper()} requirement found, but no test score is "
                    "provided. Prior English degree may qualify for a waiver."
                )
                return RequirementEvaluation(
                    requirement_id=req.requirement_id,
                    requirement_type=req.requirement_type,
                    requirement_description=req.description,
                    status=RequirementStatus.CONDITIONAL,
                    priority=req.priority,
                    user_value=None,
                    required_value=req.required_value,
                    explanation=msg,
                    structured_explanation=ExplanationBuilder.conditional(msg),
                    confidence=EligibilityConfidence.MEDIUM,
                    opportunity_evidence=req.opportunity_evidence,
                    requires_verification=True,
                )

            msg = (
                f"{req.requirement_type.upper()} requirement found, but your test score is "
                "not provided in your profile."
            )
            return RequirementEvaluation(
                requirement_id=req.requirement_id,
                requirement_type=req.requirement_type,
                requirement_description=req.description,
                status=RequirementStatus.UNKNOWN,
                priority=req.priority,
                user_value=None,
                required_value=req.required_value,
                explanation=msg,
                structured_explanation=ExplanationBuilder.unknown(msg),
                confidence=EligibilityConfidence.MEDIUM,
                opportunity_evidence=req.opportunity_evidence,
            )

        # 3. Numeric comparison
        raw_score = user_test.get("score")
        user_score = None
        try:
            user_score = float(raw_score)
        except ValueError:
            pass

        target_score = None
        try:
            target_score = float(req.required_value)
        except (ValueError, TypeError):
            pass

        user_ev = EligibilityEvidenceLinker.create_user_evidence(
            source_section="tests",
            field_name=test_key,
            value=raw_score,
            context=f"Test date: {user_test.get('test_date')}",
        )

        if user_score is not None and target_score is not None:
            comparison_str = f"{user_score} {req.operator} {target_score}"
            is_match = (
                user_score >= target_score
                if req.operator in (">=", "=>")
                else user_score == target_score
            )
            status = RequirementStatus.MATCH if is_match else RequirementStatus.NO_MATCH

            meet_str = "meets" if is_match else "does not meet"
            msg = (
                f"Your {test_key} score of {user_score} {meet_str} the minimum "
                f"requirement of {target_score}."
            )

            return RequirementEvaluation(
                requirement_id=req.requirement_id,
                requirement_type=req.requirement_type,
                requirement_description=req.description,
                status=status,
                priority=req.priority,
                user_value=user_score,
                required_value=target_score,
                comparison=comparison_str,
                user_evidence=user_ev,
                opportunity_evidence=req.opportunity_evidence,
                explanation=msg,
                structured_explanation=(
                    ExplanationBuilder.match(msg) if is_match else ExplanationBuilder.no_match(msg)
                ),
                confidence=EligibilityConfidence.HIGH,
            )

        # Non-numeric fallback
        is_match = str(raw_score).lower() == str(req.required_value).lower()
        status = RequirementStatus.MATCH if is_match else RequirementStatus.NO_MATCH
        m_str = "matches" if is_match else "does not match"
        msg = f"Your test score '{raw_score}' {m_str} '{req.required_value}'."
        return RequirementEvaluation(
            requirement_id=req.requirement_id,
            requirement_type=req.requirement_type,
            requirement_description=req.description,
            status=status,
            priority=req.priority,
            user_value=raw_score,
            required_value=req.required_value,
            user_evidence=user_ev,
            opportunity_evidence=req.opportunity_evidence,
            explanation=msg,
            confidence=EligibilityConfidence.HIGH,
        )


class DeadlineEvaluator:
    """Compares application deadline against current date with timezone awareness."""

    @classmethod
    def evaluate_deadline(
        cls, user_facts: UnifiedUserFacts, req: OpportunityRequirementItem
    ) -> RequirementEvaluation:
        """Evaluates whether the opportunity application window is currently open."""
        val = str(req.required_value).upper()
        if "ROLLING" in val:
            msg = "This opportunity operates on a rolling admissions basis."
            return RequirementEvaluation(
                requirement_id=req.requirement_id,
                requirement_type="deadline",
                requirement_description=req.description,
                status=RequirementStatus.MATCH,
                priority=req.priority,
                user_value="Current date",
                required_value="Rolling",
                comparison="Rolling admissions",
                opportunity_evidence=req.opportunity_evidence,
                explanation=msg,
                structured_explanation=ExplanationBuilder.match(msg),
                confidence=EligibilityConfidence.HIGH,
            )

        # Parse ISO date
        now = datetime.now(UTC).date()
        date_match = re.search(r"\d{4}-\d{2}-\d{2}", str(req.required_value))
        if date_match:
            try:
                deadline_date = datetime.strptime(date_match.group(0), "%Y-%m-%d").date()
                is_open = deadline_date >= now
                status = RequirementStatus.MATCH if is_open else RequirementStatus.NO_MATCH
                msg = (
                    f"Application deadline ({deadline_date}) is open."
                    if is_open
                    else f"Application deadline ({deadline_date}) has passed."
                )
                return RequirementEvaluation(
                    requirement_id=req.requirement_id,
                    requirement_type="deadline",
                    requirement_description=req.description,
                    status=status,
                    priority=req.priority,
                    user_value=str(now),
                    required_value=str(deadline_date),
                    comparison=f"{now} <= {deadline_date}",
                    opportunity_evidence=req.opportunity_evidence,
                    explanation=msg,
                    structured_explanation=(
                        ExplanationBuilder.match(msg)
                        if is_open
                        else ExplanationBuilder.no_match(msg)
                    ),
                    confidence=EligibilityConfidence.HIGH,
                )
            except ValueError:
                pass

        return RequirementEvaluation(
            requirement_id=req.requirement_id,
            requirement_type="deadline",
            requirement_description=req.description,
            status=RequirementStatus.UNKNOWN,
            priority=req.priority,
            user_value=None,
            required_value=req.required_value,
            explanation="Deadline date could not be definitively evaluated.",
            confidence=EligibilityConfidence.LOW,
            opportunity_evidence=req.opportunity_evidence,
        )


class ExperienceEvaluator:
    """Evaluates work experience, research, and publications."""

    @classmethod
    def evaluate_experience(
        cls, user_facts: UnifiedUserFacts, req: OpportunityRequirementItem
    ) -> RequirementEvaluation:
        """Evaluates minimum work or research experience."""
        target_years = 0.0
        try:
            target_years = float(req.required_value)
        except (ValueError, TypeError):
            pass

        user_years = user_facts.work_experience_years
        is_match = user_years >= target_years
        status = RequirementStatus.MATCH if is_match else RequirementStatus.NO_MATCH

        user_ev = EligibilityEvidenceLinker.create_user_evidence(
            source_section="work_experience",
            field_name="total_years",
            value=user_years,
        )

        if is_match:
            msg = (
                f"Your work experience of {user_years:.1f} years satisfies the required "
                f"{target_years:.1f} years."
            )
        else:
            msg = (
                f"The opportunity requires {target_years:.1f} years of work experience; "
                f"your profile currently shows {user_years:.1f} years."
            )

        return RequirementEvaluation(
            requirement_id=req.requirement_id,
            requirement_type="work_experience",
            requirement_description=req.description,
            status=status,
            priority=req.priority,
            user_value=user_years,
            required_value=target_years,
            comparison=f"{user_years:.1f} >= {target_years:.1f}",
            user_evidence=user_ev,
            opportunity_evidence=req.opportunity_evidence,
            explanation=msg,
            structured_explanation=(
                ExplanationBuilder.match(msg) if is_match else ExplanationBuilder.no_match(msg)
            ),
            confidence=EligibilityConfidence.HIGH,
        )


class ApplicationFeeEvaluator:
    """Evaluates application fees."""

    @classmethod
    def evaluate_fee(
        cls, user_facts: UnifiedUserFacts, req: OpportunityRequirementItem
    ) -> RequirementEvaluation:
        is_free = str(req.required_value).upper() == "NO_FEE"
        msg = (
            "This opportunity has no application fee ($0)."
            if is_free
            else "This opportunity requires an application fee."
        )
        return RequirementEvaluation(
            requirement_id=req.requirement_id,
            requirement_type="application_fee",
            requirement_description=req.description,
            status=RequirementStatus.MATCH
            if is_free
            else RequirementStatus.INFORMATIONAL
            if hasattr(RequirementStatus, "INFORMATIONAL")
            else RequirementStatus.MATCH,
            priority=RequirementPriority.INFORMATIONAL,
            user_value="Free" if is_free else "Fee Required",
            required_value=req.required_value,
            opportunity_evidence=req.opportunity_evidence,
            explanation=msg,
            confidence=EligibilityConfidence.HIGH,
        )
