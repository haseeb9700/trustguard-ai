"""Regression tests for the safe fetch path in url_ingestor.

Covers the SSRF redirect re-validation, the redirect cap, and the response
size cap. These exercise transport behaviour with a mocked ``requests.get``;
SSRF address validation and DNS pinning are tested in test_url_guard.py, so
here we stub validation to focus on the fetch/redirect/size logic.
"""

from contextlib import contextmanager

import pytest

import modules.url_ingestor as ui


class FakeResponse:
    def __init__(self, status_code=200, location=None, chunks=None, headers=None):
        self.status_code = status_code
        self.headers = dict(headers or {})
        if location:
            self.headers["Location"] = location
        self._chunks = chunks if chunks is not None else [b"body"]
        self._content = b""
        self.closed = False

    def iter_content(self, size):
        yield from self._chunks

    @property
    def content(self):
        return self._content

    def close(self):
        self.closed = True


@pytest.fixture(autouse=True)
def _stub_guard(monkeypatch):
    """Allow public hosts, reject any host containing 'internal'."""

    def fake_validate(url):
        if "internal" in url:
            raise ValueError("URL resolves to a private or reserved address.")

    @contextmanager
    def fake_pin(url):
        yield

    monkeypatch.setattr(ui, "validate_public_url", fake_validate)
    monkeypatch.setattr(ui, "pin_validated_host", fake_pin)


def _sequence(monkeypatch, responses):
    seq = list(responses)

    def fake_get(url, **kwargs):
        assert kwargs["allow_redirects"] is False
        assert kwargs["stream"] is True
        return seq.pop(0)

    monkeypatch.setattr(ui.requests, "get", fake_get)


class TestSafeGetRedirects:
    def test_follows_public_redirect(self, monkeypatch):
        _sequence(
            monkeypatch,
            [
                FakeResponse(302, location="http://example.com/final"),
                FakeResponse(200, chunks=[b"hello"]),
            ],
        )
        resp = ui._safe_get("http://example.com/start")
        assert resp.status_code == 200
        assert resp.content == b"hello"

    def test_redirect_to_internal_is_blocked(self, monkeypatch):
        _sequence(
            monkeypatch,
            [FakeResponse(302, location="http://169-internal.example/")],
        )
        with pytest.raises(ValueError, match="private or reserved"):
            ui._safe_get("http://example.com/start")

    def test_redirect_without_location_errors(self, monkeypatch):
        _sequence(monkeypatch, [FakeResponse(302)])
        with pytest.raises(ValueError, match="Location"):
            ui._safe_get("http://example.com/start")

    def test_too_many_redirects(self, monkeypatch):
        monkeypatch.setattr(
            ui.requests,
            "get",
            lambda url, **kw: FakeResponse(302, location="http://example.com/next"),
        )
        with pytest.raises(ValueError, match="Too many redirects"):
            ui._safe_get("http://example.com/a")


class TestResponseSizeCap:
    def test_declared_content_length_rejected(self):
        resp = FakeResponse(
            200, headers={"Content-Length": str(ui.MAX_RESPONSE_BYTES + 1)}
        )
        with pytest.raises(ValueError, match="size limit"):
            ui._read_capped(resp)
        assert resp.closed

    def test_streamed_overflow_rejected(self, monkeypatch):
        monkeypatch.setattr(ui, "MAX_RESPONSE_BYTES", 16)
        resp = FakeResponse(200, chunks=[b"x" * 8, b"x" * 8, b"x" * 8])  # 24 bytes
        with pytest.raises(ValueError, match="size limit"):
            ui._read_capped(resp)
        assert resp.closed

    def test_small_body_is_loaded(self):
        resp = FakeResponse(200, chunks=[b"hello ", b"world"])
        out = ui._read_capped(resp)
        assert out.content == b"hello world"
