"""Contextual link extraction and categorization."""

import re
from urllib.parse import urljoin

from app.web.extraction.html_parser import HTMLNode
from app.web.models.document import ExtractedLink, LinkType

PDF_EXTENSION_RE = re.compile(r"\.pdf(?:[?#].*)?$", re.IGNORECASE)

LINK_RULES: list[tuple[LinkType, re.Pattern, re.Pattern]] = [
    (
        LinkType.PDF,
        re.compile(r"\b(?:pdf|download\s+brochure|guidelines\s+pdf|flyer)\b", re.IGNORECASE),
        PDF_EXTENSION_RE,
    ),
    (
        LinkType.APPLICATION,
        re.compile(
            r"\b(?:apply\s+now|online\s+application|how\s+to\s+apply|submit\s+application|application\s+portal)\b",
            re.IGNORECASE,
        ),
        re.compile(r"/(?:apply|application|admissions/apply)\b", re.IGNORECASE),
    ),
    (
        LinkType.ELIGIBILITY,
        re.compile(
            r"\b(?:eligibility|eligible|who\s+can\s+apply|eligibility\s+criteria)\b", re.IGNORECASE
        ),
        re.compile(r"/(?:eligibility|eligible|criteria)\b", re.IGNORECASE),
    ),
    (
        LinkType.REQUIREMENTS,
        re.compile(
            r"\b(?:requirements|required\s+documents|prerequisites|selection\s+criteria)\b",
            re.IGNORECASE,
        ),
        re.compile(r"/(?:requirements|guidelines|prerequisites)\b", re.IGNORECASE),
    ),
    (
        LinkType.DEADLINE,
        re.compile(
            r"\b(?:deadline|key\s+dates|important\s+dates|schedule|timeline)\b", re.IGNORECASE
        ),
        re.compile(r"/(?:dates|deadlines|timeline)\b", re.IGNORECASE),
    ),
    (
        LinkType.OFFICIAL_WEBSITE,
        re.compile(
            r"\b(?:official\s+website|university\s+website|program\s+portal|homepage)\b",
            re.IGNORECASE,
        ),
        re.compile(r"/(?:official|home)\b", re.IGNORECASE),
    ),
    (
        LinkType.CONTACT,
        re.compile(
            r"\b(?:contact\s+us|inquiries|helpdesk|contact\s+person|email\s+us)\b", re.IGNORECASE
        ),
        re.compile(r"/(?:contact|inquiries|help)\b", re.IGNORECASE),
    ),
    (
        LinkType.MORE_INFO,
        re.compile(
            r"\b(?:read\s+more|learn\s+more|more\s+information|find\s+out\s+more|details)\b",
            re.IGNORECASE,
        ),
        re.compile(r"/(?:details|overview|info)\b", re.IGNORECASE),
    ),
]


class LinkExtractor:
    """Extracts, canonicalizes, and classifies hyperlinks from HTML trees."""

    @classmethod
    def extract_links(cls, root: HTMLNode, base_url: str) -> list[ExtractedLink]:
        """Finds all anchor links, resolves relative paths, and assigns contextual link types."""
        extracted: list[ExtractedLink] = []
        seen_urls: set[str] = set()

        a_nodes = root.find_all("a")
        for a in a_nodes:
            raw_href = a.get_attr("href")
            if not raw_href:
                continue

            clean_href = raw_href.strip()
            if clean_href.startswith(("javascript:", "mailto:", "tel:", "#")):
                continue

            resolved_url = urljoin(base_url, clean_href)
            if resolved_url in seen_urls:
                continue
            seen_urls.add(resolved_url)

            anchor_text = a.get_text() or a.get_attr("title") or a.get_attr("aria-label") or ""
            anchor_text = anchor_text.strip()
            if not anchor_text and not PDF_EXTENSION_RE.search(resolved_url):
                # Skip empty anchors without descriptive targets
                continue

            rel_or_abs = (
                "absolute" if clean_href.startswith(("http://", "https://")) else "relative"
            )

            # Context from parent node
            parent_context = None
            if a.parent:
                p_text = a.parent.get_text()
                if p_text and p_text != anchor_text:
                    parent_context = p_text[:200]

            link_type = cls._classify_link(anchor_text, resolved_url)

            extracted.append(
                ExtractedLink(
                    text=anchor_text or resolved_url,
                    url=resolved_url,
                    relative_or_absolute=rel_or_abs,
                    link_type=link_type,
                    context=parent_context,
                )
            )

        return extracted

    @classmethod
    def _classify_link(cls, text: str, url: str) -> LinkType:
        """Classifies link into an intentional category using anchor text and URL heuristics."""
        # 1. Direct PDF extension check
        if PDF_EXTENSION_RE.search(url):
            return LinkType.PDF

        # 2. Rule evaluation
        for link_type, text_pattern, url_pattern in LINK_RULES:
            if text_pattern.search(text) or url_pattern.search(url):
                return link_type

        return LinkType.GENERAL
