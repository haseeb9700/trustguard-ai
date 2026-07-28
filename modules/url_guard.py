"""SSRF protection — validates that ingest URLs point to public web hosts.

Without this check, the ingest endpoint could be used to make the server
fetch internal addresses (localhost, cloud metadata services, private
network hosts) on an attacker's behalf.

Two layers of defence:

1. ``validate_public_url`` resolves the host and rejects any private,
   loopback, link-local, reserved, multicast, or unspecified address.
2. ``pin_validated_host`` closes the DNS-rebinding window: it resolves and
   validates the host once, then forces the actual connection to use that
   exact IP. Without pinning, an attacker's domain could resolve to a public
   IP during validation and to an internal IP a moment later at connect time.
   Pinning only rewrites the target address — TLS SNI and certificate
   verification still use the original hostname, so HTTPS stays correct.
"""

import ipaddress
import socket
import threading
from contextlib import contextmanager
from urllib.parse import urlparse

ALLOWED_SCHEMES = {"http", "https"}

# Installed once at import: a getaddrinfo wrapper that remaps only the hosts
# we have explicitly pinned, delegating everything else to the real resolver.
_real_getaddrinfo = socket.getaddrinfo
_pin_lock = threading.Lock()
_pinned_hosts: dict = {}


def _patched_getaddrinfo(host, *args, **kwargs):
    pinned = _pinned_hosts.get(str(host).lower())
    if pinned:
        return _real_getaddrinfo(pinned, *args, **kwargs)
    return _real_getaddrinfo(host, *args, **kwargs)


if socket.getaddrinfo is not _patched_getaddrinfo:
    socket.getaddrinfo = _patched_getaddrinfo


def _is_blocked(ip_str: str) -> bool:
    ip = ipaddress.ip_address(ip_str)
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def _resolve_validated_ips(hostname: str) -> list:
    """Resolve a hostname and return its IPs, raising if any is non-public.

    Uses ``socket.getaddrinfo`` (the live reference, which is normally our pin
    wrapper) rather than the captured original, so tests that monkeypatch
    ``socket.getaddrinfo`` still exercise this validation.
    """
    try:
        addr_infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise ValueError("Could not resolve the URL's host.") from exc

    ips = []
    for info in addr_infos:
        ip_str = info[4][0]
        if _is_blocked(ip_str):
            raise ValueError("URL resolves to a private or reserved address.")
        ips.append(ip_str)

    if not ips:
        raise ValueError("Could not resolve the URL's host.")

    return ips


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

    if not parsed.hostname:
        raise ValueError("URL has no host.")

    _resolve_validated_ips(parsed.hostname)


@contextmanager
def pin_validated_host(url: str):
    """Resolve and validate a URL's host, then pin the connection to that IP.

    Within the context, any DNS lookup for this host returns only the
    already-validated address, eliminating the rebinding window between
    validation and connection. Other hosts are unaffected.
    """
    hostname = urlparse(url).hostname
    if not hostname:
        raise ValueError("URL has no host.")

    ip = _resolve_validated_ips(hostname)[0]
    key = hostname.lower()

    with _pin_lock:
        _pinned_hosts[key] = ip
    try:
        yield
    finally:
        with _pin_lock:
            _pinned_hosts.pop(key, None)
