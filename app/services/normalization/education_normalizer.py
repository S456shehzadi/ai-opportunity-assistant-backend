import re
from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class NormalizedEducation:
    raw_degree: str | None
    normalized_degree_level: (
        str  # High School, Associate, Bachelor's, Master's, Doctorate, Postdoc, Other
    )
    raw_field: str | None
    normalized_field: str | None  # Standardized concept e.g. "Computer Science"
    broad_discipline: str | None  # Broader area e.g. "Computing & Information Technology"


class EducationNormalizer:
    """Normalizes degrees, degree levels, and fields of study while preserving raw entries."""

    DEGREE_PATTERNS: ClassVar[list[tuple[str, str]]] = [
        (r"\b(ph\.?d|doctorate|doctoral|dphil|doctor\s+of\s+philosophy)\b", "Doctorate"),
        (r"\b(postdoc|postdoctoral)\b", "Postdoc"),
        (r"\b(m\.?s|m\.?sc|master'?s?|m\.?eng|m\.?phil|mba|postgraduate|graduate)\b", "Master's"),
        (r"\b(b\.?s|b\.?sc|bachelor'?s?|b\.?eng|bba|undergraduate)\b", "Bachelor's"),
        (r"\b(associate'?s?|diploma)\b", "Associate"),
        (r"\b(high\s*school|a-levels?|intermediate|secondary)\b", "High School"),
    ]

    FIELD_TAXONOMY: ClassVar[dict[str, tuple[str, str]]] = {
        # normalized_field, broad_discipline
        "computer science": ("Computer Science", "Computing & Information Technology"),
        "cs": ("Computer Science", "Computing & Information Technology"),
        "software engineering": ("Software Engineering", "Computing & Information Technology"),
        "se": ("Software Engineering", "Computing & Information Technology"),
        "artificial intelligence": (
            "Artificial Intelligence",
            "Computing & Information Technology",
        ),
        "ai": ("Artificial Intelligence", "Computing & Information Technology"),
        "machine learning": ("Machine Learning", "Computing & Information Technology"),
        "ml": ("Machine Learning", "Computing & Information Technology"),
        "data science": ("Data Science", "Computing & Information Technology"),
        "information technology": ("Information Technology", "Computing & Information Technology"),
        "it": ("Information Technology", "Computing & Information Technology"),
        "cybersecurity": ("Cybersecurity", "Computing & Information Technology"),
        "electrical engineering": ("Electrical Engineering", "Engineering & Physical Sciences"),
        "mechanical engineering": ("Mechanical Engineering", "Engineering & Physical Sciences"),
        "civil engineering": ("Civil Engineering", "Engineering & Physical Sciences"),
        "biomedical engineering": ("Biomedical Engineering", "Engineering & Physical Sciences"),
        "physics": ("Physics", "Natural Sciences"),
        "mathematics": ("Mathematics", "Natural Sciences"),
        "statistics": ("Statistics", "Natural Sciences"),
        "business administration": ("Business Administration", "Business & Economics"),
        "finance": ("Finance", "Business & Economics"),
        "economics": ("Economics", "Business & Economics"),
        "medicine": ("Medicine", "Health & Medical Sciences"),
        "public health": ("Public Health", "Health & Medical Sciences"),
        "biology": ("Biology", "Biological & Life Sciences"),
        "biotechnology": ("Biotechnology", "Biological & Life Sciences"),
        "law": ("Law", "Law & Legal Studies"),
    }

    @classmethod
    def normalize_degree_level(cls, text: str | None) -> str:
        """Determines the standard degree level (Bachelor's, Master's, Doctorate, etc.)."""
        if not text:
            return "Other"
        cleaned = text.strip().lower()

        # Check explicit patterns
        for pattern, level in cls.DEGREE_PATTERNS:
            if re.search(pattern, cleaned, re.IGNORECASE):
                return level

        return "Other"

    @classmethod
    def normalize_field_of_study(cls, field_text: str | None) -> tuple[str | None, str | None]:
        """Maps a field of study to (normalized_field, broad_discipline).

        Preserves extensible taxonomic lookup without forcing arbitrary overwrites.
        """
        if not field_text:
            return None, None
        cleaned = field_text.strip().lower()

        # Direct match in taxonomy
        if cleaned in cls.FIELD_TAXONOMY:
            return cls.FIELD_TAXONOMY[cleaned]

        # Substring / token matching
        for key, (norm_field, broad_disc) in cls.FIELD_TAXONOMY.items():
            if len(key) > 2 and (key in cleaned or cleaned in key):
                return norm_field, broad_disc

        # Capitalize raw string if unknown
        title_cased = " ".join(word.capitalize() for word in cleaned.split())
        return title_cased, "General & Interdisciplinary"

    @classmethod
    def normalize_education(
        cls, degree_text: str | None, field_text: str | None
    ) -> NormalizedEducation:
        """Produces a unified NormalizedEducation object."""
        level = cls.normalize_degree_level(degree_text)
        norm_field, broad = cls.normalize_field_of_study(field_text)

        return NormalizedEducation(
            raw_degree=degree_text,
            normalized_degree_level=level,
            raw_field=field_text,
            normalized_field=norm_field,
            broad_discipline=broad,
        )

    @staticmethod
    def normalize_gpa(
        grade: float | None,
        grading_scale: str | None = "4.0",
        percentage: float | None = None,
    ) -> float | None:
        """Normalizes various GPA scales or percentages to a standard 4.0 scale equivalent."""
        if grade is not None:
            scale_str = str(grading_scale or "4.0").strip()
            try:
                scale_val = float(scale_str)
            except ValueError:
                scale_val = 4.0

            if scale_val == 4.0:
                return round(min(max(grade, 0.0), 4.0), 2)
            elif scale_val == 5.0:
                # 5.0 scale -> 4.0 scale conversion
                return round(min(max((grade / 5.0) * 4.0, 0.0), 4.0), 2)
            elif scale_val == 10.0:
                # 10.0 Indian/European scale -> 4.0 scale conversion
                return round(min(max((grade / 10.0) * 4.0, 0.0), 4.0), 2)
            elif scale_val == 100.0:
                # Percentage scale
                return round(min(max((grade / 100.0) * 4.0, 0.0), 4.0), 2)

        if percentage is not None:
            # 85% -> ~3.7-3.8 equivalent
            return round(min(max((percentage / 100.0) * 4.0, 0.0), 4.0), 2)

        return None
