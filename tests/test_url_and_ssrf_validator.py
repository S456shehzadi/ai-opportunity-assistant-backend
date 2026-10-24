"""Tests for URL validation, scheme restrictions, and SSRF security protection."""

import pytest

from app.web.models.errors import (
    InvalidURLError,
    RedirectBlockedError,
    SSRFBlockedError,
)
from app.web.security.ssrf_protector import SSRFProtector
from app.web.security.url_validator import URLValidator


def test_url_validator_valid_http_and_https() -> None:
    norm1, host1 = URLValidator.validate_and_normalize(
        "https://example.org/scholarship?id=123#section"
    )
    assert norm1 == "https://example.org/scholarship?id=123"  # Fragment stripped
    assert host1 == "example.org"

    norm2, host2 = URLValidator.validate_and_normalize("http://portal.university.edu:8080/apply")
    assert norm2 == "http://portal.university.edu:8080/apply"
    assert host2 == "portal.university.edu"


def test_url_validator_rejects_disallowed_schemes() -> None:
    disallowed = [
        "file:///etc/passwd",
        "ftp://ftp.example.org/file.txt",
        "javascript:alert(1)",
        "data:text/html,<html></html>",
        "gopher://gopher.example.org",
    ]
    for url in disallowed:
        with pytest.raises(InvalidURLError):
            URLValidator.validate_and_normalize(url)


def test_url_validator_rejects_credentials_and_empty() -> None:
    with pytest.raises(InvalidURLError):
        URLValidator.validate_and_normalize("http://admin:secret@example.org/path")

    with pytest.raises(InvalidURLError):
        URLValidator.validate_and_normalize("")

    with pytest.raises(InvalidURLError):
        URLValidator.validate_and_normalize("   ")


def test_ssrf_blocks_loopback_and_private_ips() -> None:
    # Loopback
    with pytest.raises(SSRFBlockedError):
        SSRFProtector.validate_host("127.0.0.1")

    with pytest.raises(SSRFBlockedError):
        SSRFProtector.validate_host("localhost")

    # Private IPv4 subnets
    with pytest.raises(SSRFBlockedError):
        SSRFProtector.validate_host("10.0.0.5")

    with pytest.raises(SSRFBlockedError):
        SSRFProtector.validate_host("192.168.1.100")

    with pytest.raises(SSRFBlockedError):
        SSRFProtector.validate_host("172.16.50.1")


def test_ssrf_blocks_cloud_metadata_ip() -> None:
    # AWS/GCP/Azure link-local instance metadata endpoint
    with pytest.raises(SSRFBlockedError):
        SSRFProtector.validate_host("169.254.169.254")

    # Multicast and 0.0.0.0
    with pytest.raises(SSRFBlockedError):
        SSRFProtector.validate_host("0.0.0.0")

    with pytest.raises(SSRFBlockedError):
        SSRFProtector.validate_host("224.0.0.1")


def test_ssrf_allows_public_ip() -> None:
    # Public DNS / web IP addresses (e.g. Quad9, Cloudflare)
    ips = SSRFProtector.validate_host("9.9.9.9")
    assert "9.9.9.9" in ips


def test_ssrf_redirect_validation_blocks_private_targets() -> None:
    # Attempting to redirect from external to internal
    with pytest.raises(SSRFBlockedError):
        SSRFProtector.validate_redirect(
            current_url="https://example.org/login",
            location_header="http://169.254.169.254/latest/meta-data/",
            redirect_chain=[],
        )

    with pytest.raises(SSRFBlockedError):
        SSRFProtector.validate_redirect(
            current_url="https://example.org/search",
            location_header="http://127.0.0.1:8000/admin",
            redirect_chain=[],
        )


def test_ssrf_redirect_detects_loops_and_depth() -> None:
    # Loop detection
    with pytest.raises(RedirectBlockedError, match="loop"):
        SSRFProtector.validate_redirect(
            current_url="https://example.org/page-b",
            location_header="https://example.org/page-a",
            redirect_chain=["https://example.org/page-a", "https://example.org/page-b"],
        )

    # Exceeding depth
    with pytest.raises(RedirectBlockedError, match="maximum redirect depth"):
        SSRFProtector.validate_redirect(
            current_url="https://example.org/page-5",
            location_header="https://example.org/page-6",
            redirect_chain=[
                "https://example.org/1",
                "https://example.org/2",
                "https://example.org/3",
                "https://example.org/4",
                "https://example.org/5",
            ],
            max_redirects=5,
        )
