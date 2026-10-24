"""Prompt injection defense and tool permission boundaries."""

from __future__ import annotations

import re
from typing import ClassVar

from app.ai.conversation.schemas import ToolPermission


class PromptInjectionDefense:
    """Detects and neutralizes prompt injection attempts within queries and web content."""

    INJECTION_PATTERNS: ClassVar[list[re.Pattern]] = [
        re.compile(r"\bignore\s+(?:previous|all|above)\s+instructions\b", re.I),
        re.compile(r"\b(?:system\s+override|system\s+prompt|reveal\s+instructions)\b", re.I),
        re.compile(r"\b(?:reveal|show|print)\s+(?:api\s*keys?|passwords?|credentials?)\b", re.I),
        re.compile(r"\bbypass\s+(?:all\s+)?(?:safety|guardrails|filters|rules)\b", re.I),
        re.compile(r"\bact\s+as\s+(?:dan|root|unrestricted|jailbroken|godmode)\b", re.I),
        re.compile(r"\b(?:execute|eval)\s+(?:code|script|command|bash|python)\b", re.I),
        re.compile(r"<\s*script\b", re.I),
    ]

    @classmethod
    def is_potential_injection(cls, text: str) -> bool:
        """Returns True if text contains prompt injection or system override patterns."""
        if not text:
            return False
        for pattern in cls.INJECTION_PATTERNS:
            if pattern.search(text):
                return True
        return False

    @classmethod
    def sanitize_web_content(cls, content: str) -> str:
        """Wraps untrusted web content in strict protective fences, disarming directives."""
        if not content:
            return ""

        # Remove attempts to fake boundary tags
        sanitized = content.replace("</untrusted_source_content>", "[ESCAPED_TAG]")
        sanitized = sanitized.replace("<untrusted_source_content>", "[ESCAPED_TAG]")

        return f"<untrusted_source_content>\n{sanitized.strip()}\n</untrusted_source_content>"


class ToolPermissionGuardrails:
    """Restricts assistant execution strictly to authorized tools."""

    ALLOWED_PERMISSIONS: ClassVar[set[ToolPermission]] = {
        ToolPermission.SEARCH,
        ToolPermission.RETRIEVE,
        ToolPermission.EXTRACT,
        ToolPermission.CHECK_ELIGIBILITY,
        ToolPermission.RANK,
        ToolPermission.READ_PROFILE,
        ToolPermission.READ_SAVED,
        ToolPermission.COMPARE,
    }

    @classmethod
    def validate_tool_permission(cls, requested_permission: ToolPermission) -> None:
        """Validates that a tool execution is within the authorized security scope."""
        if requested_permission not in cls.ALLOWED_PERMISSIONS:
            raise PermissionError(
                f"Unauthorized tool execution: {requested_permission} is not permitted."
            )
