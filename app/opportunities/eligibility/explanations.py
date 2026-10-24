"""Structured explanation generator for eligibility decisions.

Ensures every decision is explained concisely, transparently, and consistently
using standardized explanation types.
"""

from __future__ import annotations

from typing import Any

from app.opportunities.eligibility.schemas import ExplanationType, StructuredExplanation


class ExplanationBuilder:
    """Builds concise, human-readable, and machine-readable explanations."""

    @staticmethod
    def match(message: str, details: dict[str, Any] | None = None) -> StructuredExplanation:
        return StructuredExplanation(
            explanation_type=ExplanationType.MATCH_REASON,
            message=message,
            details=details or {},
        )

    @staticmethod
    def no_match(message: str, details: dict[str, Any] | None = None) -> StructuredExplanation:
        return StructuredExplanation(
            explanation_type=ExplanationType.NO_MATCH_REASON,
            message=message,
            details=details or {},
        )

    @staticmethod
    def unknown(message: str, details: dict[str, Any] | None = None) -> StructuredExplanation:
        return StructuredExplanation(
            explanation_type=ExplanationType.UNKNOWN_REASON,
            message=message,
            details=details or {},
        )

    @staticmethod
    def conditional(message: str, details: dict[str, Any] | None = None) -> StructuredExplanation:
        return StructuredExplanation(
            explanation_type=ExplanationType.CONDITIONAL_REASON,
            message=message,
            details=details or {},
        )

    @staticmethod
    def conflict(message: str, details: dict[str, Any] | None = None) -> StructuredExplanation:
        return StructuredExplanation(
            explanation_type=ExplanationType.CONFLICT_REASON,
            message=message,
            details=details or {},
        )

    @staticmethod
    def missing_info(message: str, field_name: str) -> StructuredExplanation:
        return StructuredExplanation(
            explanation_type=ExplanationType.MISSING_INFORMATION,
            message=message,
            details={"missing_field": field_name},
        )

    @staticmethod
    def source_note(message: str, source_url: str) -> StructuredExplanation:
        return StructuredExplanation(
            explanation_type=ExplanationType.SOURCE_NOTE,
            message=message,
            details={"source_url": source_url},
        )
