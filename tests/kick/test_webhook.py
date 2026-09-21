"""
Kick Webhook P0 acceptance tests — from audit section 8.
Uses real RSA key fixtures so tests don't hit the network.
"""

import base64
import hashlib
import json
import os
import time

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.backends import default_backend

os.environ.setdefault("KICK_CLIENT_ID",     "01M30PXDY5MAA5JG3Q7267MYT4")
os.environ.setdefault("KICK_CLIENT_SECRET", "73f2c95ee2d593942b336cbe10c6839e81b00cf7fb88ddb8567125efff28fac0")
os.environ.setdefault("KICK_REDIRECT_URI",  "http://localhost:3000/callback")

from src.kick.webhook import (
    validate_webhook,
    check_timestamp,
    is_duplicate,
    WebhookError,
    _key_cache,
    _seen_ids,
)


# ─── RSA Test Fixture ─────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def rsa_key_fixture():
    """Generate a fresh RSA key pair and inject it into the key cache."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend(),
    )
    public_key = private_key.public_key()
    _key_cache["key"] = public_key
    _key_cache["fetched_at"] = time.time()
    _seen_ids.clear()
    return private_key


def _sign(private_key, message_id: str, timestamp: str, raw_body: bytes) -> str:
    """Sign the Kick payload format and return base64 signature."""
    payload = f"{message_id}.{timestamp}.".encode() + raw_body
    sig = private_key.sign(payload, padding.PKCS1v15(), hashes.SHA256())
    return base64.b64encode(sig).decode()


def _make_headers(private_key, raw_body: bytes, message_id: str = None, timestamp: str = None) -> dict:
    message_id = message_id or "msg-001"
    timestamp  = timestamp  or str(int(time.time()))
    sig        = _sign(private_key, message_id, timestamp, raw_body)
    return {
        "Kick-Event-Message-Id":        message_id,
        "Kick-Event-Subscription-Id":   "sub-001",
        "Kick-Event-Signature":         sig,
        "Kick-Event-Message-Timestamp": timestamp,
        "Kick-Event-Type":              "chat.message.sent",
        "Kick-Event-Version":           "1",
    }


# ─── Valid webhook ─────────────────────────────────────────────────────────────

def test_valid_webhook_passes(rsa_key_fixture):
    raw_body = b'{"event": "test"}'
    headers  = _make_headers(rsa_key_fixture, raw_body)
    meta     = validate_webhook(raw_body, headers)
    assert meta["event_type"] == "chat.message.sent"


# ─── Audit: one changed byte → signature fails ─────────────────────────────────

def test_modified_body_rejected(rsa_key_fixture):
    """Audit test: izmenjen jedan bajt raw body → signature verification pada."""
    raw_body = b'{"event": "test"}'
    headers  = _make_headers(rsa_key_fixture, raw_body)
    tampered = b'{"event": "TAMPERED"}'
    with pytest.raises(WebhookError, match="Invalid RSA signature"):
        validate_webhook(tampered, headers)


# ─── Audit: duplicate message ID → idempotent ─────────────────────────────────

def test_duplicate_message_id_rejected(rsa_key_fixture):
    """Audit test: dupliran isti message ID → side effect jednom."""
    raw_body   = b'{"event": "test"}'
    message_id = "unique-msg-123"
    headers    = _make_headers(rsa_key_fixture, raw_body, message_id=message_id)

    # First call: OK
    validate_webhook(raw_body, headers)

    # Second call: same message_id → rejected
    raw_body2   = b'{"event": "test2"}'
    headers2    = _make_headers(rsa_key_fixture, raw_body2, message_id=message_id)
    with pytest.raises(WebhookError, match="Duplicate message ID"):
        validate_webhook(raw_body2, headers2)


# ─── Audit: old timestamp → rejected ─────────────────────────────────────────

def test_old_timestamp_rejected(rsa_key_fixture):
    """Audit test: stari timestamp → webhook odbijen."""
    raw_body  = b'{"event": "test"}'
    old_ts    = str(int(time.time()) - 400)  # 400 seconds ago > 300s tolerance
    headers   = _make_headers(rsa_key_fixture, raw_body, message_id="old-msg", timestamp=old_ts)
    with pytest.raises(WebhookError, match="timestamp outside tolerance"):
        validate_webhook(raw_body, headers)


# ─── Audit: future timestamp → rejected ───────────────────────────────────────

def test_future_timestamp_rejected(rsa_key_fixture):
    raw_body  = b'{"event": "test"}'
    future_ts = str(int(time.time()) + 400)
    headers   = _make_headers(rsa_key_fixture, raw_body, message_id="future-msg", timestamp=future_ts)
    with pytest.raises(WebhookError, match="timestamp outside tolerance"):
        validate_webhook(raw_body, headers)


# ─── Missing required headers ─────────────────────────────────────────────────

def test_missing_signature_header_rejected(rsa_key_fixture):
    raw_body = b'{"event": "test"}'
    headers  = _make_headers(rsa_key_fixture, raw_body)
    del headers["Kick-Event-Signature"]
    with pytest.raises(WebhookError, match="Missing required header"):
        validate_webhook(raw_body, headers)


def test_missing_message_id_rejected(rsa_key_fixture):
    raw_body = b'{"event": "test"}'
    headers  = _make_headers(rsa_key_fixture, raw_body)
    del headers["Kick-Event-Message-Id"]
    with pytest.raises(WebhookError, match="Missing required header"):
        validate_webhook(raw_body, headers)


# ─── Timestamp helper ─────────────────────────────────────────────────────────

def test_timestamp_within_window():
    assert check_timestamp(str(int(time.time()))) is True
    assert check_timestamp(str(int(time.time()) - 100)) is True


def test_timestamp_outside_window():
    assert check_timestamp(str(int(time.time()) - 400)) is False
    assert check_timestamp("not-a-number") is False


# ─── Unknown event type: safe fallback (events module) ───────────────────────

def test_unknown_event_type_safe_fallback():
    """Audit test: nepoznat event type → bezbedan rezultat, bez pada."""
    from src.kick import events
    meta    = {"event_type": "unknown.event.xyz", "version": "99"}
    payload = {"data": "something"}
    result  = events.handle_event(meta, payload)
    assert result is None  # safe None, not an exception
