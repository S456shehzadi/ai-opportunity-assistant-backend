"""Evidence linking and provenance tracking for eligibility decisions."""

from __future__ import annotations

from typing import Any

from app.opportunities.eligibility.schemas import (
    OpportunityEvidenceRecord,
    RequirementEvaluation,
    UserEvidenceRecord,
)


class EligibilityEvidenceLinker:
    """Links user profile facts and opportunity citations to eligibility evaluations."""

    @staticmethod
    def create_user_evidence(
        source_section: str,
        field_name: str,
        value: Any,
        record_id: str | None = None,
        context: str | None = None,
        verified: bool = False,
    ) -> UserEvidenceRecord:
        """Constructs an auditable UserEvidenceRecord."""
        return UserEvidenceRecord(
            source_section=source_section,
            record_id=record_id,
            field_name=field_name,
            value=value,
            verified=verified,
            context=context,
        )

    @staticmethod
    def create_opportunity_evidence(
        source_url: str,
        field_name: str,
        evidence_text: str,
        confidence: float = 1.0,
    ) -> OpportunityEvidenceRecord:
        """Constructs an auditable OpportunityEvidenceRecord."""
        return OpportunityEvidenceRecord(
            source_url=source_url,
            field_name=field_name,
            evidence_text=evidence_text,
            confidence=confidence,
        )

    @classmethod
    def compile_evidence_audit_trail(
        cls, evaluations: list[RequirementEvaluation]
    ) -> list[dict[str, Any]]:
        """Compiles a complete audit log of all evidence citations used in an evaluation."""
        trail: list[dict[str, Any]] = []
        for req in evaluations:
            entry: dict[str, Any] = {
                "requirement_id": req.requirement_id,
                "requirement_type": req.requirement_type,
                "status": req.status.value,
                "user_evidence": req.user_evidence.model_dump() if req.user_evidence else None,
                "opportunity_evidence": (
                    req.opportunity_evidence.model_dump() if req.opportunity_evidence else None
                ),
            }
            trail.append(entry)
        return trail
