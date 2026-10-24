import re
from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class NormalizedSkillResult:
    raw_skill: str
    normalized_name: str
    category: str
    proficiency: str | None
    years_of_experience: float | None


class SkillsNormalizer:
    """Normalizes skills into standardized technical and research concepts."""

    SKILL_MAP: ClassVar[dict[str, tuple[str, str]]] = {
        # input_lower -> (canonical_name, category)
        "python": ("Python", "Programming Languages"),
        "python 3": ("Python", "Programming Languages"),
        "python programming": ("Python", "Programming Languages"),
        "python developer": ("Python", "Programming Languages"),
        "javascript": ("JavaScript", "Programming Languages"),
        "js": ("JavaScript", "Programming Languages"),
        "typescript": ("TypeScript", "Programming Languages"),
        "ts": ("TypeScript", "Programming Languages"),
        "c++": ("C++", "Programming Languages"),
        "cpp": ("C++", "Programming Languages"),
        "java": ("Java", "Programming Languages"),
        "rust": ("Rust", "Programming Languages"),
        "go": ("Go", "Programming Languages"),
        "golang": ("Go", "Programming Languages"),
        "pytorch": ("PyTorch", "AI/ML Frameworks"),
        "torch": ("PyTorch", "AI/ML Frameworks"),
        "tensorflow": ("TensorFlow", "AI/ML Frameworks"),
        "tf": ("TensorFlow", "AI/ML Frameworks"),
        "keras": ("Keras", "AI/ML Frameworks"),
        "scikit-learn": ("Scikit-Learn", "AI/ML Frameworks"),
        "sklearn": ("Scikit-Learn", "AI/ML Frameworks"),
        "machine learning": ("Machine Learning", "AI/ML Concepts"),
        "ml": ("Machine Learning", "AI/ML Concepts"),
        "deep learning": ("Deep Learning", "AI/ML Concepts"),
        "dl": ("Deep Learning", "AI/ML Concepts"),
        "natural language processing": ("Natural Language Processing", "AI/ML Concepts"),
        "nlp": ("Natural Language Processing", "AI/ML Concepts"),
        "computer vision": ("Computer Vision", "AI/ML Concepts"),
        "cv": ("Computer Vision", "AI/ML Concepts"),
        "llm": ("Large Language Models", "AI/ML Concepts"),
        "large language models": ("Large Language Models", "AI/ML Concepts"),
        "fastapi": ("FastAPI", "Web Frameworks"),
        "django": ("Django", "Web Frameworks"),
        "flask": ("Flask", "Web Frameworks"),
        "react": ("React", "Web Frameworks"),
        "reactjs": ("React", "Web Frameworks"),
        "react.js": ("React", "Web Frameworks"),
        "flutter": ("Flutter", "Mobile Development"),
        "docker": ("Docker", "DevOps & Cloud"),
        "kubernetes": ("Kubernetes", "DevOps & Cloud"),
        "k8s": ("Kubernetes", "DevOps & Cloud"),
        "aws": ("Amazon Web Services", "DevOps & Cloud"),
        "postgresql": ("PostgreSQL", "Databases"),
        "postgres": ("PostgreSQL", "Databases"),
        "sql": ("SQL", "Databases"),
        "git": ("Git", "Tools & Version Control"),
    }

    @classmethod
    def normalize_skill(
        cls,
        raw_skill: str,
        proficiency: str | None = None,
        years_of_experience: float | None = None,
        user_category: str | None = None,
    ) -> NormalizedSkillResult:
        """Standardizes a skill token into a canonical concept

        while preserving user declarations.
        """
        cleaned = raw_skill.strip().lower()

        # Remove redundant noise terms e.g. " programming language", " developer"
        cleaned_core = re.sub(
            r"\b(programming\s*language|developer|framework|engineer|proficient\s*in)\b",
            "",
            cleaned,
        ).strip()

        if cleaned in cls.SKILL_MAP:
            canonical_name, category = cls.SKILL_MAP[cleaned]
        elif cleaned_core in cls.SKILL_MAP:
            canonical_name, category = cls.SKILL_MAP[cleaned_core]
        else:
            # Fallback to Title Cased raw string
            canonical_name = " ".join(word.capitalize() for word in raw_skill.strip().split())
            category = user_category or "General Skills"

        return NormalizedSkillResult(
            raw_skill=raw_skill,
            normalized_name=canonical_name,
            category=user_category or category,
            proficiency=proficiency,
            years_of_experience=years_of_experience,
        )
