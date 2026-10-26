import re
from dataclasses import dataclass
from typing import ClassVar

from app.models.profile import EducationLevel


@dataclass(frozen=True)
class NormalizedEducation:
    raw_degree: str | None
    normalized_degree_level: str
    raw_field: str | None
    normalized_field: str | None
    broad_discipline: str | None
    country: str | None = None
    stream: str | None = None
    confidence: float = 1.0


class EducationNormalizer:
    """Normalizes degrees, degree levels, countries, and fields of study worldwide.

    Supports all 13 canonical global education categories from Primary School through
    Postdoctoral research, vocational training, and informal education.
    """

    LEVEL_PRIMARY = EducationLevel.PRIMARY.value
    LEVEL_MIDDLE_SCHOOL = EducationLevel.MIDDLE_SCHOOL.value
    LEVEL_MATRICULATION = EducationLevel.MATRICULATION.value
    LEVEL_INTERMEDIATE = EducationLevel.INTERMEDIATE.value
    LEVEL_A_LEVELS_IB = EducationLevel.A_LEVELS_IB.value
    LEVEL_VOCATIONAL = EducationLevel.VOCATIONAL.value
    LEVEL_ASSOCIATE = EducationLevel.ASSOCIATE.value
    LEVEL_BACHELORS = EducationLevel.BACHELORS.value
    LEVEL_MASTERS = EducationLevel.MASTERS.value
    LEVEL_DOCTORATE = EducationLevel.DOCTORATE.value
    LEVEL_POSTDOCTORAL = EducationLevel.POSTDOCTORAL.value
    LEVEL_PROFESSIONAL = EducationLevel.PROFESSIONAL.value
    LEVEL_NO_FORMAL = EducationLevel.NO_FORMAL.value

    # Ordered patterns evaluated from most specific to least specific
    DEGREE_PATTERNS: ClassVar[list[tuple[str, str]]] = [
        # Postdoc & Research
        (r"\b(postdoc|postdoctoral(\s+research)?)\b", LEVEL_POSTDOCTORAL),
        # PhD & Doctorate
        (r"\b(ph\.?d|doctorate|doctoral|dphil|doctor\s+of\s+philosophy)\b", LEVEL_DOCTORATE),
        # Master's / Postgraduate
        (
            r"\b(m\.?s|m\.?sc|master'?s?|m\.?eng|m\.?phil|mba|postgraduate|m\.?ed|mfa|llm)\b",
            LEVEL_MASTERS,
        ),
        # Bachelor's / Undergraduate
        (
            r"\b(b\.?s|b\.?sc|bachelor'?s?|b\.?eng|bba|undergraduate|llb|mbbs|bds|b\.?ed|bfa)\b",
            LEVEL_BACHELORS,
        ),
        # Professional Qualifications
        (
            r"\b(acca|chartered\s+accountant|ca\s+final|cpa|cfa|bar\s+at\s+law|pmp|professional\s+qualification)\b",
            LEVEL_PROFESSIONAL,
        ),
        # Associate Degree & Higher Diplomas
        (r"\b(associate'?s?(\s+degree)?|dae|diploma\s+of\s+associate|hnd|hnc)\b", LEVEL_ASSOCIATE),
        # Vocational & Technical Training
        (
            r"\b(vocational|trade|apprenticeship|polytechnic|certificate\s+course|nvq|iti|trade\s+certificate)\b",
            LEVEL_VOCATIONAL,
        ),
        # Intermediate / Higher Secondary (Distinct Level)
        (
            r"\b(intermediate|hssc|higher\s+secondary|f\.?sc|f\.?a|ics|i\.?com|12th\s+grade|grade\s+12|class\s+12)\b",
            LEVEL_INTERMEDIATE,
        ),
        # A-Levels / IB Diploma / Equivalent (Distinct Level)
        (
            r"\b(a-?levels?|advanced\s+levels?|as-?levels?|ib\s+diploma|ibdp|international\s+baccalaureate|abitur)\b",
            LEVEL_A_LEVELS_IB,
        ),
        # Matriculation / Secondary School (Distinct Level)
        (
            r"\b(matric(ulation)?|ssc|secondary\s+school(\s+certificate)?|gcse|o-?levels?|10th\s+grade|grade\s+10|class\s+10)\b",
            LEVEL_MATRICULATION,
        ),
        # High School General
        (r"\b(high\s*school(\s+diploma)?|secondary\s+school)\b", LEVEL_MATRICULATION),
        # Middle School / Lower Secondary
        (
            r"\b(middle\s+school|lower\s+secondary|junior\s+high|grade\s+[6-8]|class\s+[6-8]|ib\s+myp)\b",
            LEVEL_MIDDLE_SCHOOL,
        ),
        # Primary / Elementary School
        (
            r"\b(primary(\s+school)?|elementary(\s+school)?|grade\s+[1-5]|class\s+[1-5])\b",
            LEVEL_PRIMARY,
        ),
        # No formal qualification / Other
        (
            r"\b(no\s+formal\s+qualification|informal|self[- ]taught|none|other)\b",
            LEVEL_NO_FORMAL,
        ),
    ]

    FIELD_TAXONOMY: ClassVar[dict[str, tuple[str, str]]] = {
        # School Academic Streams
        "pre-medical": ("Pre-Medical", "Natural & Medical Sciences"),
        "pre medical": ("Pre-Medical", "Natural & Medical Sciences"),
        "pre-engineering": ("Pre-Engineering", "Engineering & Physical Sciences"),
        "pre engineering": ("Pre-Engineering", "Engineering & Physical Sciences"),
        "science": ("General Science", "Natural Sciences"),
        "arts": ("Arts & Humanities", "Humanities & Social Sciences"),
        "humanities": ("Arts & Humanities", "Humanities & Social Sciences"),
        "commerce": ("Commerce & Business", "Business & Economics"),
        "general science": ("General Science", "Natural Sciences"),
        # Computing
        "computer science": ("Computer Science", "Computing & Information Technology"),
        "cs": ("Computer Science", "Computing & Information Technology"),
        "software engineering": ("Software Engineering", "Computing & Information Technology"),
        "se": ("Software Engineering", "Computing & Information Technology"),
        "artificial intelligence": ("Artificial Intelligence", "Computing & Information Technology"),
        "ai": ("Artificial Intelligence", "Computing & Information Technology"),
        "machine learning": ("Machine Learning", "Computing & Information Technology"),
        "ml": ("Machine Learning", "Computing & Information Technology"),
        "data science": ("Data Science", "Computing & Information Technology"),
        "information technology": ("Information Technology", "Computing & Information Technology"),
        "it": ("Information Technology", "Computing & Information Technology"),
        "cybersecurity": ("Cybersecurity", "Computing & Information Technology"),
        # Engineering
        "electrical engineering": ("Electrical Engineering", "Engineering & Physical Sciences"),
        "mechanical engineering": ("Mechanical Engineering", "Engineering & Physical Sciences"),
        "civil engineering": ("Civil Engineering", "Engineering & Physical Sciences"),
        "biomedical engineering": ("Biomedical Engineering", "Engineering & Physical Sciences"),
        # Trades & Vocational
        "electrician": ("Electrical Trade", "Vocational & Technical Trades"),
        "plumbing": ("Plumbing Trade", "Vocational & Technical Trades"),
        "carpentry": ("Carpentry & Construction", "Vocational & Technical Trades"),
        "culinary arts": ("Culinary Arts & Hospitality", "Vocational & Hospitality"),
        "automotive": ("Automotive Technology", "Vocational & Technical Trades"),
        # Natural & Health Sciences
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
    def normalize_degree_level(cls, text: str | None, country: str | None = None) -> str:
        """Determines the standard degree level covering all 13 canonical levels."""
        if not text:
            return cls.LEVEL_NO_FORMAL
        cleaned = text.strip()

        # Exact match with any canonical or alias EducationLevel values
        for lvl in EducationLevel:
            if cleaned.lower() == lvl.value.lower() or cleaned.lower() == lvl.name.lower():
                # Map old legacy enum values to modern canonical 13
                if lvl == EducationLevel.HIGH_SCHOOL:
                    return cls.LEVEL_MATRICULATION
                if lvl == EducationLevel.UNDERGRADUATE:
                    return cls.LEVEL_BACHELORS
                if lvl == EducationLevel.GRADUATE:
                    return cls.LEVEL_MASTERS
                if lvl == EducationLevel.PHD:
                    return cls.LEVEL_DOCTORATE
                if lvl == EducationLevel.OTHER:
                    return cls.LEVEL_NO_FORMAL
                return lvl.value

        # Country-specific prioritization
        country_lower = (country or "").lower().strip()
        lowered = cleaned.lower()

        if "pakistan" in country_lower:
            if re.search(r"\b(matric|ssc|science|arts)\b", lowered) and not re.search(
                r"\b(inter|fsc|hssc)\b", lowered
            ):
                return cls.LEVEL_MATRICULATION
            if re.search(r"\b(intermediate|hssc|f\.?sc|f\.?a|ics|i\.?com)\b", lowered):
                return cls.LEVEL_INTERMEDIATE
            if "dae" in lowered:
                return cls.LEVEL_ASSOCIATE

        if "united kingdom" in country_lower or "uk" in country_lower:
            if re.search(r"\b(gcse|o-?level)\b", lowered):
                return cls.LEVEL_MATRICULATION
            if re.search(r"\b(a-?level|t-?level|btec)\b", lowered):
                return cls.LEVEL_A_LEVELS_IB

        # General pattern matching
        for pattern, level in cls.DEGREE_PATTERNS:
            if re.search(pattern, lowered, re.IGNORECASE):
                return level

        return cls.LEVEL_NO_FORMAL

    @classmethod
    def extract_stream(cls, text: str | None) -> str | None:
        """Extracts academic stream or trade for school/vocational students."""
        if not text:
            return None
        lowered = text.lower()
        if "pre-med" in lowered or "pre med" in lowered:
            return "Pre-Medical"
        if "pre-eng" in lowered or "pre eng" in lowered:
            return "Pre-Engineering"
        if "computer" in lowered or "ics" in lowered or "it" in lowered:
            return "Computer Science"
        if "commerce" in lowered or "icom" in lowered or "business" in lowered:
            return "Commerce"
        if "humanities" in lowered or "arts" in lowered or "fa" in lowered:
            return "Arts & Humanities"
        if "science" in lowered:
            return "General Science"
        return None

    @classmethod
    def normalize_field_of_study(
        cls, field_text: str | None
    ) -> tuple[str | None, str | None]:
        """Maps a field of study or school stream to (normalized_field, broad_discipline)."""
        if not field_text or not field_text.strip():
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
        cls,
        degree_text: str | None,
        field_text: str | None,
        country: str | None = None,
    ) -> NormalizedEducation:
        """Produces a unified NormalizedEducation object."""
        level = cls.normalize_degree_level(degree_text, country=country)
        norm_field, broad = cls.normalize_field_of_study(field_text)
        stream = cls.extract_stream(field_text) or cls.extract_stream(degree_text)

        return NormalizedEducation(
            raw_degree=degree_text,
            normalized_degree_level=level,
            raw_field=field_text,
            normalized_field=norm_field,
            broad_discipline=broad,
            country=country,
            stream=stream,
            confidence=1.0 if level != cls.LEVEL_NO_FORMAL else 0.8,
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
                return round(min(max((grade / 5.0) * 4.0, 0.0), 4.0), 2)
            elif scale_val == 10.0:
                return round(min(max((grade / 10.0) * 4.0, 0.0), 4.0), 2)
            elif scale_val == 100.0:
                return round(min(max((grade / 100.0) * 4.0, 0.0), 4.0), 2)

        if percentage is not None:
            return round(min(max((percentage / 100.0) * 4.0, 0.0), 4.0), 2)

        return None
