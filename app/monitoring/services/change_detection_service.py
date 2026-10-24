"""Change detection service for identifying verified semantic differences."""

from __future__ import annotations

import re
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from app.monitoring.interfaces.monitor import IChangeDetector
from app.monitoring.models.change_event import (
    OpportunityChangeEvent,
    OpportunityChangeType,
)


class ChangeDetectionService(IChangeDetector):
    """Detects verified semantic differences between opportunity versions and text."""

    # Regex patterns for volatile/boilerplate text to ignore
    BOILERPLATE_PATTERNS = [
        re.compile(r"©\s*\d{4}[^\n.]*", re.IGNORECASE),
        re.compile(r"all rights reserved[^\n.]*", re.IGNORECASE),
        re.compile(r"cookie policy[^\n.]*", re.IGNORECASE),
        re.compile(r"privacy policy[^\n.]*", re.IGNORECASE),
        re.compile(r"terms of (use|service)[^\n.]*", re.IGNORECASE),
        re.compile(r"page loaded in\s*[\d.]+\s*(seconds|s|ms)", re.IGNORECASE),
        re.compile(
            r"(last modified|last updated|generated on)\s*[:\-]?\s*[\d\w\s,:]+",
            re.IGNORECASE,
        ),
        re.compile(r"google tag manager|gtag|analytics\.js", re.IGNORECASE),
    ]

    def clean_text_for_comparison(self, text: str) -> str:
        """Removes volatile boilerplate, cookie notices, and normalizes whitespace."""
        if not text:
            return ""

        cleaned = text
        for pattern in self.BOILERPLATE_PATTERNS:
            cleaned = pattern.sub(" ", cleaned)

        # Normalize multiple spaces, tabs, and newlines
        cleaned = re.sub(r"\s+", " ", cleaned).strip().lower()
        return cleaned

    def detect_content_changes(
        self,
        old_text: str,
        new_text: str,
    ) -> bool:
        """Determines if there is a substantive text change after stripping boilerplate."""
        norm_old = self.clean_text_for_comparison(old_text)
        norm_new = self.clean_text_for_comparison(new_text)
        return norm_old != norm_new

    def detect_structured_changes(
        self,
        old_data: dict[str, Any],
        new_data: dict[str, Any],
        opportunity_id: UUID,
    ) -> list[OpportunityChangeEvent]:
        """Compares structured fields and generates typed, prioritized change events."""
        events: list[OpportunityChangeEvent] = []
        now = datetime.now(UTC)

        # 1. Deadline changes
        old_dl = self._parse_date(old_data.get("deadline"))
        new_dl = self._parse_date(new_data.get("deadline"))

        if old_dl != new_dl and new_dl is not None:
            if old_dl is None:
                ch_type = OpportunityChangeType.DEADLINE_CHANGED
                priority = "HIGH"
                evidence = f"Deadline announced: {new_dl.isoformat()}"
            elif new_dl > old_dl:
                ch_type = OpportunityChangeType.DEADLINE_EXTENDED
                priority = "HIGH"
                evidence = f"Deadline extended from {old_dl.isoformat()} to {new_dl.isoformat()}"
            else:
                ch_type = OpportunityChangeType.DEADLINE_SHORTENED
                priority = "URGENT"
                evidence = (
                    f"Deadline moved earlier from {old_dl.isoformat()} to {new_dl.isoformat()}"
                )

            events.append(
                OpportunityChangeEvent(
                    opportunity_id=opportunity_id,
                    change_type=ch_type,
                    affected_field="deadline",
                    old_value=old_dl.isoformat() if old_dl else None,
                    new_value=new_dl.isoformat(),
                    evidence=evidence,
                    confidence=1.0,
                    source_trust="HIGH",
                    verified=True,
                    notification_priority=priority,
                    detected_at=now,
                    effective_date=new_dl,
                )
            )

        # 2. Status changes (Active, Closed, Upcoming, Paused)
        old_status = str(old_data.get("status", "")).lower()
        new_status = str(new_data.get("status", "")).lower()

        if old_status and new_status and old_status != new_status:
            priority = "NORMAL"
            if new_status in ("closed", "expired"):
                ch_type = OpportunityChangeType.PROGRAM_CLOSED
                priority = "URGENT"
                evidence = f"Program marked as closed/expired (was {old_status})"
            elif new_status == "active" and old_status in ("upcoming", "paused", "closed"):
                ch_type = OpportunityChangeType.PROGRAM_OPENED
                priority = "HIGH"
                evidence = f"Program opened for applications (was {old_status})"
            elif new_status == "paused":
                ch_type = OpportunityChangeType.PROGRAM_PAUSED
                priority = "NORMAL"
                evidence = "Applications temporarily paused"
            else:
                ch_type = OpportunityChangeType.APPLICATION_STATUS_CHANGED
                evidence = f"Status changed from {old_status} to {new_status}"

            events.append(
                OpportunityChangeEvent(
                    opportunity_id=opportunity_id,
                    change_type=ch_type,
                    affected_field="status",
                    old_value=old_status,
                    new_value=new_status,
                    evidence=evidence,
                    confidence=1.0,
                    source_trust="HIGH",
                    verified=True,
                    notification_priority=priority,
                    detected_at=now,
                )
            )

        # 3. Funding & Financial Support changes
        old_funding_amt = old_data.get("funding_amount")
        new_funding_amt = new_data.get("funding_amount")
        old_funding_type = old_data.get("funding_type")
        new_funding_type = new_data.get("funding_type")

        if (old_funding_amt != new_funding_amt and new_funding_amt) or (
            old_funding_type != new_funding_type and new_funding_type
        ):
            events.append(
                OpportunityChangeEvent(
                    opportunity_id=opportunity_id,
                    change_type=OpportunityChangeType.FUNDING_CHANGED,
                    affected_field="funding",
                    old_value={"type": old_funding_type, "amount": old_funding_amt},
                    new_value={"type": new_funding_type, "amount": new_funding_amt},
                    evidence=f"Funding updated to: {new_funding_type} ({new_funding_amt})",
                    confidence=0.95,
                    source_trust="HIGH",
                    verified=True,
                    notification_priority="HIGH",
                    detected_at=now,
                )
            )

        # 4. Application URL changes
        old_url = old_data.get("application_url")
        new_url = new_data.get("application_url")
        if old_url != new_url and new_url:
            events.append(
                OpportunityChangeEvent(
                    opportunity_id=opportunity_id,
                    change_type=OpportunityChangeType.APPLICATION_URL_CHANGED,
                    affected_field="application_url",
                    old_value=old_url,
                    new_value=new_url,
                    evidence=f"Application portal link updated to: {new_url}",
                    confidence=1.0,
                    source_trust="HIGH",
                    verified=True,
                    notification_priority="NORMAL",
                    detected_at=now,
                )
            )

        # 5. Eligibility & Test Requirements changes
        old_tests = sorted(
            old_data.get("english_tests", []) or old_data.get("test_requirements", [])
        )
        new_tests = sorted(
            new_data.get("english_tests", []) or new_data.get("test_requirements", [])
        )
        if old_tests != new_tests and new_tests:
            events.append(
                OpportunityChangeEvent(
                    opportunity_id=opportunity_id,
                    change_type=OpportunityChangeType.TEST_REQUIREMENT_CHANGED,
                    affected_field="test_requirements",
                    old_value=old_tests,
                    new_value=new_tests,
                    evidence=f"Standardized test requirements updated: {', '.join(new_tests)}",
                    confidence=0.95,
                    source_trust="HIGH",
                    verified=True,
                    notification_priority="HIGH",
                    detected_at=now,
                )
            )

        old_degree_levels = sorted(old_data.get("degree_levels", []))
        new_degree_levels = sorted(new_data.get("degree_levels", []))
        if old_degree_levels != new_degree_levels and new_degree_levels:
            events.append(
                OpportunityChangeEvent(
                    opportunity_id=opportunity_id,
                    change_type=OpportunityChangeType.DEGREE_REQUIREMENT_CHANGED,
                    affected_field="degree_levels",
                    old_value=old_degree_levels,
                    new_value=new_degree_levels,
                    evidence=f"Eligible degree levels updated: {', '.join(new_degree_levels)}",
                    confidence=0.95,
                    source_trust="HIGH",
                    verified=True,
                    notification_priority="HIGH",
                    detected_at=now,
                )
            )

        old_nationalities = sorted(old_data.get("eligible_nationalities", []))
        new_nationalities = sorted(new_data.get("eligible_nationalities", []))
        if old_nationalities != new_nationalities and new_nationalities:
            events.append(
                OpportunityChangeEvent(
                    opportunity_id=opportunity_id,
                    change_type=OpportunityChangeType.NATIONALITY_ELIGIBILITY_CHANGED,
                    affected_field="eligible_nationalities",
                    old_value=old_nationalities,
                    new_value=new_nationalities,
                    evidence=f"Eligible nationalities updated: {', '.join(new_nationalities)}",
                    confidence=0.95,
                    source_trust="HIGH",
                    verified=True,
                    notification_priority="HIGH",
                    detected_at=now,
                )
            )

        return events

    @staticmethod
    def _parse_date(val: Any) -> date | None:
        """Helper to parse a date object or string into a date."""
        if val is None:
            return None
        if isinstance(val, date):
            return val
        if isinstance(val, datetime):
            return val.date()
        if isinstance(val, str) and val.strip():
            try:
                return date.fromisoformat(val.strip()[:10])
            except Exception:
                return None
        return None
