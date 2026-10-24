"""Web document and error models."""

from app.web.models.document import (
    ContentQualityScore,
    ExtractedDate,
    ExtractedHeading,
    ExtractedLink,
    ExtractedTable,
    LinkType,
    PageType,
    WebDocument,
)
from app.web.models.errors import (
    ConnectionFailureError,
    ContentTooLargeError,
    DNSResolutionError,
    ExtractionFailureError,
    HTTPStatusError,
    InvalidURLError,
    RedirectBlockedError,
    RobotsDisallowedError,
    SSRFBlockedError,
    UnsupportedContentTypeError,
    WebRetrievalError,
    WebTimeoutError,
)

__all__ = [
    "ConnectionFailureError",
    "ContentQualityScore",
    "ContentTooLargeError",
    "DNSResolutionError",
    "ExtractedDate",
    "ExtractedHeading",
    "ExtractedLink",
    "ExtractedTable",
    "ExtractionFailureError",
    "HTTPStatusError",
    "InvalidURLError",
    "LinkType",
    "PageType",
    "RedirectBlockedError",
    "RobotsDisallowedError",
    "SSRFBlockedError",
    "UnsupportedContentTypeError",
    "WebDocument",
    "WebRetrievalError",
    "WebTimeoutError",
]
