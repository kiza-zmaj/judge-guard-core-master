"""
SharpBet Telemetry & Observability Engine (PostHog Integration)
Phase: Paper Trading & Live Monitoring
"""

import json
import logging
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger("sharpbet.telemetry")

# PostHog Cloud EU configuration
DEFAULT_POSTHOG_KEY = "phc_vbsn9vggTFgeQNkSgNiWC2h9926sK3tHT2ZvWXZA2JJY"
DEFAULT_POSTHOG_HOST = "https://eu.i.posthog.com"

POSTHOG_API_KEY = os.environ.get("POSTHOG_API_KEY", DEFAULT_POSTHOG_KEY)
POSTHOG_HOST = os.environ.get("POSTHOG_HOST", DEFAULT_POSTHOG_HOST)
DISTINCT_ID = "sharpbet_core_paper_trader"


import atexit
from concurrent.futures import ThreadPoolExecutor

_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="sharpbet_telemetry")
atexit.register(lambda: _EXECUTOR.shutdown(wait=True, cancel_futures=False))


def _send_payload(payload: Dict[str, Any], timeout: float = 4.0) -> None:
    """Dispatches telemetry payload to PostHog endpoint."""
    try:
        url = f"{POSTHOG_HOST.rstrip('/')}/capture/"
        resp = requests.post(url, json=payload, timeout=timeout)
        if resp.status_code != 200:
            logger.warning("PostHog telemetry capture returned status %s: %s", resp.status_code, resp.text)
    except Exception as exc:
        logger.debug("PostHog telemetry send failed silently: %s", exc)


def emit_telemetry_event(
    event_name: str,
    properties: Dict[str, Any],
    distinct_id: str = DISTINCT_ID,
    sync: bool = False,
) -> bool:
    """
    Emits an event to PostHog with resilient error handling.
    Queued in persistent thread pool or executed synchronously.
    """
    payload = {
        "api_key": POSTHOG_API_KEY,
        "event": event_name,
        "distinct_id": distinct_id,
        "properties": {
            **properties,
            "$lib": "sharpbet_telemetry",
            "environment": os.environ.get("SHARPBET_ENV", "PAPER_TRADING"),
            "system_timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }

    if sync:
        _send_payload(payload)
    else:
        _EXECUTOR.submit(_send_payload, payload)
    return True


def track_odds_ingestion(
    match_id: str,
    league: str,
    home_team: str,
    away_team: str,
    odds_source: str,
    odds_dict: Dict[str, float],
) -> None:
    """Tracks raw or proxy bookmaker odds ingestion."""
    emit_telemetry_event(
        "sharpbet_odds_ingestion",
        {
            "match_id": match_id,
            "league": league,
            "home_team": home_team,
            "away_team": away_team,
            "odds_source": odds_source,
            "odds": odds_dict,
        },
    )


def track_model_inference(
    match_id: str,
    league: str,
    home_team: str,
    away_team: str,
    model_version: str,
    alpha_h: float,
    beta_a: float,
    lambda_ht_home: float,
    lambda_ht_away: float,
    prob_ht_draw: float,
    prob_ht_over05: float,
    prob_ht_over15: float,
) -> None:
    """Tracks Dixon-Coles model inference probabilities for halftime markets."""
    emit_telemetry_event(
        "sharpbet_model_inference",
        {
            "match_id": match_id,
            "league": league,
            "home_team": home_team,
            "away_team": away_team,
            "model_version": model_version,
            "alpha_h": round(alpha_h, 4),
            "beta_a": round(beta_a, 4),
            "lambda_ht_home": round(lambda_ht_home, 4),
            "lambda_ht_away": round(lambda_ht_away, 4),
            "prob_ht_draw": round(prob_ht_draw, 4),
            "prob_ht_over05": round(prob_ht_over05, 4),
            "prob_ht_over15": round(prob_ht_over15, 4),
        },
    )


def track_paper_bet_logged(entry: Dict[str, Any]) -> None:
    """Tracks a paper bet recommendation added to the immutable audit trail."""
    emit_telemetry_event(
        "sharpbet_paper_bet_logged",
        {
            "event_id": entry.get("event_id"),
            "match": entry.get("match"),
            "outcome": entry.get("outcome"),
            "bookmaker": entry.get("bookmaker"),
            "odds": entry.get("odds"),
            "ev_pct": entry.get("ev_pct"),
            "ece_at_time": entry.get("ece_at_time"),
            "stake_recommended": entry.get("stake_recommended", 0.0),
            "operational_mode": entry.get("operational_mode", "PAPER_TRADING_RESEARCH_ONLY"),
            "data_status": entry.get("data_status"),
            "input_hash": entry.get("input_hash"),
        },
    )


def track_match_settlement(
    event_id: str,
    match: str,
    outcome: str,
    odds: float,
    actual_result: str,
    won: bool,
    realized_pnl: float,
    closing_odds: Optional[float] = None,
    realized_clv: Optional[float] = None,
) -> None:
    """Tracks settlement of a paper bet with closing line value evaluation."""
    emit_telemetry_event(
        "sharpbet_match_settled",
        {
            "event_id": event_id,
            "match": match,
            "outcome": outcome,
            "entry_odds": odds,
            "actual_result": actual_result,
            "won": won,
            "realized_pnl": round(realized_pnl, 4),
            "closing_odds": round(closing_odds, 3) if closing_odds else None,
            "realized_clv": round(realized_clv, 4) if realized_clv is not None else None,
        },
    )


def track_gate_verdict(
    gate: str,
    verdict: str,
    metrics: Dict[str, Any],
) -> None:
    """Tracks system gate evaluations (Gate 0, Gate A, Gate B)."""
    emit_telemetry_event(
        "sharpbet_gate_verdict",
        {
            "gate": gate,
            "verdict": verdict,
            **metrics,
        },
        sync=True,  # Critical system gates sync immediately
    )
