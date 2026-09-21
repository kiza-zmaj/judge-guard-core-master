"""
Kick Events — Subscribe, list, and route events.

API host: https://api.kick.com (NOT id.kick.com)
"""

import os
import logging
from typing import Callable, Optional
import httpx

KICK_API_BASE = "https://api.kick.com"
logger = logging.getLogger(__name__)

# Registry of handlers: { (event_type, version): handler_fn }
_handlers: dict[tuple[str, str], Callable] = {}


# ─── Decorator / Registration ─────────────────────────────────────────────────

def on_event(event_type: str, version: str = "1"):
    """Decorator to register an event handler."""
    def decorator(fn: Callable):
        _handlers[(event_type, version)] = fn
        return fn
    return decorator


# ─── HTTP Helper ──────────────────────────────────────────────────────────────

def _kick_post(path: str, access_token: str, json: dict) -> dict:
    resp = httpx.post(
        f"{KICK_API_BASE}{path}",
        json=json,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json() if resp.content else {}


def _kick_get(path: str, access_token: str) -> dict:
    resp = httpx.get(
        f"{KICK_API_BASE}{path}",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def _kick_delete(path: str, access_token: str) -> None:
    httpx.delete(
        f"{KICK_API_BASE}{path}",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )


# ─── Subscription Management ──────────────────────────────────────────────────

def subscribe(
    event_type: str,
    broadcaster_id: str,
    webhook_url: str,
    access_token: str,
    version: str = "1",
) -> dict:
    """
    POST /public/v1/events/subscriptions
    Returns subscription record including subscription_id.
    """
    result = _kick_post(
        "/public/v1/events/subscriptions",
        access_token,
        {
            "type":           event_type,
            "version":        version,
            "broadcaster_id": broadcaster_id,
            "url":            webhook_url,
        },
    )
    logger.info(
        "Subscribed to %s v%s for broadcaster %s → id=%s",
        event_type, version, broadcaster_id, result.get("id"),
    )
    return result


def list_subscriptions(access_token: str) -> list:
    """GET /public/v1/events/subscriptions — for drift reconciliation."""
    result = _kick_get("/public/v1/events/subscriptions", access_token)
    return result.get("data", result) if isinstance(result, dict) else result


def delete_subscription(subscription_id: str, access_token: str) -> None:
    """DELETE a subscription and mark it inactive locally."""
    _kick_delete(f"/public/v1/events/subscriptions/{subscription_id}", access_token)
    logger.info("Deleted subscription %s", subscription_id)


# ─── Event Routing ────────────────────────────────────────────────────────────

def handle_event(meta: dict, payload: dict) -> Optional[dict]:
    """
    Route a validated webhook event to the correct handler.

    meta: dict returned by webhook.validate_webhook()
    payload: parsed JSON body

    Returns handler result or None for unknown events (safe fallback).
    """
    event_type = meta.get("event_type", "")
    version    = meta.get("version", "1")

    handler = _handlers.get((event_type, version))
    if handler is None:
        # Unknown event type — safe fallback, never crash
        logger.warning(
            "Unknown event type=%s version=%s — no handler registered, ignoring.",
            event_type, version,
        )
        return None

    try:
        return handler(meta, payload)
    except Exception:
        logger.exception(
            "Handler for %s v%s raised an exception — event dropped to DLQ.",
            event_type, version,
        )
        return None


# ─── Built-in event handlers (examples) ──────────────────────────────────────

@on_event("chat.message.sent", "1")
def _on_chat_message(meta: dict, payload: dict) -> dict:
    logger.debug("Chat message from %s", payload.get("sender", {}).get("username"))
    return {"status": "processed"}


@on_event("channel.followed", "1")
def _on_channel_follow(meta: dict, payload: dict) -> dict:
    logger.info("New follower: %s", payload.get("follower", {}).get("username"))
    return {"status": "processed"}


@on_event("livestream.status.updated", "1")
def _on_stream_status(meta: dict, payload: dict) -> dict:
    logger.info("Stream status changed: %s", payload.get("is_live"))
    return {"status": "processed"}
