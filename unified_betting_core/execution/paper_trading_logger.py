"""
Immutable Append-Only Paper Trading Logger for SharpBet Core (Phase 6).

Maintains an immutable record of all live or simulated betting recommendations,
ensuring an unalterable audit trail before any live capital execution can be authorized.
STRICTLY ENFORCES STAKE = €0.00 WHILE SYSTEM IS IN RESEARCH-ONLY / PAPER TRADING STATUS.
"""

import os
import json
import hashlib
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from unified_betting_core.config import DATA_DIR

PAPER_LOG_FILE = os.path.join(DATA_DIR, "paper_trading_log.jsonl")


class PaperTradingLogger:
    """
    Append-only audit logger for paper trading fixtures and bets.
    """

    def __init__(self, log_path: Optional[str] = None):
        self.log_path = log_path or PAPER_LOG_FILE
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)

    @staticmethod
    def compute_input_hash(data: Dict[str, Any]) -> str:
        """Computes deterministic SHA-256 hash of fixture inputs and odds."""
        serialized = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def log_bet_candidate(
        self,
        event_id: str,
        match: str,
        outcome: str,
        odds: float,
        prediction: Dict[str, float],
        ev_pct: float,
        ece_at_time: float,
        bookmaker: str = "MarketMax",
        model_version: str = "PoissonEngine-v2.0-TempScaled",
        data_status: str = "CACHED",
        rejection_reason: Optional[str] = None,
        is_executable: bool = False,
        raw_input_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Appends an immutable record to the paper trading audit log.
        Forces recommended stake to €0.00 if system has not achieved verified production status.
        """
        now_utc = datetime.now(timezone.utc).isoformat()
        input_hash = self.compute_input_hash(raw_input_data or {
            "event_id": event_id,
            "match": match,
            "outcome": outcome,
            "odds": odds,
            "bookmaker": bookmaker
        })

        # SAFETY LAW: Stake MUST be €0.00 while in Paper Trading / Research-Only mode
        stake_recommended = 0.00

        entry = {
            "timestamp": now_utc,
            "model_version": model_version,
            "input_hash": input_hash,
            "event_id": event_id,
            "match": match,
            "outcome": outcome,
            "bookmaker": bookmaker,
            "odds": round(odds, 3),
            "prediction": prediction,
            "ece_at_time": round(ece_at_time, 2) if ece_at_time is not None else None,
            "ev_pct": round(ev_pct, 2) if ev_pct is not None else None,
            "stake_recommended": stake_recommended,
            "operational_mode": "PAPER_TRADING_RESEARCH_ONLY",
            "data_status": data_status,
            "is_executable": is_executable,
            "rejection_reason": rejection_reason,
            "settled": False,
            "actual_result": None,
            "closing_odds": None,
            "realized_clv": None,
            "realized_pnl": None
        }

        # Append to jsonl
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

        return entry

    def read_all_logs(self) -> List[Dict[str, Any]]:
        """Reads all historical paper trading entries."""
        if not os.path.exists(self.log_path):
            return []
        entries = []
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return entries

    def get_summary(self) -> Dict[str, Any]:
        """Summarizes current paper trading audit trail."""
        logs = self.read_all_logs()
        total = len(logs)
        settled = sum(1 for l in logs if l.get("settled"))
        return {
            "log_path": self.log_path,
            "total_records": total,
            "settled_records": settled,
            "pending_records": total - settled,
            "operational_status": "RESEARCH_ONLY_PAPER_TRADING",
            "stake_limit_eur": 0.00
        }
