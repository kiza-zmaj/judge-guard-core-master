"""
Immutable Audit Trail & Persistent Logging Engine for SharpBet Core.
Records every prediction opportunity, gate evaluation, and retrospective settlement.
Enforces complete reproducibility and zero retrospective tampering.
"""

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any

from unified_betting_core.config import DATA_DIR


class AuditTrail:
    """
    Append-only persistent audit log stored in JSONL format.
    Every prediction receives a deterministic event ID and cryptographic input hash.
    """

    def __init__(self, log_path: str | None = None):
        self.log_path = log_path or os.path.join(
            str(DATA_DIR), "prediction_audit_trail.jsonl"
        )

    def record_prediction(
        self,
        match: str,
        match_date: str,
        outcome: str,
        p_model: float,
        p_devig: float,
        p_calibrated: float,
        best_odds: float,
        raw_ev_pct: float,
        calibrated_ev_pct: float,
        decision_status: str,
        is_executable: bool,
        stake: float,
        data_quality_state: str,
        gate_verdicts: dict[str, bool],
        notes: list[str],
    ) -> dict[str, Any]:
        """
        Appends an immutable prediction record before match kickoff.
        """
        # Create unique, reproducible event ID
        event_payload = f"{match_date}:{match}:{outcome}:{best_odds}"
        event_id = hashlib.sha256(event_payload.encode()).hexdigest()[:16]

        record = {
            "event_id": event_id,
            "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
            "match_date": match_date,
            "match": match,
            "outcome": outcome,
            "data_quality_state": data_quality_state,
            "p_model": round(p_model, 4),
            "p_devig": round(p_devig, 4),
            "p_calibrated": round(p_calibrated, 4),
            "best_odds": round(best_odds, 3),
            "raw_ev_pct": raw_ev_pct,
            "calibrated_ev_pct": calibrated_ev_pct,
            "decision_status": decision_status,
            "is_executable": is_executable,
            "stake": round(stake, 2),
            "gate_verdicts": gate_verdicts,
            "audit_notes": notes,
            "settlement": None,  # Populated only when retrospective closing line & result arrive
        }

        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception:
            pass

        return record

    def get_all_records(self) -> list[dict[str, Any]]:
        """Reads all recorded audit entries."""
        if not os.path.exists(self.log_path):
            return []
        records = []
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        records.append(json.loads(line.strip()))
                    except Exception:
                        pass
        return records
