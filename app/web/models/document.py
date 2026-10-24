"""Structured models representing processed web documents and extracted elements."""

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class PageType(StrEnum):
    """Categorization of web page structures for downstream opportunity reasoning."""

    OPPORTUNITY_PAGE = "OPPORTUNITY_PAGE"
    ORGANIZATION_PAGE = "ORGANIZATION_PAGE"
    PROGRAM_PAGE = "PROGRAM_PAGE"
    NEWS_PAGE = "NEWS_PAGE"
    BLOG_PAGE = "BLOG_PAGE"
    DIRECTORY_PAGE = "DIRECTORY_PAGE"
    SEARCH_PAGE = "SEARCH_PAGE"
    HOME_PAGE = "HOME_PAGE"
    DOCUMENTATION = "DOCUMENTATION"
    UNKNOWN = "UNKNOWN"


class LinkType(StrEnum):
    """Categorization of extracted hyperlinks based on textual and contextual cues."""

    APPLICATION = "APPLICATION"
    ELIGIBILITY = "ELIGIBILITY"
    REQUIREMENTS = "REQUIREMENTS"
    DEADLINE = "DEADLINE"
    OFFICIAL_WEBSITE = "OFFICIAL_WEBSITE"
    CONTACT = "CONTACT"
    PDF = "PDF"
    MORE_INFO = "MORE_INFO"
    GENERAL = "GENERAL"


class ExtractedHeading(BaseModel):
    """Preserved heading from HTML hierarchy (H1-H6)."""

    level: int = Field(ge=1, le=6, description="Heading depth from 1 to 6")
    text: str = Field(description="Clean text content of heading")


class ExtractedTable(BaseModel):
    """Structured representation of HTML tabular data preserving row/column relationships."""

    caption: str | None = Field(default=None, description="Table caption or preceding heading")
    columns: list[str] = Field(default_factory=list, description="Column header labels")
    rows: list[list[str]] = Field(
        default_factory=list, description="Ordered grid of cell text values"
    )


class ExtractedLink(BaseModel):
    """Extracted hyperlink with context and preliminary classification."""

    text: str = Field(description="Anchor text or image description")
    url: str = Field(description="Absolute resolved target URL")
    relative_or_absolute: str = Field(
        default="absolute", description="'relative' or 'absolute' in source markup"
    )
    link_type: LinkType = Field(default=LinkType.GENERAL, description="Contextual classification")
    context: str | None = Field(
        default=None, description="Surrounding sentence or parent element text"
    )


class ExtractedDate(BaseModel):
    """Candidate date phrase extracted with surrounding context without semantic decision."""

    raw_text: str = Field(description="Literal date text snippet")
    context: str = Field(description="Surrounding sentence or paragraph snippet")
    parsed_iso: str | None = Field(
        default=None, description="ISO-8601 date string (YYYY-MM-DD) if parseable"
    )


class ContentQualityScore(BaseModel):
    """Assessment of content density, text-to-code ratio, and structure validity."""

    text_length: int = Field(default=0, description="Character count of clean text")
    word_count: int = Field(default=0, description="Word count of clean text")
    text_to_code_ratio: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Clean text size relative to raw HTML"
    )
    has_main_content: bool = Field(
        default=False, description="Whether a prominent semantic body was identified"
    )
    quality_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Overall heuristic content health score"
    )
    quality_flags: list[str] = Field(
        default_factory=list, description="Diagnostic flags (e.g. low_text_density, no_headings)"
    )


class WebDocument(BaseModel):
    """Clean, high-fidelity structured source document produced from web retrieval."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, description="Unique identifier for document")
    original_url: str = Field(description="Initial requested URL before redirects")
    final_url: str = Field(description="Resolved canonical target URL after redirects")
    domain: str = Field(description="Normalized host/domain name")
    status_code: int = Field(default=200, description="HTTP response status code")
    content_type: str = Field(default="text/html", description="MIME content type")
    retrieved_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp of retrieval",
    )
    title: str = Field(default="", description="Cleaned page title")
    raw_html: str | None = Field(
        default=None, description="Raw source markup (excluded from public APIs)"
    )
    clean_text: str = Field(
        default="", description="Sanitized, structured main content representation"
    )
    language: str | None = Field(
        default=None, description="Detected primary language code (e.g. en, de, fr)"
    )
    word_count: int = Field(default=0, description="Word count of clean text")
    headings: list[ExtractedHeading] = Field(
        default_factory=list, description="Ordered document headings"
    )
    tables: list[ExtractedTable] = Field(
        default_factory=list, description="Extracted structured tables"
    )
    links: list[ExtractedLink] = Field(
        default_factory=list, description="Extracted contextual links"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Extracted HTML, OG, and meta tag data"
    )
    extracted_dates: list[ExtractedDate] = Field(
        default_factory=list, description="Extracted date candidates with surrounding context"
    )
    content_quality: ContentQualityScore = Field(
        default_factory=ContentQualityScore, description="Content health assessment"
    )
    page_type: PageType = Field(
        default=PageType.UNKNOWN, description="Structural page classification"
    )
    content_hash: str = Field(
        default="", description="SHA-256 fingerprint of normalized text for exact deduplication"
    )
    simhash: str = Field(
        default="", description="64-bit SimHash hex string for near-duplicate detection"
    )
    is_js_dependent: bool = Field(
        default=False,
        description="Whether page indicates reliance on client-side JS rendering",
    )
    redirect_chain: list[str] = Field(
        default_factory=list, description="Intermediate redirect URLs followed"
    )
    warnings: list[str] = Field(
        default_factory=list, description="Diagnostic warnings or non-fatal anomalies"
    )
