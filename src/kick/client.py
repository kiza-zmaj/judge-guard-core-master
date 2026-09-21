"""
Kick REST API Client — wraps https://api.kick.com endpoints.

IMPORTANT: All API calls go to api.kick.com, NOT id.kick.com.
id.kick.com is OAuth-only (authorize / token / revoke).
"""

import os
import time
import threading
import logging
from typing import Optional
import httpx

from . import oauth

KICK_API_BASE = "https://api.kick.com"
logger = logging.getLogger(__name__)


class KickClient:
    """
    Authenticated Kick API client with automatic token refresh.

    Usage:
        client = KickClient(access_token, refresh_token)
        user = client.get_user()
    """

    def __init__(self, access_token: str, refresh_token: Optional[str] = None, expires_at: float = 0.0):
        self._access_token  = access_token
        self._refresh_token = refresh_token
        self._expires_at    = expires_at
        self._lock          = threading.Lock()

    def _maybe_refresh(self):
        """Refresh access token if it expires within 60 seconds."""
        if self._refresh_token and self._expires_at and time.time() >= self._expires_at - 60:
            with self._lock:
                if time.time() >= self._expires_at - 60:  # double-check inside lock
                    tokens = oauth.refresh_token(self._refresh_token)
                    self._access_token  = tokens["access_token"]
                    self._refresh_token = tokens.get("refresh_token", self._refresh_token)
                    self._expires_at    = time.time() + tokens.get("expires_in", 3600)
                    logger.info("Kick access token refreshed successfully.")

    def _headers(self) -> dict:
        self._maybe_refresh()
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Accept":        "application/json",
        }

    def _get(self, path: str, **kwargs) -> dict:
        resp = httpx.get(f"{KICK_API_BASE}{path}", headers=self._headers(), timeout=10, **kwargs)
        resp.raise_for_status()
        return resp.json()

    def _patch(self, path: str, json: dict) -> dict:
        resp = httpx.patch(f"{KICK_API_BASE}{path}", json=json, headers=self._headers(), timeout=10)
        resp.raise_for_status()
        return resp.json() if resp.content else {}

    # ─── User ───────────────────────────────────────────────────────────────

    def get_user(self) -> dict:
        """GET /public/v1/user — requires user:read scope."""
        return self._get("/public/v1/user")

    # ─── Channel ────────────────────────────────────────────────────────────

    def get_channel(self, broadcaster_id: str) -> dict:
        """GET /public/v1/channels/{id} — requires channel:read scope."""
        return self._get(f"/public/v1/channels/{broadcaster_id}")

    def update_channel(self, broadcaster_id: str, **fields) -> dict:
        """PATCH /public/v1/channels/{id} — requires channel:write scope."""
        return self._patch(f"/public/v1/channels/{broadcaster_id}", json=fields)

    # ─── Channel Rewards ────────────────────────────────────────────────────

    def get_rewards(self, broadcaster_id: str) -> dict:
        """GET channel rewards — requires channel:rewards:read scope."""
        return self._get(f"/public/v1/channels/{broadcaster_id}/rewards")

    # ─── Kicks Leaderboard ──────────────────────────────────────────────────

    def get_kicks_leaderboard(self, broadcaster_id: str) -> dict:
        """Requires kicks:read scope."""
        return self._get(f"/public/v1/channels/{broadcaster_id}/kicks/leaderboard")

    # ─── Ads ────────────────────────────────────────────────────────────────

    def get_ads(self, broadcaster_id: str) -> dict:
        """Requires ads:read scope."""
        return self._get(f"/public/v1/channels/{broadcaster_id}/ads")

    @classmethod
    def from_token_response(cls, token_response: dict) -> "KickClient":
        """Convenience constructor from OAuth token exchange response."""
        return cls(
            access_token  = token_response["access_token"],
            refresh_token = token_response.get("refresh_token"),
            expires_at    = time.time() + token_response.get("expires_in", 3600),
        )
