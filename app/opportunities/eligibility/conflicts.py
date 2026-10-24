"""Conflict detection and management for eligibility evaluation.

Identifies contradictory user profile records and unresolved opportunity claims,
preventing silent resolution of ambiguous facts.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ConflictItem(BaseModel):
    """Detailed audit representation of a contradiction."""

    entity_type: str = Field(description="'user_profile' or 'opportunity'")
    field_name: str
    competing_values: list[Any]
    sources_or_records: list[str]
    is_resolved: bool = False
    resolution: str | None = None
    reasoning: str


class EligibilityConflictDetector:
    """Detects discrepancies in user profile facts and opportunity sources."""

    @classmethod
    def detect_user_conflicts(cls, education_records: list[dict[str, Any]]) -> list[ConflictItem]:
        """Detects conflicting academic performance records for the same degree level."""
        conflicts: list[ConflictItem] = []
        degree_map: dict[str, list[dict[str, Any]]] = {}

        for rec in education_records:
            deg = rec.get("normalized_degree_level") or rec.get("degree_title") or "Unknown"
            if deg != "Unknown":
                degree_map.setdefault(deg, []).append(rec)

        for deg, records in degree_map.items():
            if len(records) > 1:
                # Check for conflicting GPAs on same institution/degree
                gpas = [
                    r.get("grade") or r.get("cgpa")
                    for r in records
                    if r.get("grade") is not None or r.get("cgpa") is not None
                ]
                if len(set(gpas)) > 1:
                    conflicts.append(
                        ConflictItem(
                            entity_type="user_profile",
                            field_name=f"cgpa_{deg}",
                            competing_values=gpas,
                            sources_or_records=[
                                r.get("institution", "Unknown Institution") for r in records
                            ],
                            is_resolved=False,
                            reasoning=(
                                f"Contradictory GPA records found for {deg}: "
                                f"{gpas}. Requires user verification."
                            ),
                        )
                    )
        return conflicts

    @classmethod
    def detect_opportunity_conflicts(cls, opportunity_conflicts: list[str]) -> list[ConflictItem]:
        """Parses opportunity conflict audit strings into structured ConflictItems."""
        items: list[ConflictItem] = []
        for c in opportunity_conflicts:
            items.append(
                ConflictItem(
                    entity_type="opportunity",
                    field_name="opportunity_source_claim",
                    competing_values=[],
                    sources_or_records=[],
                    is_resolved=False,
                    reasoning=c,
                )
            )
        return items
