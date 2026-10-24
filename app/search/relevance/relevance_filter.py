import re
from typing import ClassVar

from app.ai.query.intent_schemas import SearchIntent
from app.search.models.search_result import NormalizedSearchResult


class PreliminaryRelevanceFilter:
    """Evaluates search result relevance, flags candidate official sources, and eliminates noise."""

    OFFICIAL_TLDS: ClassVar[set[str]] = {
        ".edu",
        ".gov",
        ".org",
        ".ac.uk",
        ".edu.de",
        ".europa.eu",
    }

    OFFICIAL_DOMAINS: ClassVar[set[str]] = {
        "daad.de",
        "fulbrightprogram.org",
        "chevening.org",
        "erasmus-plus.ec.europa.eu",
        "campusfrance.org",
        "studyinaustria.at",
        "studyinsweden.se",
        "studyinholland.nl",
        "studyinitaly.esteri.it",
        "cern.ch",
        "mpg.de",
        "humboldt-foundation.de",
    }

    NOISE_PATTERNS: ClassVar[list[str]] = [
        r"\b(casino|gambling|poker|crypto\s*airdrop|adult|dating)\b",
        r"\b(buy\s+cheap|discount\s+code|coupon)\b",
    ]

    @classmethod
    def filter_and_score(
        cls,
        results: list[NormalizedSearchResult],
        intent: SearchIntent | None = None,
        min_relevance_threshold: float = 0.3,
    ) -> list[NormalizedSearchResult]:
        filtered: list[NormalizedSearchResult] = []

        # Keywords for relevance scoring
        target_tokens: set[str] = set()
        if intent:
            target_tokens.update(t.lower() for t in intent.opportunity_categories)
            target_tokens.update(c.lower() for c in intent.countries)
            target_tokens.update(r.lower() for r in intent.regions)
            target_tokens.update(d.lower() for d in intent.degree_levels)
            target_tokens.update(f.lower() for f in intent.fields)
            target_tokens.update(k.lower() for k in intent.keywords)

        for item in results:
            content = f"{item.title} {item.snippet}".lower()

            # 1. Noise Elimination
            is_noise = any(re.search(pat, content) for pat in cls.NOISE_PATTERNS)
            if is_noise:
                continue

            # 2. Official Source Detection
            domain = item.domain.lower()
            is_official = (
                any(domain.endswith(tld) for tld in cls.OFFICIAL_TLDS)
                or domain in cls.OFFICIAL_DOMAINS
                or any(
                    key in domain
                    for key in ("daad", "erasmus", "fulbright", "chevening", "europa.eu", "edu")
                )
            )
            item.is_official_source_candidate = is_official

            # 3. Preliminary Relevance Score (0.0 to 1.0)
            if target_tokens:
                overlap = sum(1 for token in target_tokens if token in content)
                score = min(1.0, 0.4 + (overlap * 0.15))
                if is_official:
                    score = min(1.0, score + 0.15)
            else:
                score = 0.8 if is_official else 0.6

            item.relevance_score = round(score, 2)

            if item.relevance_score >= min_relevance_threshold:
                filtered.append(item)

        # Sort with official candidates and higher preliminary score first
        filtered.sort(
            key=lambda x: (
                x.is_official_source_candidate,
                x.relevance_score or 0.0,
                -x.rank,
            ),
            reverse=True,
        )

        return filtered
