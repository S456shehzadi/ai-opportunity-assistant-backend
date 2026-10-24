import re
from typing import ClassVar
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


class UrlNormalizer:
    """Normalizes URLs for deduplication, strip tracking tokens, and extract clean domains."""

    TRACKING_PARAMS: ClassVar[set[str]] = {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "fbclid",
        "gclid",
        "ref",
        "ref_src",
        "source",
        "trk",
        "_hsenc",
        "_hsmi",
        "mc_cid",
        "mc_eid",
        "vero_id",
        "yclid",
    }

    @classmethod
    def normalize_url(cls, raw_url: str) -> str:
        """Returns a canonical version of the URL stripped of tracking params and fragments."""
        if not raw_url:
            return ""

        url = raw_url.strip()
        parsed = urlparse(url)

        # Standardize scheme and host (lowercase)
        scheme = parsed.scheme.lower() if parsed.scheme else "https"
        netloc = parsed.netloc.lower()

        # Remove default ports
        if netloc.endswith(":80") and scheme == "http":
            netloc = netloc[:-3]
        elif netloc.endswith(":443") and scheme == "https":
            netloc = netloc[:-4]

        # Strip fragment
        fragment = ""

        # Normalize path: remove redundant slashes, strip trailing slash unless root '/'
        path = parsed.path or "/"
        path = re.sub(r"/{2,}", "/", path)
        if len(path) > 1 and path.endswith("/"):
            path = path[:-1]

        # Strip tracking query parameters, preserve meaningful parameters
        clean_query = ""
        if parsed.query:
            query_pairs = parse_qsl(parsed.query, keep_blank_values=True)
            filtered_pairs = [
                (k, v) for k, v in query_pairs if k.lower() not in cls.TRACKING_PARAMS
            ]
            if filtered_pairs:
                clean_query = urlencode(filtered_pairs)

        normalized = urlunparse((scheme, netloc, path, parsed.params, clean_query, fragment))
        return normalized

    @classmethod
    def extract_domain(cls, url: str) -> str:
        """Extracts clean displayed domain (stripping leading 'www.')."""
        if not url:
            return ""
        parsed = urlparse(url)
        netloc = (parsed.netloc or parsed.path).lower()
        # Remove port if present
        domain = netloc.split(":")[0]
        # Remove leading www.
        if domain.startswith("www."):
            domain = domain[4:]
        return domain

    @classmethod
    def is_same_resource(cls, url1: str, url2: str) -> bool:
        """Checks if two URLs point to the same canonical resource."""
        return cls.normalize_url(url1) == cls.normalize_url(url2)
