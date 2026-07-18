"""SSRF protection — validates that ingest URLs point to public web hosts.

Without this check, the ingest endpoint could be used to make the server
fetch internal addresses (localhost, cloud metadata services, private
network hosts) on an attacker's behalf.
"""

import ipaddress
import socket
from urllib.parse import urlparse

ALLOWED_SCHEMES = {"http", "https"}


def validate_public_url(url: str) -> None:
    """Raise ValueError unless the URL is an http(s) URL on a public host.

    Checks the scheme, then resolves the hostname and rejects any address
    that is private, loopback, link-local, reserved, multicast, or
    unspecified.

    Args:
        url: The URL to validate.

    Raises:
        ValueError: If the URL is not safe to fetch server-side.
    """
    parsed = urlparse(url)

    if parsed.scheme not in ALLOWED_SCHEMES:
        raise ValueError("Only http and https URLs are allowed.")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL has no host.")

    try:
        addr_infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        raise ValueError("Could not resolve the URL's host.")

    for info in addr_infos:
        ip = ipaddress.ip_address(info[4][0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            raise ValueError("URL resolves to a private or reserved address.")
