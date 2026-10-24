"""Structured web retrieval and processing exception hierarchy."""


class WebRetrievalError(Exception):
    """Base exception for all web retrieval and processing errors."""

    def __init__(self, message: str, url: str | None = None, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.url = url
        self.details = details or {}


class InvalidURLError(WebRetrievalError):
    """Raised when target URL fails syntax or scheme validation."""


class SSRFBlockedError(WebRetrievalError):
    """Raised when target URL resolves to a forbidden, private, or internal network address."""


class RobotsDisallowedError(WebRetrievalError):
    """Raised when target URL path is disallowed by the domain's robots.txt policy."""


class WebTimeoutError(WebRetrievalError):
    """Raised when connection, read, write, or pool timeout expires during retrieval."""


class DNSResolutionError(WebRetrievalError):
    """Raised when hostname DNS resolution fails or returns no valid addresses."""


class ConnectionFailureError(WebRetrievalError):
    """Raised when TCP/TLS connection to target host fails or is abruptly closed."""


class HTTPStatusError(WebRetrievalError):
    """Raised when server returns an HTTP error status code (e.g. 4xx, 5xx)."""

    def __init__(
        self,
        message: str,
        status_code: int,
        url: str | None = None,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(message, url=url, details={"status_code": status_code})
        self.status_code = status_code
        self.retry_after = retry_after


class ContentTooLargeError(WebRetrievalError):
    """Raised when downloaded response exceeds maximum configured payload/HTML byte size."""


class UnsupportedContentTypeError(WebRetrievalError):
    """Raised when HTTP response Content-Type is not supported (e.g. non-HTML/XHTML)."""


class RedirectBlockedError(WebRetrievalError):
    """Raised when redirect loop is detected or redirect exceeds maximum allowed hops."""


class ExtractionFailureError(WebRetrievalError):
    """Raised when HTML parsing or main content extraction fails."""
