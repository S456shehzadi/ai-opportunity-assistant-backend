"""Extensible global academic and professional field taxonomy.

Covers all 11 core categories specified in Prompt 26:
A. Computing and Information Technology
B. Engineering and Technology
C. Natural and Physical Sciences
D. Health and Life Sciences
E. Business, Economics and Management
F. Social Sciences and Humanities
G. Creative and Communication Fields
H. Law, Governance and Public Service
I. Agriculture, Environment and Food Systems
J. Vocational, Technical and Practical Fields
K. Other Education and Professional Fields
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import ClassVar


@dataclass(frozen=True)
class FieldCategory:
    id: str
    name: str
    disciplines: list[str]
    suggested_specializations: list[str]
    school_subjects: list[str] = field(default_factory=list)


class FieldTaxonomyService:
    TAXONOMY_VERSION = "2.0.0"

    CATEGORIES: ClassVar[dict[str, FieldCategory]] = {
        "computing": FieldCategory(
            id="computing",
            name="Computing and Information Technology",
            disciplines=[
                "Computer Science",
                "Software Engineering",
                "Information Technology",
                "Artificial Intelligence",
                "Machine Learning",
                "Data Science",
                "Data Analytics",
                "Cybersecurity",
                "Information Systems",
                "Cloud Computing",
                "Computer Networks",
                "Database Systems",
                "Human-Computer Interaction",
                "Computer Vision",
                "Natural Language Processing",
                "Robotics",
                "Internet of Things",
                "Distributed Systems",
                "Embedded Systems",
                "Game Development",
                "Web Development",
                "Mobile Application Development",
                "DevOps and Site Reliability Engineering",
                "Other Computing Disciplines",
            ],
            suggested_specializations=[
                "AI and Machine Learning",
                "Flutter and Mobile Engineering",
                "Software Architecture",
                "Data Engineering",
                "Cybersecurity & Ethical Hacking",
                "Cloud Infrastructure (AWS/GCP/Azure)",
                "Computer Vision & NLP",
                "Distributed Systems & Microservices",
                "Algorithms & Theoretical CS",
                "Full-Stack Web Development",
                "DevOps & CI/CD Automation",
                "Open-Source Development",
            ],
            school_subjects=[
                "Computer Science",
                "Information Technology",
                "Basic Programming",
                "Digital Literacy",
            ],
        ),
        "engineering": FieldCategory(
            id="engineering",
            name="Engineering and Technology",
            disciplines=[
                "Electrical Engineering",
                "Electronics Engineering",
                "Mechanical Engineering",
                "Civil Engineering",
                "Chemical Engineering",
                "Industrial Engineering",
                "Mechatronics",
                "Aerospace Engineering",
                "Biomedical Engineering",
                "Environmental Engineering",
                "Renewable Energy",
                "Telecommunications",
                "Materials Engineering",
                "Manufacturing and Automation",
                "Other Engineering Disciplines",
            ],
            suggested_specializations=[
                "Power Systems & Smart Grids",
                "Embedded Hardware & VLSI",
                "Structural Engineering",
                "Thermodynamics & Fluid Dynamics",
                "Robotics & Control Systems",
                "Renewable Energy & Solar Tech",
                "CAD/CAM & Mechanical Design",
                "Sustainable Construction",
                "Automotive & Transportation Engineering",
            ],
            school_subjects=[
                "Physics",
                "Mathematics",
                "Applied Sciences",
                "Technical Drawing",
            ],
        ),
        "natural_sciences": FieldCategory(
            id="natural_sciences",
            name="Natural and Physical Sciences",
            disciplines=[
                "Mathematics",
                "Statistics",
                "Physics",
                "Chemistry",
                "Biology",
                "Biotechnology",
                "Microbiology",
                "Biochemistry",
                "Genetics",
                "Environmental Science",
                "Earth Sciences",
                "Geology",
                "Astronomy",
                "Climate Science",
                "Other Scientific Disciplines",
            ],
            suggested_specializations=[
                "Pure Mathematics & Algebra",
                "Applied Statistics & Probability",
                "Quantum Physics & Optics",
                "Molecular Biology & Genetics",
                "Organic & Analytical Chemistry",
                "Bioinformatics & Computational Biology",
                "Ecology & Marine Biology",
                "Astrophysics",
            ],
            school_subjects=[
                "General Science",
                "Biology",
                "Chemistry",
                "Physics",
                "Mathematics",
            ],
        ),
        "health": FieldCategory(
            id="health",
            name="Health and Life Sciences",
            disciplines=[
                "Medicine",
                "Nursing",
                "Pharmacy",
                "Public Health",
                "Dentistry",
                "Physiotherapy",
                "Nutrition and Dietetics",
                "Biomedical Research",
                "Health Informatics",
                "Medical Laboratory Sciences",
                "Psychology-Related Health Disciplines",
                "Other Health and Life-Science Disciplines",
            ],
            suggested_specializations=[
                "Clinical Medicine & Surgery",
                "Epidemiology & Global Health",
                "Pharmacology & Drug Discovery",
                "Cardiovascular & Neurosciences",
                "Pediatrics & Maternal Health",
                "Physical Rehabilitation",
                "Clinical Nutrition",
                "Health Systems Management",
            ],
            school_subjects=[
                "Biology",
                "Human Physiology",
                "Health & Hygiene",
                "Chemistry",
            ],
        ),
        "business": FieldCategory(
            id="business",
            name="Business, Economics and Management",
            disciplines=[
                "Business Administration",
                "Economics",
                "Finance",
                "Accounting",
                "Marketing",
                "Digital Marketing",
                "Entrepreneurship",
                "International Business",
                "Human Resources",
                "Supply Chain Management",
                "Operations Management",
                "Project Management",
                "Business Analytics",
                "Management Information Systems",
                "Social Entrepreneurship",
                "Other Business Disciplines",
            ],
            suggested_specializations=[
                "Corporate Finance & Investment",
                "Digital Marketing & Growth",
                "Financial Accounting & Auditing",
                "Supply Chain Logistics",
                "Strategic Leadership & HR",
                "Fintech & Venture Capital",
                "Behavioral Economics",
                "Data-Driven Business Intelligence",
            ],
            school_subjects=[
                "Economics",
                "Commerce",
                "Accounting",
                "Business Studies",
            ],
        ),
        "social_sciences": FieldCategory(
            id="social_sciences",
            name="Social Sciences and Humanities",
            disciplines=[
                "Psychology",
                "Sociology",
                "Political Science",
                "International Relations",
                "Public Policy",
                "Education",
                "Linguistics",
                "History",
                "Philosophy",
                "Anthropology",
                "Development Studies",
                "Peace and Conflict Studies",
                "Gender Studies",
                "Cultural Studies",
                "Social Work",
                "Other Social-Science or Humanities Disciplines",
            ],
            suggested_specializations=[
                "Cognitive & Clinical Psychology",
                "Diplomacy & Global Governance",
                "Public Policy & Administration",
                "Applied Linguistics & ESL",
                "Curriculum & Educational Technology",
                "Human Rights & Social Justice",
                "Modern Global History",
            ],
            school_subjects=[
                "Social Studies",
                "History",
                "Geography",
                "Civics & Pakistan Studies",
                "English Literature",
            ],
        ),
        "creative": FieldCategory(
            id="creative",
            name="Creative and Communication Fields",
            disciplines=[
                "Graphic Design",
                "UI/UX Design",
                "Product Design",
                "Animation",
                "Film and Media",
                "Photography",
                "Journalism",
                "Communication",
                "Content Creation",
                "Writing and Editing",
                "Digital Arts",
                "Game Art",
                "Illustration",
                "Architecture",
                "Fashion and Textile Design",
                "Other Creative Disciplines",
            ],
            suggested_specializations=[
                "Mobile UI/UX & Interaction Design",
                "Brand Identity & Visual Design",
                "3D Animation & Motion Graphics",
                "Investigative Journalism",
                "Video Production & Editing",
                "Creative Writing & Copywriting",
                "Architectural Design & BIM",
            ],
            school_subjects=[
                "Art & Drawing",
                "Creative Writing",
                "Media Studies",
                "Design & Technology",
            ],
        ),
        "law": FieldCategory(
            id="law",
            name="Law, Governance and Public Service",
            disciplines=[
                "Law",
                "Human Rights Law",
                "International Law",
                "Public Administration",
                "Governance",
                "Public Policy",
                "Diplomacy",
                "Public Sector Management",
                "Other Related Disciplines",
            ],
            suggested_specializations=[
                "Corporate & Commercial Law",
                "International Human Rights",
                "Constitutional & Administrative Law",
                "Environmental & Energy Law",
                "Criminal Law & Criminology",
                "Public Sector Leadership",
            ],
            school_subjects=[
                "Civics",
                "Law & Justice Studies",
                "Political Systems",
            ],
        ),
        "agriculture": FieldCategory(
            id="agriculture",
            name="Agriculture, Environment and Food Systems",
            disciplines=[
                "Agriculture",
                "Agronomy",
                "Forestry",
                "Animal Sciences",
                "Veterinary Sciences",
                "Food Science",
                "Food Technology",
                "Water Resources Management",
                "Conservation Biology",
                "Sustainable Development",
                "Other Related Disciplines",
            ],
            suggested_specializations=[
                "Precision Agriculture & Smart Farming",
                "Crop Protection & Soil Science",
                "Veterinary Medicine & Animal Health",
                "Food Safety & Quality Assurance",
                "Forest Conservation & Watersheds",
                "Climate-Resilient Agriculture",
            ],
            school_subjects=[
                "Agricultural Science",
                "General Science",
                "Environmental Studies",
            ],
        ),
        "vocational": FieldCategory(
            id="vocational",
            name="Vocational, Technical and Practical Fields",
            disciplines=[
                "Electrical Trades",
                "Mechanical Trades",
                "Plumbing",
                "Welding and Fabrication",
                "Automotive Technology",
                "Construction",
                "Renewable Energy Installation",
                "Hospitality",
                "Culinary Arts",
                "Tourism",
                "Healthcare Support",
                "Industrial Maintenance",
                "Technical Drafting",
                "Other Vocational or Trade Disciplines",
            ],
            suggested_specializations=[
                "Industrial Electrician & Wiring",
                "CNC Machining & Tool Making",
                "MIG/TIG Welding & Fabrication",
                "Automotive Diagnostics & EV Repair",
                "Solar Panel & Inverter Installation",
                "HVAC (Heating, Ventilation & AC)",
                "Culinary Arts & Professional Kitchen",
                "Patient Care & Nursing Assistance",
            ],
            school_subjects=[
                "Technical Trades",
                "Workshop Practice",
                "Woodwork & Metalwork",
                "Home Economics",
            ],
        ),
        "other": FieldCategory(
            id="other",
            name="Other Education and Professional Fields",
            disciplines=[
                "Education and Teaching",
                "Logistics and Supply",
                "Transportation and Aviation",
                "Sports Science and Physical Education",
                "Mathematics Education",
                "Research Methodology",
                "Interdisciplinary Studies",
                "Other Professional Fields",
            ],
            suggested_specializations=[
                "Early Childhood & Primary Teaching",
                "Special Education & Inclusivity",
                "Sports Coaching & Athletic Training",
                "Aviation Management & Flight Ops",
                "Interdisciplinary Problem Solving",
            ],
            school_subjects=[
                "Physical Education",
                "General Studies",
            ],
        ),
    }

    @classmethod
    def get_all_categories(cls) -> list[FieldCategory]:
        return list(cls.CATEGORIES.values())

    @classmethod
    def find_category_for_discipline(cls, discipline_name: str) -> FieldCategory | None:
        disc_clean = discipline_name.strip().lower()
        for cat in cls.CATEGORIES.values():
            for d in cat.disciplines:
                if d.lower() == disc_clean or disc_clean in d.lower():
                    return cat
        return None

    @classmethod
    def get_suggested_specializations(cls, primary_field: str | None, is_school_level: bool = False) -> list[str]:
        if not primary_field:
            return cls.CATEGORIES["computing"].suggested_specializations[:6]

        cat = cls.find_category_for_discipline(primary_field)
        if cat:
            if is_school_level and cat.school_subjects:
                return cat.school_subjects + cat.suggested_specializations[:4]
            return cat.suggested_specializations

        # Fallback to computing + business top suggestions
        return (
            cls.CATEGORIES["computing"].suggested_specializations[:4]
            + cls.CATEGORIES["business"].suggested_specializations[:4]
        )

    @classmethod
    def search_disciplines(cls, query: str, limit: int = 15) -> list[dict[str, str]]:
        q = query.strip().lower()
        results: list[dict[str, str]] = []

        for cat in cls.CATEGORIES.values():
            for disc in cat.disciplines:
                if not q or q in disc.lower() or q in cat.name.lower():
                    results.append({"name": disc, "category": cat.name, "category_id": cat.id})
                    if len(results) >= limit:
                        return results
        return results
