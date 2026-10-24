from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Any, ClassVar


class TestStatus(StrEnum):
    VALID = "valid"
    EXPIRED = "expired"
    TAKEN = "taken"  # Taken, but exact validity cannot be verified without date
    NOT_TAKEN = "not_taken"
    UNKNOWN = "unknown"  # Critical distinction: missing is NOT "no"


@dataclass(frozen=True)
class NormalizedTestResult:
    canonical_test_name: str
    test_type: str  # Language, Aptitude, Academic
    score: str | None
    sub_scores: dict[str, Any]
    test_date: date | None
    expiry_date: date | None
    status: TestStatus
    raw_test_name: str


class TestNormalizer:
    """Normalizes standardized tests and distinguishes Valid, Expired, Not Taken, and Unknown."""

    KNOWN_TESTS: ClassVar[dict[str, tuple[str, str, int]]] = {
        # name_lower -> (canonical_name, test_type, validity_years)
        "ielts": ("IELTS", "Language", 2),
        "ielts academic": ("IELTS", "Language", 2),
        "ielts general": ("IELTS", "Language", 2),
        "toefl": ("TOEFL", "Language", 2),
        "toefl ibt": ("TOEFL", "Language", 2),
        "pte": ("PTE", "Language", 2),
        "pte academic": ("PTE", "Language", 2),
        "duolingo": ("Duolingo English Test", "Language", 2),
        "det": ("Duolingo English Test", "Language", 2),
        "gre": ("GRE", "Aptitude", 5),
        "gre general": ("GRE", "Aptitude", 5),
        "gmat": ("GMAT", "Aptitude", 5),
        "gat": ("GAT", "Aptitude", 2),
        "sat": ("SAT", "Aptitude", 5),
    }

    @classmethod
    def normalize_test(
        cls,
        test_name: str,
        score: str | None = None,
        score_details: dict[str, Any] | None = None,
        test_date: date | None = None,
        expiry_date: date | None = None,
        as_of_date: date | None = None,
    ) -> NormalizedTestResult:
        """Determines the canonical test name and validity status."""
        cleaned_name = test_name.strip().lower()
        sub_scores = score_details or {}
        today = as_of_date or datetime.now(UTC).date()

        info = cls.KNOWN_TESTS.get(cleaned_name)
        if info:
            canonical_name, test_type, validity_years = info
        else:
            canonical_name = test_name.strip()
            test_type = "Standardized Test"
            validity_years = 2

        # Compute or verify expiry date
        calc_expiry = expiry_date
        if calc_expiry is None and test_date is not None:
            try:
                calc_expiry = date(test_date.year + validity_years, test_date.month, test_date.day)
            except ValueError:
                # Handle leap year Feb 29
                calc_expiry = date(
                    test_date.year + validity_years, test_date.month, test_date.day - 1
                )

        # Status determination
        if not score:
            status = TestStatus.NOT_TAKEN
        elif calc_expiry is not None:
            if calc_expiry >= today:
                status = TestStatus.VALID
            else:
                status = TestStatus.EXPIRED
        else:
            status = TestStatus.TAKEN

        return NormalizedTestResult(
            canonical_test_name=canonical_name,
            test_type=test_type,
            score=score,
            sub_scores=sub_scores,
            test_date=test_date,
            expiry_date=calc_expiry,
            status=status,
            raw_test_name=test_name,
        )

    @classmethod
    def get_test_status_for_missing(cls, test_name: str) -> NormalizedTestResult:
        """Explicitly represents an unprovided/missing test as UNKNOWN (Never 'No')."""
        info = cls.KNOWN_TESTS.get(test_name.strip().lower())
        canonical_name = info[0] if info else test_name.strip()
        test_type = info[1] if info else "Language"

        return NormalizedTestResult(
            canonical_test_name=canonical_name,
            test_type=test_type,
            score=None,
            sub_scores={},
            test_date=None,
            expiry_date=None,
            status=TestStatus.UNKNOWN,
            raw_test_name=test_name,
        )
