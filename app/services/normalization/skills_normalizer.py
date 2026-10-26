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
    status: str = "have"  # have, learning, desired
    acquisition_source: str | None = None


class SkillsNormalizer:
    """Normalizes skills into standardized technical, research, creative, business,

    transferable, and practical/vocational concepts.
    """

    SKILL_MAP: ClassVar[dict[str, tuple[str, str]]] = {
        # --- A. Technical and Digital Skills ---
        "python": ("Python", "Technical & Digital Skills"),
        "python 3": ("Python", "Technical & Digital Skills"),
        "python programming": ("Python", "Technical & Digital Skills"),
        "python developer": ("Python", "Technical & Digital Skills"),
        "javascript": ("JavaScript", "Technical & Digital Skills"),
        "js": ("JavaScript", "Technical & Digital Skills"),
        "typescript": ("TypeScript", "Technical & Digital Skills"),
        "ts": ("TypeScript", "Technical & Digital Skills"),
        "c++": ("C++", "Technical & Digital Skills"),
        "cpp": ("C++", "Technical & Digital Skills"),
        "c#": ("C#", "Technical & Digital Skills"),
        "java": ("Java", "Technical & Digital Skills"),
        "rust": ("Rust", "Technical & Digital Skills"),
        "go": ("Go", "Technical & Digital Skills"),
        "golang": ("Go", "Technical & Digital Skills"),
        "dart": ("Dart", "Technical & Digital Skills"),
        "html": ("HTML/CSS", "Technical & Digital Skills"),
        "html5": ("HTML/CSS", "Technical & Digital Skills"),
        "css": ("HTML/CSS", "Technical & Digital Skills"),
        "pytorch": ("PyTorch", "Technical & Digital Skills"),
        "torch": ("PyTorch", "Technical & Digital Skills"),
        "tensorflow": ("TensorFlow", "Technical & Digital Skills"),
        "tf": ("TensorFlow", "Technical & Digital Skills"),
        "keras": ("Keras", "Technical & Digital Skills"),
        "scikit-learn": ("Scikit-Learn", "Technical & Digital Skills"),
        "sklearn": ("Scikit-Learn", "Technical & Digital Skills"),
        "machine learning": ("Machine Learning", "Technical & Digital Skills"),
        "ml": ("Machine Learning", "Technical & Digital Skills"),
        "deep learning": ("Deep Learning", "Technical & Digital Skills"),
        "dl": ("Deep Learning", "Technical & Digital Skills"),
        "natural language processing": ("Natural Language Processing", "Technical & Digital Skills"),
        "nlp": ("Natural Language Processing", "Technical & Digital Skills"),
        "computer vision": ("Computer Vision", "Technical & Digital Skills"),
        "cv": ("Computer Vision", "Technical & Digital Skills"),
        "llm": ("Large Language Models", "Technical & Digital Skills"),
        "large language models": ("Large Language Models", "Technical & Digital Skills"),
        "fastapi": ("FastAPI", "Technical & Digital Skills"),
        "django": ("Django", "Technical & Digital Skills"),
        "flask": ("Flask", "Technical & Digital Skills"),
        "react": ("React", "Technical & Digital Skills"),
        "reactjs": ("React", "Technical & Digital Skills"),
        "react.js": ("React", "Technical & Digital Skills"),
        "flutter": ("Flutter", "Technical & Digital Skills"),
        "docker": ("Docker", "Technical & Digital Skills"),
        "kubernetes": ("Kubernetes", "Technical & Digital Skills"),
        "k8s": ("Kubernetes", "Technical & Digital Skills"),
        "aws": ("Amazon Web Services", "Technical & Digital Skills"),
        "azure": ("Microsoft Azure", "Technical & Digital Skills"),
        "gcp": ("Google Cloud Platform", "Technical & Digital Skills"),
        "postgresql": ("PostgreSQL", "Technical & Digital Skills"),
        "postgres": ("PostgreSQL", "Technical & Digital Skills"),
        "sql": ("SQL", "Technical & Digital Skills"),
        "mongodb": ("MongoDB", "Technical & Digital Skills"),
        "git": ("Git", "Technical & Digital Skills"),
        "github": ("GitHub", "Technical & Digital Skills"),
        "linux": ("Linux", "Technical & Digital Skills"),
        "data analysis": ("Data Analysis", "Technical & Digital Skills"),
        "excel": ("Microsoft Excel", "Technical & Digital Skills"),
        "advanced excel": ("Microsoft Excel", "Technical & Digital Skills"),
        "power bi": ("Power BI", "Technical & Digital Skills"),
        "tableau": ("Tableau", "Technical & Digital Skills"),
        "autocad": ("AutoCAD", "Technical & Digital Skills"),
        "matlab": ("MATLAB", "Technical & Digital Skills"),
        "solidworks": ("SolidWorks", "Technical & Digital Skills"),
        "cybersecurity": ("Cybersecurity", "Technical & Digital Skills"),

        # --- B. Professional and Transferable Skills ---
        "communication": ("Communication", "Professional & Transferable Skills"),
        "written communication": ("Written Communication", "Professional & Transferable Skills"),
        "presentation": ("Presentation", "Professional & Transferable Skills"),
        "presentation skills": ("Presentation", "Professional & Transferable Skills"),
        "teamwork": ("Teamwork", "Professional & Transferable Skills"),
        "collaboration": ("Teamwork", "Professional & Transferable Skills"),
        "leadership": ("Leadership", "Professional & Transferable Skills"),
        "team leadership": ("Leadership", "Professional & Transferable Skills"),
        "critical thinking": ("Critical Thinking", "Professional & Transferable Skills"),
        "problem solving": ("Problem Solving", "Professional & Transferable Skills"),
        "problem-solving": ("Problem Solving", "Professional & Transferable Skills"),
        "analytical thinking": ("Analytical Thinking", "Professional & Transferable Skills"),
        "time management": ("Time Management", "Professional & Transferable Skills"),
        "organization": ("Organization", "Professional & Transferable Skills"),
        "adaptability": ("Adaptability", "Professional & Transferable Skills"),
        "public speaking": ("Public Speaking", "Professional & Transferable Skills"),
        "negotiation": ("Negotiation", "Professional & Transferable Skills"),
        "project coordination": ("Project Coordination", "Professional & Transferable Skills"),
        "decision making": ("Decision Making", "Professional & Transferable Skills"),
        "conflict resolution": ("Conflict Resolution", "Professional & Transferable Skills"),

        # --- C. Research and Academic Skills ---
        "literature review": ("Literature Review", "Research & Academic Skills"),
        "research design": ("Research Design", "Research & Academic Skills"),
        "data collection": ("Data Collection", "Research & Academic Skills"),
        "statistical analysis": ("Statistical Analysis", "Research & Academic Skills"),
        "qualitative research": ("Qualitative Research", "Research & Academic Skills"),
        "quantitative research": ("Quantitative Research", "Research & Academic Skills"),
        "academic writing": ("Academic Writing", "Research & Academic Skills"),
        "technical writing": ("Technical Writing", "Research & Academic Skills"),
        "referencing": ("Referencing and Citation", "Research & Academic Skills"),
        "citation": ("Referencing and Citation", "Research & Academic Skills"),
        "experimental methods": ("Experimental Methods", "Research & Academic Skills"),
        "scientific communication": ("Scientific Communication", "Research & Academic Skills"),
        "research ethics": ("Research Ethics", "Research & Academic Skills"),
        "grant writing": ("Grant Proposal Writing", "Research & Academic Skills"),
        "grant proposal writing": ("Grant Proposal Writing", "Research & Academic Skills"),

        # --- D. Business and Entrepreneurship Skills ---
        "business planning": ("Business Planning", "Business & Entrepreneurship Skills"),
        "market research": ("Market Research", "Business & Entrepreneurship Skills"),
        "financial analysis": ("Financial Analysis", "Business & Entrepreneurship Skills"),
        "product management": ("Product Management", "Business & Entrepreneurship Skills"),
        "customer discovery": ("Customer Discovery", "Business & Entrepreneurship Skills"),
        "sales": ("Sales", "Business & Entrepreneurship Skills"),
        "marketing strategy": ("Marketing Strategy", "Business & Entrepreneurship Skills"),
        "digital marketing": ("Digital Marketing", "Business & Entrepreneurship Skills"),
        "seo": ("Search Engine Optimization (SEO)", "Business & Entrepreneurship Skills"),
        "search engine optimization": ("Search Engine Optimization (SEO)", "Business & Entrepreneurship Skills"),
        "social media marketing": ("Social Media Management", "Business & Entrepreneurship Skills"),
        "branding": ("Branding", "Business & Entrepreneurship Skills"),
        "business development": ("Business Development", "Business & Entrepreneurship Skills"),
        "fundraising": ("Fundraising", "Business & Entrepreneurship Skills"),
        "startup development": ("Startup Development", "Business & Entrepreneurship Skills"),

        # --- E. Creative and Communication Skills ---
        "graphic design": ("Graphic Design", "Creative & Communication Skills"),
        "ui/ux": ("UI/UX Design", "Creative & Communication Skills"),
        "ui/ux design": ("UI/UX Design", "Creative & Communication Skills"),
        "figma": ("Figma", "Creative & Communication Skills"),
        "adobe photoshop": ("Adobe Photoshop", "Creative & Communication Skills"),
        "photoshop": ("Adobe Photoshop", "Creative & Communication Skills"),
        "adobe illustrator": ("Adobe Illustrator", "Creative & Communication Skills"),
        "illustrator": ("Adobe Illustrator", "Creative & Communication Skills"),
        "video editing": ("Video Editing", "Creative & Communication Skills"),
        "premiere pro": ("Adobe Premiere Pro", "Creative & Communication Skills"),
        "animation": ("Animation", "Creative & Communication Skills"),
        "3d modeling": ("3D Modeling & Animation", "Creative & Communication Skills"),
        "photography": ("Photography", "Creative & Communication Skills"),
        "content writing": ("Content Writing", "Creative & Communication Skills"),
        "copywriting": ("Copywriting", "Creative & Communication Skills"),
        "storytelling": ("Storytelling", "Creative & Communication Skills"),

        # --- F. Practical, Vocational and Industry Skills ---
        "electrical wiring": ("Electrical Installation & Wiring", "Practical & Vocational Skills"),
        "electrical installation": ("Electrical Installation & Wiring", "Practical & Vocational Skills"),
        "welding": ("Welding and Fabrication", "Practical & Vocational Skills"),
        "mig welding": ("Welding and Fabrication", "Practical & Vocational Skills"),
        "tig welding": ("Welding and Fabrication", "Practical & Vocational Skills"),
        "cnc machining": ("CNC Machining", "Practical & Vocational Skills"),
        "cnc": ("CNC Machining", "Practical & Vocational Skills"),
        "automotive repair": ("Automotive Diagnostics & Repair", "Practical & Vocational Skills"),
        "plumbing": ("Plumbing & Piping", "Practical & Vocational Skills"),
        "solar installation": ("Solar Panel Installation", "Practical & Vocational Skills"),
        "hvac": ("HVAC Maintenance", "Practical & Vocational Skills"),
        "culinary arts": ("Culinary Arts & Cooking", "Practical & Vocational Skills"),
        "cooking": ("Culinary Arts & Cooking", "Practical & Vocational Skills"),
        "patient care": ("Patient Care & Healthcare Support", "Practical & Vocational Skills"),
        "nursing assistance": ("Patient Care & Healthcare Support", "Practical & Vocational Skills"),
        "technical drafting": ("Technical Drafting", "Practical & Vocational Skills"),
    }

    @classmethod
    def normalize_skill(
        cls,
        raw_skill: str,
        proficiency: str | None = None,
        years_of_experience: float | None = None,
        user_category: str | None = None,
        status: str = "have",
        acquisition_source: str | None = None,
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
            status=status,
            acquisition_source=acquisition_source,
        )
