"""Privacy-preserving sanitizer filtering credentials, tokens, and PII from analytics."""

from __future__ import annotations

import re
from typing import Any


class PrivacyPreservingAnalytics:
    """Scrubs credentials, secret keys, passwords, and sensitive identifiers from event metadata."""

    SENSITIVE_KEY_PATTERNS = [
        re.compile(r"password", re.IGNORECASE),
        re.compile(r"secret", re.IGNORECASE),
        re.compile(r"token", re.IGNORECASE),
        re.compile(r"api[_-]?key", re.IGNORECASE),
        re.compile(r"authorization", re.IGNORECASE),
        re.compile(r"credential", re.IGNORECASE),
        re.compile(r"bearer", re.IGNORECASE),
        re.compile(r"credit[_-]?card", re.IGNORECASE),
        re.compile(r"ssn", re.IGNORECASE),
    ]

    EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b")
    BEARER_PATTERN = re.compile(r"Bearer\s+[A-Za-z0-9\-_.]+", re.IGNORECASE)

    @classmethod
    def sanitize_metadata(cls, data: Any) -> Any:
        """Recursively traverses dictionaries/lists and replaces sensitive tokens."""
        if isinstance(data, dict):
            clean_dict: dict[str, Any] = {}
            for k, v in data.items():
                if any(p.search(str(k)) for p in cls.SENSITIVE_KEY_PATTERNS):
                    clean_dict[k] = "[REDACTED_SECRET]"
                else:
                    clean_dict[k] = cls.sanitize_metadata(v)
            return clean_dict
        elif isinstance(data, list):
            return [cls.sanitize_metadata(item) for item in data]
        elif isinstance(data, str):
            text = cls.BEARER_PATTERN.sub("Bearer [REDACTED_TOKEN]", data)
            text = cls.EMAIL_PATTERN.sub("[REDACTED_EMAIL]", text)
            return text
        else:
            return data
