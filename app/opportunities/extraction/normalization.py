"""Normalization utilities for extracted opportunity data.

Provides organization name standardization, academic/language requirement
rule mapping to database models, and degree/field taxonomy normalization.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.models.opportunity import RequirementOperator
from app.opportunities.extraction.schemas import (
    ExtractedAcademicRequirement,
    ExtractedLanguageRequirement,
)


@dataclass
class NormalizedOrganization:
    """Canonical organization metadata."""

    canonical_name: str
    display_name: str
    domain: str | None = None
    country: str | None = None


class OrganizationNormalizer:
    """Standardizes global institutions, universities, and granting bodies."""

    # Common canonical organizations
    KNOWN_ORGANIZATIONS: dict[str, NormalizedOrganization] = {
        "mit": NormalizedOrganization(
            canonical_name="Massachusetts Institute of Technology",
            display_name="MIT",
            domain="mit.edu",
            country="United States",
        ),
        "massachusetts institute of technology": NormalizedOrganization(
            canonical_name="Massachusetts Institute of Technology",
            display_name="Massachusetts Institute of Technology",
            domain="mit.edu",
            country="United States",
        ),
        "stanford": NormalizedOrganization(
            canonical_name="Stanford University",
            display_name="Stanford University",
            domain="stanford.edu",
            country="United States",
        ),
        "stanford university": NormalizedOrganization(
            canonical_name="Stanford University",
            display_name="Stanford University",
            domain="stanford.edu",
            country="United States",
        ),
        "harvard": NormalizedOrganization(
            canonical_name="Harvard University",
            display_name="Harvard University",
            domain="harvard.edu",
            country="United States",
        ),
        "harvard university": NormalizedOrganization(
            canonical_name="Harvard University",
            display_name="Harvard University",
            domain="harvard.edu",
            country="United States",
        ),
        "oxford": NormalizedOrganization(
            canonical_name="University of Oxford",
            display_name="University of Oxford",
            domain="ox.ac.uk",
            country="United Kingdom",
        ),
        "oxford university": NormalizedOrganization(
            canonical_name="University of Oxford",
            display_name="University of Oxford",
            domain="ox.ac.uk",
            country="United Kingdom",
        ),
        "university of oxford": NormalizedOrganization(
            canonical_name="University of Oxford",
            display_name="University of Oxford",
            domain="ox.ac.uk",
            country="United Kingdom",
        ),
        "cambridge": NormalizedOrganization(
            canonical_name="University of Cambridge",
            display_name="University of Cambridge",
            domain="cam.ac.uk",
            country="United Kingdom",
        ),
        "cambridge university": NormalizedOrganization(
            canonical_name="University of Cambridge",
            display_name="University of Cambridge",
            domain="cam.ac.uk",
            country="United Kingdom",
        ),
        "university of cambridge": NormalizedOrganization(
            canonical_name="University of Cambridge",
            display_name="University of Cambridge",
            domain="cam.ac.uk",
            country="United Kingdom",
        ),
        "daad": NormalizedOrganization(
            canonical_name="Deutscher Akademischer Austauschdienst",
            display_name="DAAD",
            domain="daad.de",
            country="Germany",
        ),
        "chevening": NormalizedOrganization(
            canonical_name="Foreign, Commonwealth & Development Office",
            display_name="Chevening",
            domain="chevening.org",
            country="United Kingdom",
        ),
        "fulbright": NormalizedOrganization(
            canonical_name="U.S. Department of State",
            display_name="Fulbright Program",
            domain="fulbrightprogram.org",
            country="United States",
        ),
        "erasmus": NormalizedOrganization(
            canonical_name="European Commission",
            display_name="Erasmus+",
            domain="erasmus-plus.ec.europa.eu",
            country="European Union",
        ),
        "eth zurich": NormalizedOrganization(
            canonical_name="ETH Zurich",
            display_name="ETH Zurich",
            domain="ethz.ch",
            country="Switzerland",
        ),
        "epfl": NormalizedOrganization(
            canonical_name="École Polytechnique Fédérale de Lausanne",
            display_name="EPFL",
            domain="epfl.ch",
            country="Switzerland",
        ),
        "nus": NormalizedOrganization(
            canonical_name="National University of Singapore",
            display_name="NUS",
            domain="nus.edu.sg",
            country="Singapore",
        ),
        "national university of singapore": NormalizedOrganization(
            canonical_name="National University of Singapore",
            display_name="National University of Singapore",
            domain="nus.edu.sg",
            country="Singapore",
        ),
        "cern": NormalizedOrganization(
            canonical_name="European Organization for Nuclear Research",
            display_name="CERN",
            domain="cern.ch",
            country="Switzerland",
        ),
    }

    @classmethod
    def normalize(cls, raw_org: str, source_domain: str | None = None) -> NormalizedOrganization:
        """Normalizes an organization name to canonical form."""
        if not raw_org or not raw_org.strip():
            fallback_name = source_domain or "Unknown Organization"
            return NormalizedOrganization(
                canonical_name=fallback_name,
                display_name=fallback_name,
                domain=source_domain,
            )

        cleaned = raw_org.strip()
        cleaned_key = re.sub(r"[^\w\s]", "", cleaned.lower()).strip()
        cleaned_key = re.sub(r"\s+", " ", cleaned_key)

        if cleaned_key in cls.KNOWN_ORGANIZATIONS:
            known = cls.KNOWN_ORGANIZATIONS[cleaned_key]
            return NormalizedOrganization(
                canonical_name=known.canonical_name,
                display_name=known.display_name,
                domain=known.domain or source_domain,
                country=known.country,
            )

        # Remove trailing corporate designations if present
        trimmed = re.sub(
            r"\b(inc|llc|ltd|gmbh|corp|co\.|organization|foundation)\.?$",
            "",
            cleaned,
            flags=re.IGNORECASE,
        ).strip()
        final_name = trimmed if trimmed else cleaned

        return NormalizedOrganization(
            canonical_name=final_name,
            display_name=final_name,
            domain=source_domain,
        )


class RequirementNormalizer:
    """Normalizes extracted academic and language requirements into database rule definitions."""

    @staticmethod
    def normalize_language_requirement(
        req: ExtractedLanguageRequirement,
    ) -> dict[str, Any] | None:
        """Converts an extracted language requirement into an OpportunityRequirement dictionary."""
        if not req.is_required and not req.minimum_score:
            return None

        test_name = (req.test_name or "english").lower().strip()
        req_type = "language_test"
        if "ielts" in test_name:
            req_type = "ielts"
        elif "toefl" in test_name:
            req_type = "toefl"
        elif "pte" in test_name:
            req_type = "pte"
        elif "gre" in test_name:
            req_type = "gre"
        elif "gmat" in test_name:
            req_type = "gmat"

        # Try to parse minimum score as float
        score_val: float | str = req.minimum_score or ""
        if req.minimum_score:
            score_match = re.search(r"(\d+(?:\.\d+)?)", req.minimum_score)
            if score_match:
                try:
                    score_val = float(score_match.group(1))
                except ValueError:
                    score_val = req.minimum_score

        return {
            "requirement_type": req_type,
            "operator": RequirementOperator.GREATER_THAN_EQUAL,
            "value": score_val,
            "unit": "band" if req_type == "ielts" else "score",
            "is_mandatory": req.is_required,
        }

    @staticmethod
    def normalize_academic_requirements(
        req: ExtractedAcademicRequirement,
    ) -> list[dict[str, Any]]:
        """Converts academic requirement into atomic OpportunityRequirement rule definitions."""
        rules: list[dict[str, Any]] = []

        if req.degree_level:
            rules.append(
                {
                    "requirement_type": "degree_level",
                    "operator": RequirementOperator.IN,
                    "value": [req.degree_level.lower()],
                    "unit": None,
                    "is_mandatory": True,
                }
            )

        if req.minimum_cgpa is not None:
            rules.append(
                {
                    "requirement_type": "cgpa",
                    "operator": RequirementOperator.GREATER_THAN_EQUAL,
                    "value": req.minimum_cgpa,
                    "unit": "4.0",
                    "is_mandatory": True,
                }
            )

        if req.minimum_percentage is not None:
            rules.append(
                {
                    "requirement_type": "percentage",
                    "operator": RequirementOperator.GREATER_THAN_EQUAL,
                    "value": req.minimum_percentage,
                    "unit": "%",
                    "is_mandatory": True,
                }
            )

        if req.degree_subject:
            rules.append(
                {
                    "requirement_type": "field_of_study",
                    "operator": RequirementOperator.CONTAINS,
                    "value": req.degree_subject,
                    "unit": None,
                    "is_mandatory": True,
                }
            )

        return rules


class DegreeFieldTaxonomy:
    """Taxonomy standardizer for degree levels and academic fields."""

    DEGREE_SYNONYMS: dict[str, str] = {
        "bs": "bachelor",
        "bsc": "bachelor",
        "ba": "bachelor",
        "beng": "bachelor",
        "bachelors": "bachelor",
        "undergraduate": "bachelor",
        "ms": "master",
        "msc": "master",
        "ma": "master",
        "meng": "master",
        "masters": "master",
        "postgraduate": "master",
        "graduate": "master",
        "phd": "phd",
        "doctorate": "phd",
        "doctoral": "phd",
        "postdoc": "postdoc",
        "postdoctoral": "postdoc",
        "high school": "high_school",
        "secondary school": "high_school",
    }

    @classmethod
    def normalize_degree(cls, raw_degree: str | None) -> str | None:
        """Normalizes raw degree text into canonical taxonomy term."""
        if not raw_degree:
            return None
        cleaned = raw_degree.lower().strip()
        cleaned = re.sub(r"[^\w\s]", "", cleaned)
        for synonym, canonical in cls.DEGREE_SYNONYMS.items():
            if synonym == cleaned or re.search(rf"\b{synonym}\b", cleaned):
                return canonical
        return cleaned
