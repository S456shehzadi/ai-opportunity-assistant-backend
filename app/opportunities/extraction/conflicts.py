"""Conflict detection and resolution for multi-source opportunity extraction.

Identifies contradictory deadlines, funding amounts, or requirements between
different web pages or aggregators and resolves them in favor of verified,
official sources while maintaining full audit logs of conflicting claims.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.opportunities.extraction.schemas import ExtractedOpportunity, SourceTrustType


@dataclass
class ConflictRecord:
    """Detailed audit record of a field conflict between sources."""

    field_name: str
    official_value: Any
    official_source_url: str
    secondary_value: Any
    secondary_source_url: str
    resolution: str
    reasoning: str


class ConflictDetector:
    """Analyzes multiple extractions for an opportunity and identifies conflicting facts."""

    @classmethod
    def detect_and_resolve_conflicts(
        cls,
        primary: ExtractedOpportunity,
        secondary: ExtractedOpportunity,
    ) -> list[ConflictRecord]:
        """Compares two extracted records, resolving conflicts in favor of higher trust."""
        conflicts: list[ConflictRecord] = []

        # Determine which record has higher source trust
        primary_is_more_trusted = (
            primary.source_trust_score >= secondary.source_trust_score
            or primary.source_type == SourceTrustType.OFFICIAL
        )

        trusted = primary if primary_is_more_trusted else secondary
        other = secondary if primary_is_more_trusted else primary

        # Check deadline conflict
        if (
            trusted.deadline.value
            and other.deadline.value
            and trusted.deadline.value != other.deadline.value
        ):
            conflict = ConflictRecord(
                field_name="application_deadline",
                official_value=trusted.deadline.value,
                official_source_url=trusted.official_source_url,
                secondary_value=other.deadline.value,
                secondary_source_url=other.official_source_url,
                resolution=str(trusted.deadline.value),
                reasoning=(
                    f"Resolved deadline conflict: Selected {trusted.deadline.value} "
                    f"from higher trust source ({trusted.source_type}) over "
                    f"{other.deadline.value} from {other.source_type}."
                ),
            )
            conflicts.append(conflict)

        # Check funding amount conflict
        if (
            trusted.funding_amount
            and other.funding_amount
            and (
                trusted.funding_amount.amount != other.funding_amount.amount
                or trusted.funding_amount.currency != other.funding_amount.currency
            )
        ):
            conflict = ConflictRecord(
                field_name="funding_amount",
                official_value=trusted.funding_amount,
                official_source_url=trusted.official_source_url,
                secondary_value=other.funding_amount,
                secondary_source_url=other.official_source_url,
                resolution=str(trusted.funding_amount),
                reasoning=(f"Resolved funding conflict: Prioritized {trusted.source_type} source."),
            )
            conflicts.append(conflict)

        # Check application fee conflict
        if (
            trusted.application_fee.value is not None
            and other.application_fee.value is not None
            and trusted.application_fee.value != other.application_fee.value
        ):
            conflict = ConflictRecord(
                field_name="application_fee",
                official_value=trusted.application_fee.value,
                official_source_url=trusted.official_source_url,
                secondary_value=other.application_fee.value,
                secondary_source_url=other.official_source_url,
                resolution=str(trusted.application_fee.value),
                reasoning=(f"Resolved fee conflict: Prioritized {trusted.source_type} source."),
            )
            conflicts.append(conflict)

        return conflicts
