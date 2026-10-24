"""Strict URL validation and scheme sanitization for web retrieval."""

import re
from urllib.parse import urlparse, urlunparse

from app.web.models.errors import InvalidURLError

ALLOWED_SCHEMES = {"http", "https"}
DISALLOWED_HOST_CHARS = re.compile(r"[\s\x00-\x1f\x7f\"'<>\\^`{|}]")


class URLValidator:
    """Validates and normalizes target web URLs before retrieval."""

    @classmethod
    def validate_and_normalize(cls, raw_url: str) -> tuple[str, str]:
        """Validates that a URL is well-formed, uses http/https, and contains a valid host.

        Returns:
            tuple[str, str]: (normalized_url, hostname)

        Raises:
            InvalidURLError: If the URL fails scheme, hostname, or syntax checks.
        """
        if not raw_url or not isinstance(raw_url, str):
            raise InvalidURLError("URL must be a non-empty string.", url=str(raw_url))

        url_str = raw_url.strip()
        if not url_str:
            raise InvalidURLError("URL must not be empty or whitespace.", url=raw_url)

        try:
            parsed = urlparse(url_str)
        except Exception as exc:
            raise InvalidURLError(f"Failed to parse URL: {exc}", url=raw_url) from exc

        scheme = parsed.scheme.lower()
        if not scheme:
            raise InvalidURLError(
                "URL scheme is missing. Only http:// and https:// are permitted.", url=raw_url
            )

        if scheme not in ALLOWED_SCHEMES:
            raise InvalidURLError(
                f"Unsupported URL scheme '{scheme}'. Only http:// and https:// are permitted.",
                url=raw_url,
            )

        if not parsed.netloc:
            raise InvalidURLError("URL missing network location/hostname.", url=raw_url)

        # Check for userinfo (user:password@host)
        if parsed.username or parsed.password:
            raise InvalidURLError("URLs with embedded credentials are not permitted.", url=raw_url)

        hostname = (parsed.hostname or "").lower().strip()
        if not hostname:
            raise InvalidURLError("URL missing valid hostname.", url=raw_url)

        if DISALLOWED_HOST_CHARS.search(hostname):
            raise InvalidURLError(
                f"Hostname contains invalid characters: '{hostname}'", url=raw_url
            )

        # Basic hostname format validation
        if hostname.startswith(".") or hostname.endswith("."):
            raise InvalidURLError(f"Malformed hostname: '{hostname}'", url=raw_url)

        # Normalize port
        port = parsed.port
        netloc = hostname
        if port:
            if (scheme == "http" and port != 80) or (scheme == "https" and port != 443):
                netloc = f"{hostname}:{port}"

        # Clean path and drop fragments (#)
        path = parsed.path or "/"
        normalized = urlunparse(
            (
                scheme,
                netloc,
                path,
                parsed.params,
                parsed.query,
                "",  # Remove fragment
            )
        )

        return normalized, hostname
