"""Requirement adapter transforming various opportunity representations into atomic criteria."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field

from app.opportunities.eligibility.schemas import (
    OpportunityEvidenceRecord,
    RequirementPriority,
)
from app.opportunities.extraction.schemas import ExtractedOpportunity, FieldStatus


class OpportunityRequirementItem(BaseModel):
    """Normalized atomic criterion representing an eligibility hurdle."""

    requirement_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    requirement_type: str = Field(
        description="cgpa, percentage, degree_level, field_of_study, nationality, test, experience"
    )
    description: str
    priority: RequirementPriority = Field(default=RequirementPriority.MANDATORY)
    operator: str = Field(default=">=", description=">=, <=, ==, in, contains, between")
    required_value: Any
    unit: str | None = None
    waiver_allowed: bool = False
    waiver_conditions: str | None = None
    opportunity_evidence: OpportunityEvidenceRecord | None = None


class RequirementAdapter:
    """Transforms ExtractedOpportunity or DB models into OpportunityRequirementItem criteria."""

    @classmethod
    def adapt(cls, opportunity: ExtractedOpportunity | Any) -> list[OpportunityRequirementItem]:
        """Converts an opportunity into a list of atomic requirement items."""
        if isinstance(opportunity, ExtractedOpportunity):
            return cls._from_extracted_opportunity(opportunity)
        if isinstance(opportunity, dict):
            return cls._from_dict(opportunity)
        return cls._from_db_model(opportunity)

    @classmethod
    def _from_extracted_opportunity(
        cls, opp: ExtractedOpportunity
    ) -> list[OpportunityRequirementItem]:
        items: list[OpportunityRequirementItem] = []
        source_url = opp.official_source_url

        # 1. Degree Level Requirement
        if opp.degree_levels:
            ev_rec = None
            if opp.degree_requirement.evidence:
                ev_rec = OpportunityEvidenceRecord(
                    source_url=source_url,
                    field_name="degree_requirement",
                    evidence_text=opp.degree_requirement.evidence.evidence_text,
                    confidence=opp.degree_requirement.confidence,
                )
            items.append(
                OpportunityRequirementItem(
                    requirement_type="degree_level",
                    description=f"Must hold or be pursuing: {', '.join(opp.degree_levels)}",
                    priority=RequirementPriority.MANDATORY,
                    operator="in",
                    required_value=opp.degree_levels,
                    opportunity_evidence=ev_rec,
                )
            )

        # 2. Minimum CGPA Requirement
        if opp.minimum_cgpa.status == FieldStatus.FOUND and opp.minimum_cgpa.value is not None:
            ev_rec = None
            if opp.minimum_cgpa.evidence:
                ev_rec = OpportunityEvidenceRecord(
                    source_url=source_url,
                    field_name="minimum_cgpa",
                    evidence_text=opp.minimum_cgpa.evidence.evidence_text,
                    confidence=opp.minimum_cgpa.confidence,
                )
            items.append(
                OpportunityRequirementItem(
                    requirement_type="cgpa",
                    description=f"Minimum CGPA of {opp.minimum_cgpa.value} required",
                    priority=RequirementPriority.MANDATORY,
                    operator=">=",
                    required_value=float(opp.minimum_cgpa.value),
                    unit="4.0 scale",
                    opportunity_evidence=ev_rec,
                )
            )

        # 3. Minimum Percentage Requirement
        if (
            opp.minimum_percentage.status == FieldStatus.FOUND
            and opp.minimum_percentage.value is not None
        ):
            ev_rec = None
            if opp.minimum_percentage.evidence:
                ev_rec = OpportunityEvidenceRecord(
                    source_url=source_url,
                    field_name="minimum_percentage",
                    evidence_text=opp.minimum_percentage.evidence.evidence_text,
                    confidence=opp.minimum_percentage.confidence,
                )
            items.append(
                OpportunityRequirementItem(
                    requirement_type="percentage",
                    description=f"Minimum percentage of {opp.minimum_percentage.value}%",
                    priority=RequirementPriority.MANDATORY,
                    operator=">=",
                    required_value=float(opp.minimum_percentage.value),
                    unit="%",
                    opportunity_evidence=ev_rec,
                )
            )

        # 4. Fields of Study Requirement
        if opp.fields_of_study:
            items.append(
                OpportunityRequirementItem(
                    requirement_type="field_of_study",
                    description=f"Eligible fields: {', '.join(opp.fields_of_study)}",
                    priority=RequirementPriority.MANDATORY,
                    operator="in",
                    required_value=opp.fields_of_study,
                )
            )

        # 5. Nationality & Destination Requirements
        if (
            opp.eligible_nationalities.status == FieldStatus.FOUND
            and opp.eligible_nationalities.value
        ):
            items.append(
                OpportunityRequirementItem(
                    requirement_type="nationality",
                    description=f"Eligible: {', '.join(opp.eligible_nationalities.value)}",
                    priority=RequirementPriority.MANDATORY,
                    operator="in",
                    required_value=opp.eligible_nationalities.value,
                )
            )
        elif opp.eligible_countries:
            items.append(
                OpportunityRequirementItem(
                    requirement_type="nationality",
                    description=f"Eligible countries: {', '.join(opp.eligible_countries)}",
                    priority=RequirementPriority.MANDATORY,
                    operator="in",
                    required_value=opp.eligible_countries,
                )
            )

        # 6. Standardized Language Requirements (IELTS, TOEFL, PTE)
        for lang_req in opp.language_requirements:
            ev_rec = None
            if lang_req.evidence:
                ev_rec = OpportunityEvidenceRecord(
                    source_url=source_url,
                    field_name="language_requirement",
                    evidence_text=lang_req.evidence.evidence_text,
                    confidence=lang_req.evidence.confidence,
                )

            # If explicit test specified
            test_name = lang_req.test_name or "English"
            score = lang_req.minimum_score

            # Parse numeric cutoff if possible
            numeric_score = None
            if score:
                try:
                    numeric_score = float(score)
                except ValueError:
                    numeric_score = score

            items.append(
                OpportunityRequirementItem(
                    requirement_type=test_name.lower(),
                    description=(
                        f"{test_name} minimum score: {score}"
                        if score
                        else f"{test_name} proficiency required"
                    ),
                    priority=RequirementPriority.MANDATORY
                    if lang_req.is_required
                    else RequirementPriority.INFORMATIONAL,
                    operator=">=" if numeric_score is not None else "==",
                    required_value=numeric_score if numeric_score is not None else score,
                    waiver_allowed=lang_req.waiver_allowed,
                    waiver_conditions=lang_req.waiver_conditions,
                    opportunity_evidence=ev_rec,
                )
            )

        # 7. Application Fee Requirement
        if opp.application_fee.status == FieldStatus.FOUND:
            fee_required = opp.application_fee.value
            items.append(
                OpportunityRequirementItem(
                    requirement_type="application_fee",
                    description="Application fee required"
                    if fee_required
                    else "Free application ($0 fee)",
                    priority=RequirementPriority.INFORMATIONAL,
                    operator="==",
                    required_value="FEE_REQUIRED" if fee_required else "NO_FEE",
                )
            )

        # 8. Deadline Requirement
        if opp.deadline.status == FieldStatus.FOUND and opp.deadline.value:
            ev_rec = None
            if opp.deadline.evidence:
                ev_rec = OpportunityEvidenceRecord(
                    source_url=source_url,
                    field_name="deadline",
                    evidence_text=opp.deadline.evidence.evidence_text,
                    confidence=opp.deadline.confidence,
                )
            items.append(
                OpportunityRequirementItem(
                    requirement_type="deadline",
                    description=f"Application deadline: {opp.deadline.value}",
                    priority=RequirementPriority.IMPORTANT,
                    operator=">=",
                    required_value=opp.deadline.value,
                    opportunity_evidence=ev_rec,
                )
            )
        elif opp.is_rolling.status == FieldStatus.FOUND and opp.is_rolling.value:
            items.append(
                OpportunityRequirementItem(
                    requirement_type="deadline",
                    description="Rolling admissions deadline",
                    priority=RequirementPriority.IMPORTANT,
                    operator="==",
                    required_value="ROLLING",
                )
            )

        return items

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> list[OpportunityRequirementItem]:
        """Adapts plain dictionary representation of requirements."""
        items: list[OpportunityRequirementItem] = []

        if "degree_levels" in data and data["degree_levels"]:
            items.append(
                OpportunityRequirementItem(
                    requirement_type="degree_level",
                    description=f"Target degrees: {', '.join(data['degree_levels'])}",
                    priority=RequirementPriority.MANDATORY,
                    operator="in",
                    required_value=data["degree_levels"],
                )
            )

        if "minimum_cgpa" in data and data["minimum_cgpa"] is not None:
            items.append(
                OpportunityRequirementItem(
                    requirement_type="cgpa",
                    description=f"Minimum CGPA: {data['minimum_cgpa']}",
                    priority=RequirementPriority.MANDATORY,
                    operator=">=",
                    required_value=float(data["minimum_cgpa"]),
                )
            )

        if "minimum_percentage" in data and data["minimum_percentage"] is not None:
            items.append(
                OpportunityRequirementItem(
                    requirement_type="percentage",
                    description=f"Minimum percentage: {data['minimum_percentage']}%",
                    priority=RequirementPriority.MANDATORY,
                    operator=">=",
                    required_value=float(data["minimum_percentage"]),
                )
            )

        if "fields_of_study" in data and data["fields_of_study"]:
            items.append(
                OpportunityRequirementItem(
                    requirement_type="field_of_study",
                    description=f"Fields: {', '.join(data['fields_of_study'])}",
                    priority=RequirementPriority.MANDATORY,
                    operator="in",
                    required_value=data["fields_of_study"],
                )
            )

        if "eligible_nationalities" in data and data["eligible_nationalities"]:
            items.append(
                OpportunityRequirementItem(
                    requirement_type="nationality",
                    description=f"Eligible: {', '.join(data['eligible_nationalities'])}",
                    priority=RequirementPriority.MANDATORY,
                    operator="in",
                    required_value=data["eligible_nationalities"],
                )
            )
        elif "eligible_countries" in data and data["eligible_countries"]:
            items.append(
                OpportunityRequirementItem(
                    requirement_type="nationality",
                    description=f"Eligible countries: {', '.join(data['eligible_countries'])}",
                    priority=RequirementPriority.MANDATORY,
                    operator="in",
                    required_value=data["eligible_countries"],
                )
            )

        # Raw requirements list
        if "requirements" in data and isinstance(data["requirements"], list):
            for r in data["requirements"]:
                if isinstance(r, dict):
                    items.append(
                        OpportunityRequirementItem(
                            requirement_type=r.get("requirement_type", "general"),
                            description=r.get("description")
                            or r.get("requirement_description", ""),
                            priority=RequirementPriority(r.get("priority", "MANDATORY")),
                            operator=r.get("operator", ">="),
                            required_value=r.get("required_value") or r.get("value"),
                            waiver_allowed=r.get("waiver_allowed", False),
                            waiver_conditions=r.get("waiver_conditions"),
                        )
                    )

        # Language tests in dict
        if "ielts" in data and data["ielts"] is not None:
            items.append(
                OpportunityRequirementItem(
                    requirement_type="ielts",
                    description=f"IELTS minimum: {data['ielts']}",
                    priority=RequirementPriority.MANDATORY,
                    operator=">=",
                    required_value=float(data["ielts"]),
                    waiver_allowed=data.get("ielts_waiver_allowed", False),
                    waiver_conditions=data.get("ielts_waiver_conditions"),
                )
            )

        if "deadline" in data and data["deadline"]:
            items.append(
                OpportunityRequirementItem(
                    requirement_type="deadline",
                    description=f"Deadline: {data['deadline']}",
                    priority=RequirementPriority.IMPORTANT,
                    operator=">=",
                    required_value=str(data["deadline"]),
                )
            )

        return items

    @classmethod
    def _from_db_model(cls, db_opp: Any) -> list[OpportunityRequirementItem]:
        """Adapts SQLAlchemy Opportunity model and its OpportunityRequirement child rows."""
        items: list[OpportunityRequirementItem] = []

        # Convert atomic requirements relationship safely
        reqs: list[Any] = []
        try:
            from sqlalchemy import inspect as sa_inspect
            insp = sa_inspect(db_opp, raise_errors=False)
            if insp is not None and "requirements" not in insp.unloaded:
                reqs = list(db_opp.requirements or [])
        except Exception:
            pass

        if not reqs:
            try:
                raw = getattr(db_opp, "requirements", [])
                if not callable(raw):
                    reqs = list(raw)
            except Exception:
                reqs = []

        for req in reqs:
            items.append(
                OpportunityRequirementItem(
                    requirement_id=str(req.id),
                    requirement_type=req.requirement_type,
                    description=f"{req.requirement_type} {req.operator} {req.value}",
                    priority=RequirementPriority.MANDATORY
                    if req.is_mandatory
                    else RequirementPriority.INFORMATIONAL,
                    operator=str(req.operator),
                    required_value=req.value,
                    unit=req.unit,
                )
            )

        # Fallback to column attributes on Opportunity if requirements table has no rows
        if not items:
            if getattr(db_opp, "degree_levels", None):
                items.append(
                    OpportunityRequirementItem(
                        requirement_type="degree_level",
                        description=f"Target degrees: {', '.join(db_opp.degree_levels)}",
                        priority=RequirementPriority.MANDATORY,
                        operator="in",
                        required_value=db_opp.degree_levels,
                    )
                )
            if getattr(
                db_opp, "eligible_nationalities", None
            ) and db_opp.eligible_nationalities != ["Global"]:
                items.append(
                    OpportunityRequirementItem(
                        requirement_type="nationality",
                        description=f"Eligible: {', '.join(db_opp.eligible_nationalities)}",
                        priority=RequirementPriority.MANDATORY,
                        operator="in",
                        required_value=db_opp.eligible_nationalities,
                    )
                )
            if getattr(db_opp, "deadline", None):
                items.append(
                    OpportunityRequirementItem(
                        requirement_type="deadline",
                        description=f"Deadline: {db_opp.deadline}",
                        priority=RequirementPriority.IMPORTANT,
                        operator=">=",
                        required_value=str(db_opp.deadline),
                    )
                )

        return items
