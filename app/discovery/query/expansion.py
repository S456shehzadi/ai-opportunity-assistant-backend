"""Controlled domain-aware query expansion service supporting multilingual concepts."""

from __future__ import annotations

import re

# Domain concept synonym dictionary
DOMAIN_SYNONYMS: dict[str, list[str]] = {
    "master's": ["masters", "msc", "graduate degree", "postgraduate program"],
    "masters": ["master's", "msc", "graduate degree", "postgraduate"],
    "msc": ["master's", "graduate program", "postgraduate"],
    "phd": ["doctoral", "doctorate", "doctoral fellowship"],
    "doctoral": ["phd", "doctorate"],
    "scholarship": ["funding", "financial aid", "grant", "fellowship"],
    "scholarships": ["funding", "financial aid", "grants", "fellowships"],
    "funding": ["scholarship", "financial aid", "grant"],
    "internship": ["placement", "traineeship", "industrial training"],
    "internships": ["placements", "traineeships"],
    "ai": ["artificial intelligence", "machine learning"],
    "artificial intelligence": ["ai", "machine learning", "data science"],
    "cs": ["computer science", "software engineering"],
    "computer science": ["software engineering", "computing", "informatics"],
    "fellowship": ["scholarship", "research grant"],
    "tuition-free": ["fully funded", "full tuition scholarship"],
}

# Multilingual concept bridges to ensure cross-language discovery
MULTILINGUAL_CONCEPTS: dict[str, list[str]] = {
    # Arabic
    "منح": ["scholarships", "funding"],
    "منحة": ["scholarship", "funding"],
    "ماجستير": ["master's", "graduate degree"],
    "دكتوراه": ["phd", "doctoral"],
    "تدريب": ["internship", "traineeship"],
    "ممولة": ["funded", "scholarship"],
    "حاسوب": ["computer science", "computing"],
    "ذكاء اصطناعي": ["artificial intelligence", "ai"],
    # Urdu
    "اسکالرشپ": ["scholarship", "funding"],
    "وظیفہ": ["scholarship", "grant"],
    "ماسٹرز": ["master's", "graduate degree"],
    "پی ایچ ڈی": ["phd", "doctoral"],
    "انٹرنشپ": ["internship", "placement"],
    # Turkish
    "burs": ["scholarship", "funding"],
    "yüksek lisans": ["master's", "graduate degree"],
    "doktora": ["phd", "doctoral"],
    "staj": ["internship", "traineeship"],
    # French
    "bourse": ["scholarship", "funding"],
    "master": ["master's", "graduate degree"],
    "doctorat": ["phd", "doctoral"],
    "stage": ["internship", "placement"],
    # Spanish
    "beca": ["scholarship", "grant"],
    "maestría": ["master's", "graduate degree"],
    "pasantía": ["internship", "placement"],
}


class QueryExpansionService:
    """Generates controlled semantic variants preserving user intent without
    inventing constraints.
    """

    def __init__(self, max_expansions: int = 4) -> None:
        self.max_expansions = max_expansions

    def expand(self, query: str) -> list[str]:
        """Returns ordered list of query variants starting with the original query."""
        cleaned_query = query.strip()
        if not cleaned_query:
            return []

        expansions: list[str] = [cleaned_query]

        # 1. Check multilingual concept bridges
        for token, english_equivalents in MULTILINGUAL_CONCEPTS.items():
            if token in cleaned_query.lower():
                for eq in english_equivalents:
                    new_q = re.sub(re.escape(token), eq, cleaned_query, flags=re.IGNORECASE).strip()
                    if new_q and new_q not in expansions:
                        expansions.append(new_q)
                        if len(expansions) >= self.max_expansions + 1:
                            return expansions[: self.max_expansions + 1]

        # 2. Check domain synonyms
        for key, synonyms in DOMAIN_SYNONYMS.items():
            pattern = rf"\b{re.escape(key)}\b"
            if re.search(pattern, cleaned_query, flags=re.IGNORECASE):
                for syn in synonyms:
                    variant = re.sub(
                        pattern, syn, cleaned_query, flags=re.IGNORECASE, count=1
                    ).strip()
                    if variant and variant not in expansions:
                        expansions.append(variant)
                        if len(expansions) >= self.max_expansions + 1:
                            break
            if len(expansions) >= self.max_expansions + 1:
                break

        return expansions[: self.max_expansions + 1]
