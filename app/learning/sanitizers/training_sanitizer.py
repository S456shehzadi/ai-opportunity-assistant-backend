"""Data minimization, secret scrubbing, and provenance verification."""

from __future__ import annotations

import re
from typing import Any

EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
PHONE_PATTERN = re.compile(r"(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}")
SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
CARD_PATTERN = re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")
API_KEY_PATTERN = re.compile(
    r"(?:bearer\s+[A-Za-z0-9\-_=]{20,}|(?:sk|api|token|secret)[_-][A-Za-z0-9\-_]{16,})",
    re.IGNORECASE,
)
ADDRESS_PATTERN = re.compile(
    r"\b\d{1,5}\s+[A-Za-z0-9\s,]{4,25}(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Terrace|Ter|Court|Ct|Way|Place|Pl)\b",
    re.IGNORECASE,
)

FORBIDDEN_LICENSES = {"ALL_RIGHTS_RESERVED", "PROPRIETARY", "NON_COMMERCIAL", "RESTRICTED"}


class TrainingDataSanitizer:
    """Sanitizes PII, sensitive secrets, and verifies provenance compliance."""

    def sanitize_text(self, text: str) -> tuple[str, bool]:
        """Redacts PII, credentials, and sensitive tokens from string."""
        if not text:
            return text, False

        redacted = False
        result = text

        if EMAIL_PATTERN.search(result):
            result = EMAIL_PATTERN.sub("[REDACTED_EMAIL]", result)
            redacted = True

        if PHONE_PATTERN.search(result):
            result = PHONE_PATTERN.sub("[REDACTED_PHONE]", result)
            redacted = True

        if SSN_PATTERN.search(result):
            result = SSN_PATTERN.sub("[REDACTED_SSN]", result)
            redacted = True

        if CARD_PATTERN.search(result):
            result = CARD_PATTERN.sub("[REDACTED_CARD]", result)
            redacted = True

        if API_KEY_PATTERN.search(result):
            result = API_KEY_PATTERN.sub("[REDACTED_KEY]", result)
            redacted = True

        if ADDRESS_PATTERN.search(result):
            result = ADDRESS_PATTERN.sub("[REDACTED_ADDRESS]", result)
            redacted = True

        return result, redacted

    def sanitize_value(self, value: Any) -> tuple[Any, bool]:
        """Recursively sanitizes values within nested dictionaries and lists."""
        if isinstance(value, str):
            return self.sanitize_text(value)
        if isinstance(value, dict):
            new_dict = {}
            any_redacted = False
            for k, v in value.items():
                sanitized_v, red = self.sanitize_value(v)
                new_dict[k] = sanitized_v
                if red:
                    any_redacted = True
            return new_dict, any_redacted
        if isinstance(value, list):
            new_list = []
            any_redacted = False
            for item in value:
                sanitized_item, red = self.sanitize_value(item)
                new_list.append(sanitized_item)
                if red:
                    any_redacted = True
            return new_list, any_redacted
        return value, False

    def sanitize_example(self, example: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        """Sanitizes an entire training or evaluation example."""
        sanitized_example, was_redacted = self.sanitize_value(example)
        if was_redacted and isinstance(sanitized_example, dict):
            meta = sanitized_example.setdefault("metadata", {})
            if isinstance(meta, dict):
                meta["sanitized_pii"] = True
        return sanitized_example, was_redacted

    def verify_provenance_and_consent(self, example: dict[str, Any]) -> bool:
        """Verifies legal provenance, license compliance, and user consent."""
        metadata = example.get("metadata", {})
        if not isinstance(metadata, dict):
            return False

        # If data originated from human interaction/conversation, consent is mandatory
        is_user_interaction = metadata.get("is_user_interaction", False)
        has_user_consent = metadata.get("user_consent", False)
        if is_user_interaction and not has_user_consent:
            return False

        # Check license compliance
        source_license = metadata.get("license", "").upper()
        if source_license in FORBIDDEN_LICENSES:
            return False

        # Provenance must be traceable (e.g., provenance_review_id, source_url, or source_id)
        has_provenance = bool(
            example.get("provenance_review_id")
            or metadata.get("source_url")
            or metadata.get("source_id")
            or metadata.get("benchmark_name")
        )
        return has_provenance
