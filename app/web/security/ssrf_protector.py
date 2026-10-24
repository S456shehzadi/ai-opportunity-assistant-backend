"""Server-Side Request Forgery (SSRF) protection and redirect security checks."""

import ipaddress
import logging
import socket
from urllib.parse import urljoin

from app.web.models.errors import (
    DNSResolutionError,
    RedirectBlockedError,
    SSRFBlockedError,
)
from app.web.security.url_validator import URLValidator

logger = logging.getLogger(__name__)

DISALLOWED_HOSTNAMES = {
    "localhost",
    "localhost.localdomain",
    "ip6-localhost",
    "ip6-loopback",
    "metadata.google.internal",
    "instance-data",
}


class SSRFProtector:
    """Enforces strict IP and DNS validation to prevent Server-Side Request Forgery attacks."""

    @classmethod
    def validate_host(cls, hostname: str, url: str | None = None) -> list[str]:
        """Resolves hostname to IP addresses and verifies none belong to restricted IP subnets.

        Args:
            hostname: Target hostname or IP string.
            url: Optional context URL for error reporting.

        Returns:
            list[str]: Verified safe resolved IP addresses.

        Raises:
            SSRFBlockedError: If any resolved IP is loopback, private, link-local, or reserved.
            DNSResolutionError: If hostname cannot be resolved.
        """
        clean_host = hostname.strip().lower()

        # Check explicit disallowed named hosts
        if clean_host in DISALLOWED_HOSTNAMES or clean_host.endswith(".internal"):
            raise SSRFBlockedError(
                f"Access to internal hostname '{clean_host}' is prohibited.", url=url
            )

        # Check if hostname is already a literal IP address
        try:
            ip_obj = ipaddress.ip_address(clean_host)
            cls._verify_ip_is_public(ip_obj, url=url)
            return [str(ip_obj)]
        except ValueError:
            # Not a literal IP, proceed to DNS resolution
            pass

        # Resolve hostname via DNS
        try:
            addr_info = socket.getaddrinfo(
                clean_host,
                None,
                family=socket.AF_UNSPEC,
                type=socket.SOCK_STREAM,
            )
        except (socket.gaierror, OSError) as exc:
            raise DNSResolutionError(
                f"Failed to resolve DNS for hostname '{clean_host}': {exc}", url=url
            ) from exc

        if not addr_info:
            raise DNSResolutionError(
                f"DNS resolution returned no addresses for hostname '{clean_host}'.", url=url
            )

        verified_ips: list[str] = []
        for item in addr_info:
            sockaddr = item[4]
            ip_str = sockaddr[0]
            try:
                ip_obj = ipaddress.ip_address(ip_str)
            except ValueError as exc:
                raise SSRFBlockedError(
                    f"Resolved invalid IP address '{ip_str}' for host '{clean_host}'.", url=url
                ) from exc

            cls._verify_ip_is_public(ip_obj, url=url)
            verified_ips.append(ip_str)

        return verified_ips

    @classmethod
    def _verify_ip_is_public(
        cls, ip: ipaddress.IPv4Address | ipaddress.IPv6Address, url: str | None = None
    ) -> None:
        """Verifies that an IP is globally routable and not in private or reserved ranges."""
        if ip.is_loopback:
            raise SSRFBlockedError(f"Access to loopback address '{ip}' is prohibited.", url=url)
        if ip.is_private:
            raise SSRFBlockedError(
                f"Access to private network address '{ip}' is prohibited.", url=url
            )
        if ip.is_link_local:
            raise SSRFBlockedError(
                f"Access to link-local/cloud-metadata address '{ip}' is prohibited.", url=url
            )
        if ip.is_multicast:
            raise SSRFBlockedError(f"Access to multicast address '{ip}' is prohibited.", url=url)
        if ip.is_reserved:
            raise SSRFBlockedError(f"Access to reserved address '{ip}' is prohibited.", url=url)
        if ip.is_unspecified:
            raise SSRFBlockedError(f"Access to unspecified address '{ip}' is prohibited.", url=url)

        # Explicit check for IPv4-mapped IPv6 addresses (e.g. ::ffff:127.0.0.1)
        if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
            cls._verify_ip_is_public(ip.ipv4_mapped, url=url)

    @classmethod
    def validate_redirect(
        cls,
        current_url: str,
        location_header: str,
        redirect_chain: list[str],
        max_redirects: int = 5,
    ) -> tuple[str, str]:
        """Validates a redirect target URL against SSRF, loop, and depth rules.

        Returns:
            tuple[str, str]: (normalized_target_url, target_hostname)

        Raises:
            RedirectBlockedError: If redirect count exceeded or redirect loop detected.
            SSRFBlockedError: If redirect target resolves to private/internal address.
            InvalidURLError: If redirect target is malformed or uses disallowed scheme.
        """
        if len(redirect_chain) >= max_redirects:
            raise RedirectBlockedError(
                f"Exceeded maximum redirect depth of {max_redirects}.", url=current_url
            )

        # Resolve relative redirect URLs (e.g. "/path" or "../login")
        target_url = urljoin(current_url, location_header.strip())

        # Validate URL format and permitted scheme (http/https)
        normalized_url, hostname = URLValidator.validate_and_normalize(target_url)

        # Detect redirect loops
        if normalized_url in redirect_chain:
            raise RedirectBlockedError(
                f"Redirect loop detected: '{normalized_url}' was already visited.",
                url=normalized_url,
            )

        # Validate target host against SSRF (DNS resolution & IP check)
        cls.validate_host(hostname, url=normalized_url)

        return normalized_url, hostname
