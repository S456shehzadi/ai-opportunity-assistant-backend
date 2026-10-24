"""Evidence tracking, source provenance, and citation verification models."""

import re
import uuid
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class EvidenceType(StrEnum):
    """Categorization of source evidence origin."""

    DIRECT_TEXT = "DIRECT_TEXT"
    TABLE = "TABLE"
    LIST = "LIST"
    METADATA = "METADATA"
    STRUCTURED_DATA = "STRUCTURED_DATA"
    URL = "URL"
    INFERRED = "INFERRED"


class Evidence(BaseModel):
    """Verifiable source evidence citation grounding an extracted fact."""

    source_document_id: uuid.UUID | None = Field(
        default=None, description="Identifier of the origin WebDocument"
    )
    source_url: str = Field(description="Exact URL of the source page")
    field_name: str = Field(description="Opportunity attribute grounded by this evidence")
    evidence_text: str = Field(description="Literal text quote or structural citation")
    evidence_type: EvidenceType = Field(
        default=EvidenceType.DIRECT_TEXT, description="Origin type of the citation"
    )
    location: str | None = Field(
        default=None, description="DOM section, table caption, or heading path"
    )
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Verification certainty of the evidence"
    )
    extracted_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when evidence was captured",
    )


class EvidenceValidator:
    """Verifies evidence integrity and guards against fabricated citations."""

    @classmethod
    def verify_evidence(
        cls,
        evidence: Evidence | None,
        source_content: str | None = None,
    ) -> bool:
        """Verifies that evidence exists, is non-empty, and appears in the source text
        if provided.
        """
        if evidence is None:
            return False

        if not evidence.evidence_text or not evidence.evidence_text.strip():
            return False

        if not evidence.source_url or not evidence.source_url.strip():
            return False

        # If source content is supplied, verify quotation existence
        if source_content:
            quote = evidence.evidence_text.strip().lower()
            normalized_source = " ".join(source_content.lower().split())
            normalized_quote = " ".join(quote.split())

            # Check exact substring
            if normalized_quote in normalized_source:
                return True

            # If evidence contains numbers, all numbers must be present in source text
            numbers_in_quote = re.findall(r"\d+", normalized_quote)
            if numbers_in_quote:
                for num in numbers_in_quote:
                    if num not in normalized_source:
                        return False

            # If evidence is a summary or table row, check key token presence
            tokens = [t for t in re.findall(r"\w+", normalized_quote) if len(t) >= 2]
            if tokens:
                matches = sum(1 for t in tokens if t in normalized_source)
                ratio = matches / len(tokens)
                return ratio >= 0.85

            return False

        return True

    verify_evidence_in_text = verify_evidence
