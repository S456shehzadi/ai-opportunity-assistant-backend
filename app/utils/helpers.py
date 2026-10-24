from urllib.parse import urlparse


def extract_domain(url: str) -> str:
    """Safely extract canonical hostname from a URL."""
    try:
        parsed = urlparse(url)
        return parsed.hostname or url
    except Exception:
        return url


def normalize_whitespace(text: str) -> str:
    """Normalize internal and external whitespace in extracted HTML snippets."""
    return " ".join(text.split())
