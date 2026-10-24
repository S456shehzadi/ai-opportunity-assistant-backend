"""Deduplication and canonical identity generation for extracted opportunities.

Ensures that identical opportunities discovered from different search queries,
syndicated aggregators, or tracking links are correctly identified with a
stable, deterministic canonical key.
"""

from __future__ import annotations

import hashlib
import re
from urllib.parse import urlparse

from app.opportunities.extraction.normalization import OrganizationNormalizer


class OpportunityDeduplicator:
    """Manages identity and deduplication across scraped opportunity pages."""

    @staticmethod
    def clean_canonical_url(url: str) -> str:
        """Strips query parameters, tracking tags (utm, ref), and fragments."""
        if not url:
            return ""
        parsed = urlparse(url)
        # Normalize domain (lowercase, remove 'www.')
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        # Normalize path (strip trailing slashes)
        path = parsed.path.rstrip("/")
        return f"{netloc}{path}"

    @classmethod
    def generate_canonical_key(
        cls,
        title: str,
        organization: str,
        category: str,
        official_url: str,
    ) -> str:
        """Computes a stable hash key identifying the opportunity uniquely.

        Formula: sha256(org_norm::title_norm::category_norm::url_norm)
        """
        # Normalize organization
        norm_org = OrganizationNormalizer.normalize(organization).canonical_name.lower().strip()

        # Normalize title: lowercase, remove special characters, remove excessive whitespace
        clean_title = re.sub(r"[^\w\s]", " ", title.lower()).strip()
        clean_title = re.sub(r"\s+", " ", clean_title)

        # Normalize category
        norm_cat = (category or "other").lower().strip()

        # Clean canonical URL path
        clean_url = cls.clean_canonical_url(official_url)

        seed = f"{norm_org}::{clean_title}::{norm_cat}::{clean_url}"
        digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]
        return f"opp_{digest}"

    @classmethod
    def are_duplicates(
        cls,
        title_a: str,
        org_a: str,
        url_a: str,
        title_b: str,
        org_b: str,
        url_b: str,
    ) -> bool:
        """Determines whether two opportunity records refer to the same program."""
        clean_url_a = cls.clean_canonical_url(url_a)
        clean_url_b = cls.clean_canonical_url(url_b)

        # If non-empty URLs point to the same clean path
        if clean_url_a and clean_url_b and clean_url_a == clean_url_b:
            return True

        # Check normalized orgs
        norm_org_a = OrganizationNormalizer.normalize(org_a).canonical_name.lower()
        norm_org_b = OrganizationNormalizer.normalize(org_b).canonical_name.lower()

        if norm_org_a != norm_org_b:
            return False

        # Compare cleaned titles
        t_a = re.sub(r"[^\w\s]", "", title_a.lower()).strip()
        t_b = re.sub(r"[^\w\s]", "", title_b.lower()).strip()

        if t_a == t_b:
            return True

        # Check high lexical overlap for title if same organization
        words_a = set(t_a.split())
        words_b = set(t_b.split())
        if not words_a or not words_b:
            return False

        intersection = words_a.intersection(words_b)
        union = words_a.union(words_b)
        jaccard = len(intersection) / len(union)

        return jaccard >= 0.75
