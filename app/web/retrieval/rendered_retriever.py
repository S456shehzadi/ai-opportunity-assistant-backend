"""Abstraction for future rendered-page retrieval and JS-dependency detection."""

import re
from abc import ABC, abstractmethod

from app.web.models.document import WebDocument

JS_INDICATOR_PATTERNS = [
    re.compile(r'<div\s+id=["\'](?:root|app|__next|__nuxt)["\']\s*>\s*</div>', re.IGNORECASE),
    re.compile(
        r"<noscript>[^<]*(?:enable\s+javascript|requires\s+javascript)[^<]*</noscript>",
        re.IGNORECASE,
    ),
    re.compile(r'<body[^>]*>\s*<script[^>]*src="[^"]+"[^>]*>\s*</script>\s*</body>', re.IGNORECASE),
]


def detect_js_dependency(raw_html: str, clean_text: str, word_count: int) -> bool:
    """Heuristic assessment whether initial HTML is an empty client-side JS application shell."""
    if not raw_html:
        return False

    # Check for known Single Page Application (SPA) shell patterns
    for pattern in JS_INDICATOR_PATTERNS:
        if pattern.search(raw_html) and word_count < 50:
            return True

    # If text is extremely short while HTML has scripts
    if word_count < 30 and len(raw_html) > 1000 and "<script" in raw_html.lower():
        # High ratio of markup/scripts to readable text
        return True

    return False


class RenderedPageRetriever(ABC):
    """Abstract interface for future headless browser / client-side rendered retrieval."""

    @abstractmethod
    async def render_and_fetch(self, url: str) -> WebDocument:
        """Retrieves and executes JavaScript to render dynamic DOM content."""
        pass


class StubRenderedPageRetriever(RenderedPageRetriever):
    """Stub implementation documenting the extension boundary for headless browser workers."""

    async def render_and_fetch(self, url: str) -> WebDocument:
        raise NotImplementedError(
            "Rendered retrieval with browser automation will be integrated in a future phase."
        )
