"""Tests for the SSRF protection guard."""

import socket

import pytest

import modules.url_guard as url_guard
from modules.url_guard import validate_public_url


def _fake_resolver(ip: str):
    def resolver(hostname, port):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 0))]

    return resolver


class TestScheme:
    def test_ftp_is_rejected(self):
        with pytest.raises(ValueError, match="http and https"):
            validate_public_url("ftp://example.com/file")

    def test_file_scheme_is_rejected(self):
        with pytest.raises(ValueError):
            validate_public_url("file:///etc/passwd")

    def test_missing_host_is_rejected(self):
        with pytest.raises(ValueError):
            validate_public_url("https://")


class TestPrivateAddresses:
    def test_public_ip_is_allowed(self, monkeypatch):
        monkeypatch.setattr(socket, "getaddrinfo", _fake_resolver("93.184.216.34"))
        validate_public_url("https://example.com/page")  # should not raise

    @pytest.mark.parametrize(
        "ip",
        [
            "127.0.0.1",        # loopback
            "10.0.0.5",         # private
            "192.168.1.1",      # private
            "172.16.0.1",       # private
            "169.254.169.254",  # link-local (cloud metadata)
            "0.0.0.0",          # unspecified
        ],
    )
    def test_internal_ips_are_rejected(self, monkeypatch, ip):
        monkeypatch.setattr(socket, "getaddrinfo", _fake_resolver(ip))
        with pytest.raises(ValueError, match="private or reserved"):
            validate_public_url("https://evil.example.com/")

    def test_unresolvable_host_is_rejected(self, monkeypatch):
        def boom(hostname, port):
            raise socket.gaierror("no such host")

        monkeypatch.setattr(socket, "getaddrinfo", boom)
        with pytest.raises(ValueError, match="resolve"):
            validate_public_url("https://does-not-exist.invalid/")
