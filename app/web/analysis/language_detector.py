"""Lightweight language detection from markup and text features."""

import re

COMMON_STOPWORDS: dict[str, set[str]] = {
    "en": {"the", "and", "for", "with", "university", "scholarship", "students", "degree"},
    "de": {"der", "die", "das", "und", "für", "mit", "stipendium", "studierende", "universität"},
    "fr": {"le", "la", "les", "et", "pour", "bourse", "étudiants", "université"},
    "es": {"el", "la", "los", "las", "y", "para", "beca", "estudiantes", "universidad"},
}

CYRILLIC_RE = re.compile(r"[\u0400-\u04FF]")
ARABIC_RE = re.compile(r"[\u0600-\u06FF]")
CJK_RE = re.compile(r"[\u4E00-\u9FFF\u3040-\u30FF]")


class LanguageDetector:
    """Detects primary language of extracted web documents."""

    @classmethod
    def detect(cls, clean_text: str, html_lang: str | None = None) -> str:
        """Determines primary language code (e.g. 'en', 'de', 'fr', 'es')."""
        text = clean_text
        # 1. Trust valid HTML lang attribute if available
        if html_lang:
            clean_lang = html_lang.strip().lower()
            prefix = clean_lang.split("-")[0].split("_")[0]
            if len(prefix) == 2:
                return prefix

        # 2. Non-Latin script checks
        if CYRILLIC_RE.search(text[:1000]):
            return "ru"
        if ARABIC_RE.search(text[:1000]):
            return "ar"
        if CJK_RE.search(text[:1000]):
            return "zh"

        # 3. Stopword frequency scoring
        words = set(re.findall(r"\b\w+\b", text.lower()[:3000]))
        best_lang = "en"
        best_matches = 0

        for lang_code, stopwords in COMMON_STOPWORDS.items():
            matches = len(words & stopwords)
            if matches > best_matches:
                best_matches = matches
                best_lang = lang_code

        return best_lang
