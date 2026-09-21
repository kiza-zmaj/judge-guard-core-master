"""
Kick Webhook Security — RSA/SHA-256 signature verification.

Kick signature payload format:
    message_id + "." + timestamp + "." + raw_body_bytes

Headers to check:
    Kick-Event-Message-Id
    Kick-Event-Subscription-Id
    Kick-Event-Signature
    Kick-Event-Message-Timestamp
    Kick-Event-Type
    Kick-Event-Version
"""

import base64
import hashlib
import os
import time
import threading
from typing import Optional

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.exceptions import InvalidSignature

# ─── Config ───────────────────────────────────────────────────────────────────
KICK_PUBLIC_KEY_URL = "https://id.kick.com/oauth/public-key"   # adjust if Kick changes this
TIMESTAMP_TOLERANCE = 300   # ±5 minutes
IDEMPOTENCY_TTL     = 600   # 10 minutes cache for message IDs

# ─── Public Key Cache ─────────────────────────────────────────────────────────
_key_cache: dict = {"key": None, "fetched_at": 0.0}
_key_lock = threading.Lock()
KEY_CACHE_TTL = 3600  # refresh every 1 hour


def _fetch_public_key() -> bytes:
    """Download Kick RSA public key (PEM format)."""
    resp = httpx.get(KICK_PUBLIC_KEY_URL, timeout=10)
    resp.raise_for_status()
    # Kick may return JSON { "public_key": "-----BEGIN..." } or raw PEM
    if resp.headers.get("content-type", "").startswith("application/json"):
        return resp.json()["public_key"].encode()
    return resp.content


def get_public_key():
    """Return cached RSA public key object, refreshing if stale."""
    with _key_lock:
        now = time.time()
        if _key_cache["key"] is None or now - _key_cache["fetched_at"] > KEY_CACHE_TTL:
            pem = _fetch_public_key()
            _key_cache["key"] = serialization.load_pem_public_key(pem)
            _key_cache["fetched_at"] = now
        return _key_cache["key"]


# ─── Idempotency Store ────────────────────────────────────────────────────────
_seen_ids: dict[str, float] = {}
_id_lock = threading.Lock()


def _cleanup_seen():
    """Remove expired message IDs."""
    cutoff = time.time() - IDEMPOTENCY_TTL
    expired = [k for k, v in _seen_ids.items() if v < cutoff]
    for k in expired:
        del _seen_ids[k]


def is_duplicate(message_id: str) -> bool:
    """
    Returns True if we've already seen this message ID.
    Atomically records it if new.
    """
    with _id_lock:
        _cleanup_seen()
        if message_id in _seen_ids:
            return True
        _seen_ids[message_id] = time.time()
        return False


# ─── Timestamp Validation ─────────────────────────────────────────────────────

def check_timestamp(timestamp_str: str) -> bool:
    """
    Returns True if timestamp is within ±TIMESTAMP_TOLERANCE of now.
    Kick sends Unix timestamp as string.
    """
    try:
        ts = float(timestamp_str)
    except (ValueError, TypeError):
        return False
    return abs(time.time() - ts) <= TIMESTAMP_TOLERANCE


# ─── Signature Verification ───────────────────────────────────────────────────

def verify_signature(
    raw_body: bytes,
    message_id: str,
    timestamp: str,
    signature_b64: str,
) -> bool:
    """
    Verify Kick RSA/SHA-256 signature.

    Payload = message_id + "." + timestamp + "." + raw_body
    Signature is base64-encoded RSA-PSS or PKCS1v15 over SHA-256 of payload.
    """
    payload = f"{message_id}.{timestamp}.".encode() + raw_body

    try:
        sig_bytes = base64.b64decode(signature_b64)
        pub_key = get_public_key()

        # Try PKCS1v15 first (most common for webhooks), then PSS
        try:
            pub_key.verify(sig_bytes, payload, padding.PKCS1v15(), hashes.SHA256())
            return True
        except InvalidSignature:
            pub_key.verify(
                sig_bytes,
                payload,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                hashes.SHA256(),
            )
            return True
    except (InvalidSignature, Exception):
        return False


# ─── Main Entry Point ─────────────────────────────────────────────────────────

class WebhookError(Exception):
    """Raised when webhook validation fails."""
    pass


def validate_webhook(raw_body: bytes, headers: dict) -> dict:
    """
    Full webhook validation pipeline.
    Returns parsed header dict if valid.
    Raises WebhookError with reason if invalid.

    headers: dict-like with case-insensitive header names.
    """
    def h(name):
        return headers.get(name) or headers.get(name.lower())

    message_id  = h("Kick-Event-Message-Id")
    sub_id      = h("Kick-Event-Subscription-Id")
    signature   = h("Kick-Event-Signature")
    timestamp   = h("Kick-Event-Message-Timestamp")
    event_type  = h("Kick-Event-Type")
    version     = h("Kick-Event-Version")

    # 1. Required headers present
    for name, val in [
        ("Kick-Event-Message-Id",        message_id),
        ("Kick-Event-Signature",         signature),
        ("Kick-Event-Message-Timestamp", timestamp),
        ("Kick-Event-Type",              event_type),
    ]:
        if not val:
            raise WebhookError(f"Missing required header: {name}")

    # 2. Timestamp freshness
    if not check_timestamp(timestamp):
        raise WebhookError("Webhook timestamp outside tolerance window")

    # 3. RSA signature
    if not verify_signature(raw_body, message_id, timestamp, signature):
        raise WebhookError("Invalid RSA signature")

    # 4. Idempotency (after signature — don't record invalid messages)
    if is_duplicate(message_id):
        raise WebhookError(f"Duplicate message ID: {message_id}")

    return {
        "message_id":    message_id,
        "subscription_id": sub_id,
        "event_type":    event_type,
        "version":       version or "1",
        "timestamp":     timestamp,
    }
