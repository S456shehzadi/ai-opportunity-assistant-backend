"""Pattern-based date extraction preserving context without semantic classification."""

import re
from datetime import datetime

from app.web.models.document import ExtractedDate

MONTHS_PATTERN = (
    r"(?:January|February|March|April|May|June|July|August|September|October|November|December|"
    r"Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)"
)

# Common international date patterns
DATE_REGEXES = [
    # 15 December 2026 or 15 Dec 2026
    re.compile(
        rf"\b(?P<day>\d{{1,2}})(?:st|nd|rd|th)?\s+(?P<month>{MONTHS_PATTERN})\s+(?P<year>\d{{4}})\b",
        re.IGNORECASE,
    ),
    # December 15, 2026 or Dec 15 2026
    re.compile(
        rf"\b(?P<month>{MONTHS_PATTERN})\s+(?P<day>\d{{1,2}})(?:st|nd|rd|th)?(?:,)?\s+(?P<year>\d{{4}})\b",
        re.IGNORECASE,
    ),
    # ISO: 2026-12-15
    re.compile(r"\b(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})\b"),
    # Slash/Dot: 15/12/2026 or 15.12.2026
    re.compile(r"\b(?P<first>\d{1,2})[/.](?P<second>\d{1,2})[/.](?P<year>\d{4})\b"),
    # Month YYYY: October 2026
    re.compile(rf"\b(?P<month>{MONTHS_PATTERN})\s+(?P<year>\d{{4}})\b", re.IGNORECASE),
]

MONTH_MAP = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}


class DateExtractor:
    """Extracts date strings and surrounding text context without semantic interpretation."""

    @classmethod
    def extract_dates(cls, text: str) -> list[ExtractedDate]:
        """Scans clean text for date patterns and records candidate phrases with context."""
        extracted: list[ExtractedDate] = []
        seen_spans: set[tuple[int, int]] = set()

        lines = text.split("\n")
        for line in lines:
            line_clean = line.strip()
            if not line_clean:
                continue

            for pattern in DATE_REGEXES:
                for match in pattern.finditer(line_clean):
                    span = match.span()
                    if any(s[0] <= span[0] and span[1] <= s[1] for s in seen_spans):
                        continue
                    seen_spans.add(span)

                    raw_text = match.group(0).strip()
                    parsed_iso = cls._try_parse_iso(match)

                    # Extract context: sentence or up to 100 characters around match
                    start = max(0, span[0] - 40)
                    end = min(len(line_clean), span[1] + 40)
                    context_snippet = line_clean[start:end].strip()

                    extracted.append(
                        ExtractedDate(
                            raw_text=raw_text,
                            context=context_snippet,
                            parsed_iso=parsed_iso,
                        )
                    )

        return extracted

    @classmethod
    def _try_parse_iso(cls, match: re.Match) -> str | None:
        """Attempts to normalize unambiguous matched components to YYYY-MM-DD."""
        groupdict = match.groupdict()
        try:
            year = int(groupdict["year"])
            if "month" in groupdict:
                m_str = groupdict["month"].lower()
                if m_str.isdigit():
                    month = int(m_str)
                else:
                    month = MONTH_MAP.get(m_str, 0)
                if month == 0:
                    return None
                day = int(groupdict.get("day", 1))
                return datetime(year, month, day).strftime("%Y-%m-%d")
            elif "first" in groupdict and "second" in groupdict:
                # Ambiguous day/month vs month/day: if first > 12, it is definitely day
                first = int(groupdict["first"])
                second = int(groupdict["second"])
                if first > 12 >= second:
                    return datetime(year, second, first).strftime("%Y-%m-%d")
                elif second > 12 >= first:
                    return datetime(year, first, second).strftime("%Y-%m-%d")
                else:
                    # Default international DD/MM/YYYY
                    return datetime(year, second, first).strftime("%Y-%m-%d")
        except Exception:
            return None
        return None
