"""
Kick OAuth 2.1 — Authorization Code + PKCE S256

Hosts:
  OAuth:  https://id.kick.com    (authorize, token, revoke)
  API:    https://api.kick.com   (everything else)

NEVER mix these two hosts.
"""

import os
import hashlib
import hmac
import base64
import secrets
import time
from urllib.parse import urlencode
from typing import Optional
import httpx

KICK_AUTHORIZE_URL = "https://id.kick.com/oauth/authorize"
KICK_TOKEN_URL     = "https://id.kick.com/oauth/token"
KICK_REVOKE_URL    = "https://id.kick.com/oauth/revoke"

CLIENT_ID     = os.environ["KICK_CLIENT_ID"]
CLIENT_SECRET = os.environ["KICK_CLIENT_SECRET"]
REDIRECT_URI  = os.environ["KICK_REDIRECT_URI"]
SCOPES        = os.environ.get("KICK_SCOPES", "user:read channel:read events:subscribe")

# In-memory PKCE + state store  (replace with Redis/signed-cookie in prod)
# { state: { verifier, expires_at } }
_pending: dict[str, dict] = {}
_PENDING_TTL = 300  # 5 minutes


# ──────────────────────────────────────────────
# PKCE helpers
# ──────────────────────────────────────────────

def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def generate_pkce() -> tuple[str, str]:
    """Return (code_verifier, code_challenge_S256)."""
    verifier  = _b64url(secrets.token_bytes(48))   # 64-char URL-safe string
    challenge = _b64url(hashlib.sha256(verifier.encode()).digest())
    return verifier, challenge


def generate_state() -> str:
    """Cryptographically secure one-time state token."""
    return secrets.token_urlsafe(32)


# ──────────────────────────────────────────────
# Authorization URL
# ──────────────────────────────────────────────

def build_authorize_url(scopes: Optional[str] = None) -> tuple[str, str]:
    """
    Returns (authorize_url, state).
    Stores verifier+state in _pending for validation at callback.
    """
    state = generate_state()
    verifier, challenge = generate_pkce()

    _pending[state] = {
        "verifier":   verifier,
        "expires_at": time.time() + _PENDING_TTL,
    }

    params = {
        "client_id":             CLIENT_ID,
        "response_type":         "code",
        "redirect_uri":          REDIRECT_URI,
        "scope":                 scopes or SCOPES,
        "state":                 state,
        "code_challenge":        challenge,
        "code_challenge_method": "S256",
    }
    return f"{KICK_AUTHORIZE_URL}?{urlencode(params)}", state


# ──────────────────────────────────────────────
# Callback validation
# ──────────────────────────────────────────────

def _pop_pending(state: str) -> Optional[dict]:
    """Return and remove pending record if valid and not expired."""
    record = _pending.pop(state, None)
    if record is None:
        return None
    if time.time() > record["expires_at"]:
        return None  # expired
    return record


def exchange_code(code: str, state: str) -> dict:
    """
    Exchange authorization code for tokens.
    Raises ValueError on state mismatch / expired / unknown state.
    """
    record = _pop_pending(state)
    if record is None:
        raise ValueError("Invalid or expired state — possible CSRF")

    resp = httpx.post(
        KICK_TOKEN_URL,
        data={
            "grant_type":    "authorization_code",
            "client_id":     CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uri":  REDIRECT_URI,
            "code":          code,
            "code_verifier": record["verifier"],
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=10,
    )
    resp.raise_for_status()
    tokens = resp.json()
    # Never log access_token or refresh_token
    return tokens


# ──────────────────────────────────────────────
# Token lifecycle
# ──────────────────────────────────────────────

def refresh_token(refresh_tok: str) -> dict:
    """Use refresh token to obtain a new access token."""
    resp = httpx.post(
        KICK_TOKEN_URL,
        data={
            "grant_type":    "refresh_token",
            "client_id":     CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "refresh_token": refresh_tok,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def revoke_token(token: str, token_type_hint: str = "access_token") -> None:
    """Revoke a token. Call on disconnect/logout."""
    httpx.post(
        KICK_REVOKE_URL,
        data={
            "client_id":       CLIENT_ID,
            "client_secret":   CLIENT_SECRET,
            "token":           token,
            "token_type_hint": token_type_hint,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=10,
    )
    # Intentionally ignoring errors — best-effort revoke
