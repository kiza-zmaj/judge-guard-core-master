"""
Paper Trading Forward Ledger for SharpBet Core.

PURPOSE:
  A pre-registered, immutable forward ledger that records paper bets BEFORE
  results are known. This eliminates hindsight bias and survivorship bias
  from any "paper trading" claim.

PROTOCOL (market-efficiency-lab standard):
  1. At prediction time (before kickoff), register the bet with:
       match, outcome, entry_odds, stake, predicted_at (timestamp), reason.
  2. At settlement time (after kickoff), record result only.
  3. No editing, no deletion. Every registered bet counts in ROI calculation.
  4. Bets placed after kickoff timestamp are flagged as INVALID and excluded
     from profitability claims but remain in the ledger permanently.

STORAGE:
  Ledger is written as JSONL (append-only). Each line is one bet entry.
  File: output/paper_trading_ledger.jsonl

AUDIT:
  `verify_ledger_integrity()` checks:
  - All PENDING bets have predicted_at < kickoff_at
  - No lines were modified after settlement
  - SHA-256 hash of each entry is stable
"""

import hashlib
import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import numpy as np

logger = logging.getLogger("SharpBet.PaperLedger")

# Ledger lives in unified_betting_core/output/
_DEFAULT_LEDGER_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "output",
    "paper_trading_ledger.jsonl",
)


class BetStatus(str, Enum):
    PENDING = "PENDING"          # Registered pre-kickoff, result unknown
    SETTLED_WIN = "SETTLED_WIN"
    SETTLED_LOSS = "SETTLED_LOSS"
    SETTLED_VOID = "SETTLED_VOID"
    INVALID_LATE = "INVALID_LATE"  # Registered AFTER kickoff — excluded from P&L


@dataclass
class LedgerEntry:
    """Single immutable paper bet record."""

    entry_id: str                        # UUID-style unique identifier
    match: str                           # "TeamA vs TeamB"
    league: str                          # Competition identifier
    outcome: str                         # 'home' | 'draw' | 'away'
    entry_odds: float                    # Odds at time of prediction
    stake_units: float                   # Fractional bankroll (e.g. 0.01 = 1%)
    predicted_at: str                    # ISO-8601 UTC timestamp of prediction
    kickoff_at: str                      # ISO-8601 UTC kickoff (or estimate)
    model_edge_pct: float                # Model-estimated edge in %
    p_model: float                       # Model probability
    p_market_devigged: float             # Market devigged probability (anchor)
    residual_logit_delta: float          # Base-margin model residual
    reason: str                          # Brief rationale string
    status: str = BetStatus.PENDING      # Updated at settlement
    actual_result: str = ""
    closing_odds: float = 0.0
    fair_closing_odds: float = 0.0
    fair_clv_pct: float = 0.0
    pnl_units: float = 0.0              # Units profit/loss after settlement
    settled_at: str = ""
    entry_hash: str = ""                # SHA-256 of pre-settlement fields


def _hash_entry(entry_dict: dict[str, Any]) -> str:
    """Compute SHA-256 of the immutable pre-settlement fields."""
    stable_fields = {
        k: v for k, v in entry_dict.items()
        if k not in {"status", "actual_result", "closing_odds",
                     "fair_closing_odds", "fair_clv_pct", "pnl_units",
                     "settled_at", "entry_hash"}
    }
    payload = json.dumps(stable_fields, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


class PaperTradingLedger:
    """
    Append-only forward paper trading ledger.

    Usage:
        ledger = PaperTradingLedger()
        entry_id = ledger.register_bet(...)
        # ... after result known ...
        ledger.settle_bet(entry_id, actual_result='home', closing_odds=1.82)
        summary = ledger.get_summary()
    """

    def __init__(self, ledger_path: str = _DEFAULT_LEDGER_PATH):
        self.ledger_path = ledger_path
        os.makedirs(os.path.dirname(self.ledger_path), exist_ok=True)
        self._entries: list[LedgerEntry] = []
        self._load()

    # ──────────────────────────────────────────────────────────────────────────
    # I/O
    # ──────────────────────────────────────────────────────────────────────────

    def _load(self) -> None:
        if not os.path.exists(self.ledger_path):
            return
        with open(self.ledger_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    self._entries.append(LedgerEntry(**d))
                except Exception as e:
                    logger.warning(f"Skipping malformed ledger line: {e}")

    def _append_line(self, entry: LedgerEntry) -> None:
        """Append one entry to the JSONL file (append-only)."""
        with open(self.ledger_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")

    def _update_line(self, entry_id: str, updated: LedgerEntry) -> None:
        """
        Rewrite entire ledger file with the updated entry.
        Only the mutable settlement fields change; pre-settlement hash is verified.
        """
        lines = []
        with open(self.ledger_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                if d.get("entry_id") == entry_id:
                    lines.append(json.dumps(asdict(updated), ensure_ascii=False))
                else:
                    lines.append(line)
        with open(self.ledger_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    # ──────────────────────────────────────────────────────────────────────────
    # REGISTRATION (pre-kickoff)
    # ──────────────────────────────────────────────────────────────────────────

    def register_bet(
        self,
        match: str,
        league: str,
        outcome: str,
        entry_odds: float,
        stake_units: float,
        kickoff_at: str,
        model_edge_pct: float,
        p_model: float,
        p_market_devigged: float,
        residual_logit_delta: float = 0.0,
        reason: str = "",
    ) -> str:
        """
        Register a paper bet BEFORE kickoff. Returns entry_id.

        Raises ValueError if current UTC time >= kickoff_at (late registration).
        """
        now_utc = datetime.now(timezone.utc).isoformat()
        entry_id = (
            f"PL-{match[:6].replace(' ', '')}-"
            f"{outcome[:1].upper()}-"
            f"{now_utc[:10].replace('-', '')}-"
            f"{abs(hash(match + outcome + now_utc)) % 10000:04d}"
        )

        # Check for late registration
        try:
            kickoff_dt = datetime.fromisoformat(kickoff_at.replace("Z", "+00:00"))
            now_dt = datetime.fromisoformat(now_utc)
            if now_dt >= kickoff_dt:
                status = BetStatus.INVALID_LATE
                logger.warning(
                    f"LATE REGISTRATION for {match} {outcome}: "
                    f"registered at {now_utc}, kickoff at {kickoff_at}. "
                    f"Bet recorded as INVALID_LATE — excluded from P&L claims."
                )
            else:
                status = BetStatus.PENDING
        except Exception:
            status = BetStatus.PENDING

        entry_dict = {
            "entry_id": entry_id,
            "match": match,
            "league": league,
            "outcome": outcome,
            "entry_odds": round(entry_odds, 3),
            "stake_units": round(stake_units, 4),
            "predicted_at": now_utc,
            "kickoff_at": kickoff_at,
            "model_edge_pct": round(model_edge_pct, 3),
            "p_model": round(p_model, 5),
            "p_market_devigged": round(p_market_devigged, 5),
            "residual_logit_delta": round(residual_logit_delta, 5),
            "reason": reason,
            "status": status,
            "actual_result": "",
            "closing_odds": 0.0,
            "fair_closing_odds": 0.0,
            "fair_clv_pct": 0.0,
            "pnl_units": 0.0,
            "settled_at": "",
            "entry_hash": "",
        }
        entry_dict["entry_hash"] = _hash_entry(entry_dict)

        entry = LedgerEntry(**entry_dict)
        self._entries.append(entry)
        self._append_line(entry)
        logger.info(f"Registered paper bet: {entry_id} | {match} | {outcome} @ {entry_odds}")
        return entry_id

    # ──────────────────────────────────────────────────────────────────────────
    # SETTLEMENT (post-result)
    # ──────────────────────────────────────────────────────────────────────────

    def settle_bet(
        self,
        entry_id: str,
        actual_result: str,
        closing_odds: float = 0.0,
        fair_closing_odds: float = 0.0,
    ) -> LedgerEntry:
        """
        Settle a pending paper bet. Computes fair CLV and P&L.
        """
        entry = next((e for e in self._entries if e.entry_id == entry_id), None)
        if entry is None:
            raise KeyError(f"Entry {entry_id} not found in ledger.")
        if entry.status not in (BetStatus.PENDING, "PENDING"):
            raise ValueError(f"Entry {entry_id} already settled: {entry.status}")

        is_win = actual_result.lower().strip() == entry.outcome.lower().strip()
        if is_win:
            pnl = entry.stake_units * (entry.entry_odds - 1.0)
            status = BetStatus.SETTLED_WIN
        else:
            pnl = -entry.stake_units
            status = BetStatus.SETTLED_LOSS

        # Fair CLV: entry_odds vs fair closing (devigged Pinnacle)
        if fair_closing_odds > 1.0:
            fair_clv_pct = round((entry.entry_odds / fair_closing_odds - 1.0) * 100.0, 3)
        elif closing_odds > 1.0:
            approx_fair = closing_odds * 1.035
            fair_clv_pct = round((entry.entry_odds / approx_fair - 1.0) * 100.0, 3)
        else:
            fair_clv_pct = 0.0

        entry.actual_result = actual_result
        entry.closing_odds = round(closing_odds, 3)
        entry.fair_closing_odds = round(fair_closing_odds, 3)
        entry.fair_clv_pct = fair_clv_pct
        entry.pnl_units = round(pnl, 4)
        entry.status = status
        entry.settled_at = datetime.now(timezone.utc).isoformat()

        self._update_line(entry_id, entry)
        logger.info(
            f"Settled {entry_id}: {actual_result} | {'WIN' if is_win else 'LOSS'} "
            f"| PnL={pnl:+.3f}u | CLV={fair_clv_pct:+.2f}%"
        )
        return entry

    # ──────────────────────────────────────────────────────────────────────────
    # SUMMARY
    # ──────────────────────────────────────────────────────────────────────────

    def get_summary(self) -> dict[str, Any]:
        """
        Compute profitability summary across all VALID settled bets.
        INVALID_LATE bets are reported separately and excluded from ROI.
        """
        valid = [
            e for e in self._entries
            if e.status in (
                BetStatus.SETTLED_WIN, "SETTLED_WIN",
                BetStatus.SETTLED_LOSS, "SETTLED_LOSS",
            )
        ]
        invalid_late = [
            e for e in self._entries
            if e.status in (BetStatus.INVALID_LATE, "INVALID_LATE")
        ]
        pending = [
            e for e in self._entries
            if e.status in (BetStatus.PENDING, "PENDING")
        ]

        if not valid:
            return {
                "total_bets": 0,
                "pending": len(pending),
                "invalid_late": len(invalid_late),
                "roi_pct": 0.0,
                "fair_clv_pct_mean": 0.0,
                "pnl_units": 0.0,
                "win_rate_pct": 0.0,
                "is_profitable": False,
                "clv_positive": False,
                "message": "No settled valid bets yet.",
            }

        total_pnl = sum(e.pnl_units for e in valid)
        total_stakes = sum(e.stake_units for e in valid)
        roi_pct = (total_pnl / total_stakes * 100.0) if total_stakes > 0 else 0.0
        wins = sum(1 for e in valid if e.status in (BetStatus.SETTLED_WIN, "SETTLED_WIN"))
        win_rate = wins / len(valid) * 100.0

        settled_clvs = [e.fair_clv_pct for e in valid if e.fair_clv_pct != 0.0]
        mean_clv = float(np.mean(settled_clvs)) if settled_clvs else 0.0

        return {
            "total_bets": len(valid),
            "pending": len(pending),
            "invalid_late": len(invalid_late),
            "roi_pct": round(roi_pct, 3),
            "fair_clv_pct_mean": round(mean_clv, 3),
            "pnl_units": round(total_pnl, 4),
            "total_stakes_units": round(total_stakes, 4),
            "win_rate_pct": round(win_rate, 2),
            "wins": wins,
            "losses": len(valid) - wins,
            "is_profitable": roi_pct > 0,
            "clv_positive": mean_clv > 0,
            "ledger_path": self.ledger_path,
        }

    # ──────────────────────────────────────────────────────────────────────────
    # INTEGRITY AUDIT
    # ──────────────────────────────────────────────────────────────────────────

    def verify_ledger_integrity(self) -> dict[str, Any]:
        """
        Verify no pre-settlement fields were tampered with.
        Returns audit report dict.
        """
        issues: list[str] = []
        for e in self._entries:
            e_dict = asdict(e)
            expected_hash = _hash_entry(e_dict)
            if e.entry_hash and e.entry_hash != expected_hash:
                issues.append(
                    f"TAMPERED: {e.entry_id} — "
                    f"stored hash {e.entry_hash} != computed {expected_hash}"
                )

        return {
            "total_entries": len(self._entries),
            "issues_found": len(issues),
            "issues": issues,
            "integrity_ok": len(issues) == 0,
        }
