"""
Kick OAuth P0 acceptance tests — from audit section 8.
No real HTTP calls: all Kick endpoints are mocked via httpx_mock.
"""

import time
import pytest

# Patch env before importing module
import os
os.environ.setdefault("KICK_CLIENT_ID",     "01M30PXDY5MAA5JG3Q7267MYT4")
os.environ.setdefault("KICK_CLIENT_SECRET", "73f2c95ee2d593942b336cbe10c6839e81b00cf7fb88ddb8567125efff28fac0")
os.environ.setdefault("KICK_REDIRECT_URI",  "http://localhost:3000/callback")
os.environ.setdefault("KICK_SCOPES",        "user:read channel:read events:subscribe")

from src.kick.oauth import (
    build_authorize_url,
    exchange_code,
    generate_pkce,
    generate_state,
    _pending,
)


# ─── PKCE helpers ─────────────────────────────────────────────────────────────

def test_pkce_s256_length():
    verifier, challenge = generate_pkce()
    assert len(verifier) >= 43, "Verifier must be ≥43 chars (RFC 7636)"
    assert len(challenge) >= 43, "Challenge must be ≥43 chars"


def test_pkce_verifier_challenge_differ():
    verifier, challenge = generate_pkce()
    assert verifier != challenge


def test_state_is_unique():
    s1 = generate_state()
    s2 = generate_state()
    assert s1 != s2
    assert len(s1) >= 32


# ─── build_authorize_url ──────────────────────────────────────────────────────

def test_authorize_url_contains_s256():
    url, state = build_authorize_url()
    assert "code_challenge_method=S256" in url


def test_authorize_url_contains_state():
    url, state = build_authorize_url()
    assert f"state={state}" in url


def test_authorize_url_exact_redirect():
    url, _ = build_authorize_url()
    assert "redirect_uri=http%3A%2F%2Flocalhost%3A3000%2Fcallback" in url


def test_state_stored_in_pending():
    url, state = build_authorize_url()
    assert state in _pending
    assert "verifier" in _pending[state]


# ─── exchange_code — state validation ─────────────────────────────────────────

def test_unknown_state_raises():
    """Audit test: unknown state → rejected."""
    with pytest.raises(ValueError, match="Invalid or expired state"):
        exchange_code("some-code", "UNKNOWN_STATE_XYZ")


def test_expired_state_raises(monkeypatch):
    """Audit test: expired state → rejected."""
    _, state = build_authorize_url()
    # Force expiry
    _pending[state]["expires_at"] = time.time() - 1
    with pytest.raises(ValueError, match="Invalid or expired state"):
        exchange_code("some-code", state)


def test_state_consumed_after_use(monkeypatch):
    """State is one-time — second use raises even with valid code."""
    import httpx

    _, state = build_authorize_url()
    verifier = _pending[state]["verifier"]

    # Mock HTTP response for first exchange
    def mock_post(*args, **kwargs):
        class R:
            status_code = 200
            def raise_for_status(self): pass
            def json(self): return {
                "access_token": "tok",
                "refresh_token": "ref",
                "expires_in": 3600,
            }
        return R()

    monkeypatch.setattr(httpx, "post", mock_post)
    exchange_code("code1", state)  # succeeds, pops state

    # Second call with same state must fail
    with pytest.raises(ValueError, match="Invalid or expired state"):
        exchange_code("code1", state)


def test_wrong_redirect_uri_blocked(monkeypatch):
    """Audit test: wrong redirect URI → Kick token exchange fails → we propagate error."""
    import httpx

    _, state = build_authorize_url()

    class MockResp:
        status_code = 400
        def raise_for_status(self):
            raise httpx.HTTPStatusError("400", request=None, response=self)
        def json(self):
            return {"error": "invalid_redirect_uri"}

    monkeypatch.setattr(httpx, "post", lambda *a, **kw: MockResp())

    with pytest.raises(httpx.HTTPStatusError):
        exchange_code("code", state)
