"""
Antigravity Telemetry System.
Tracks per-call LLM latency, token counts, model id, prompt version,
cost estimates, and persists telemetry to SQLite research.db (P1-8 compliant).
Supports Bolt, Jules, Antigravity, and JudgeGuard agent telemetry.
"""

import os
import time
import sqlite3
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "research.db")

# Approximate Gemini & Gemma token cost rates (per million tokens) in USD
COST_PER_MILLION = {
    "gemini-3.8-flash": {"prompt": 0.15, "completion": 0.60},
    "gemini-3.7-flash": {"prompt": 0.10, "completion": 0.40},
    "gemini-2.5-flash": {"prompt": 0.075, "completion": 0.30},
    "gemma4:31b": {"prompt": 0.00, "completion": 0.00}, # Local/Cloud Ollama
    "default": {"prompt": 0.10, "completion": 0.40},
}


def _init_telemetry_table(conn: sqlite3.Connection):
    """Ensures telemetry schema exists in SQLite."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            agent TEXT NOT NULL,
            action TEXT NOT NULL,
            model TEXT NOT NULL,
            prompt_tokens INTEGER DEFAULT 0,
            completion_tokens INTEGER DEFAULT 0,
            total_tokens INTEGER DEFAULT 0,
            cached_tokens INTEGER DEFAULT 0,
            tokens_saved INTEGER DEFAULT 0,
            latency_ms REAL DEFAULT 0.0,
            cost_estimate_usd REAL DEFAULT 0.0,
            status TEXT DEFAULT 'SUCCESS',
            git_sha TEXT DEFAULT '',
            details TEXT DEFAULT ''
        )
    """)
    conn.commit()


def calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Calculates approximate cost in USD for the token usage."""
    rates = COST_PER_MILLION.get(model, COST_PER_MILLION["default"])
    cost = (prompt_tokens / 1_000_000.0) * rates["prompt"] + \
           (completion_tokens / 1_000_000.0) * rates["completion"]
    return round(cost, 6)


class TelemetryTracker:
    """
    Singleton-style telemetry manager for tracking LLM token metrics,
    latency, and agent operation telemetry.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DB_PATH
        self._ensure_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_db(self):
        try:
            with self._get_connection() as conn:
                _init_telemetry_table(conn)
        except Exception as e:
            logger.warning(f"Could not initialize telemetry table: {e}")

    def record_call(
        self,
        agent: str,
        action: str,
        model: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: int = 0,
        cached_tokens: int = 0,
        tokens_saved: int = 0,
        latency_ms: float = 0.0,
        status: str = "SUCCESS",
        git_sha: str = "",
        details: str = "",
    ) -> Dict[str, Any]:
        """
        Records an LLM call or agent task execution telemetry record.
        """
        if total_tokens == 0:
            total_tokens = prompt_tokens + completion_tokens

        cost = calculate_cost(model, prompt_tokens, completion_tokens)

        try:
            with self._get_connection() as conn:
                _init_telemetry_table(conn)
                conn.execute("""
                    INSERT INTO telemetry (
                        agent, action, model, prompt_tokens, completion_tokens,
                        total_tokens, cached_tokens, tokens_saved, latency_ms,
                        cost_estimate_usd, status, git_sha, details
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    agent, action, model, prompt_tokens, completion_tokens,
                    total_tokens, cached_tokens, tokens_saved, latency_ms,
                    cost, status, git_sha, details
                ))
                conn.commit()
        except Exception as e:
            logger.warning(f"Telemetry logging error: {e}")

        record = {
            "agent": agent,
            "action": action,
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "cached_tokens": cached_tokens,
            "tokens_saved": tokens_saved,
            "latency_ms": latency_ms,
            "cost_estimate_usd": cost,
            "status": status,
            "git_sha": git_sha,
        }
        logger.info(
            f"📊 [TELEMETRY] agent={agent} model={model} tokens={total_tokens} (saved={tokens_saved}) "
            f"latency={latency_ms:.1f}ms cost=${cost:.5f}"
        )
        return record

    def get_summary(self, limit: int = 100) -> Dict[str, Any]:
        """Returns aggregated telemetry statistics across all agents."""
        try:
            with self._get_connection() as conn:
                _init_telemetry_table(conn)
                cursor = conn.cursor()
                
                # Totals
                row = cursor.execute("""
                    SELECT 
                        COUNT(*) as total_calls,
                        SUM(total_tokens) as sum_tokens,
                        SUM(tokens_saved) as sum_saved,
                        SUM(cached_tokens) as sum_cached,
                        AVG(latency_ms) as avg_latency,
                        SUM(cost_estimate_usd) as total_cost
                    FROM telemetry
                """).fetchone()

                # Per agent breakdown
                by_agent = cursor.execute("""
                    SELECT agent, COUNT(*) as calls, SUM(total_tokens) as tokens, SUM(tokens_saved) as saved
                    FROM telemetry GROUP BY agent
                """).fetchall()

                return {
                    "total_calls": row["total_calls"] or 0,
                    "total_tokens": row["sum_tokens"] or 0,
                    "total_tokens_saved": row["sum_saved"] or 0,
                    "total_cached_tokens": row["sum_cached"] or 0,
                    "average_latency_ms": round(row["avg_latency"] or 0.0, 2),
                    "total_cost_usd": round(row["total_cost"] or 0.0, 5),
                    "by_agent": {r["agent"]: {"calls": r["calls"], "tokens": r["tokens"], "saved": r["saved"]} for r in by_agent}
                }
        except Exception as e:
            logger.error(f"Failed to fetch telemetry summary: {e}")
            return {"error": str(e)}

    def format_badge(self, agent: str, action: str, total_tokens: int, tokens_saved: int, latency_ms: float, model: str) -> str:
        """Formats a markdown telemetry badge suitable for commits and PRs."""
        return (
            f"📊 **Telemetry ({agent.upper()})**: {total_tokens:,} tokens used | "
            f"⚡ {tokens_saved:,} tokens saved | ⏱️ {latency_ms:.1f}ms | 🤖 `{model}`"
        )


# Global default instance
telemetry = TelemetryTracker()


if __name__ == "__main__":
    import json
    tracker = TelemetryTracker()
    # Test record
    tracker.record_call(
        agent="bolt",
        action="Git Token Optimization Benchmark",
        model="gemini-3.7-flash",
        prompt_tokens=420,
        completion_tokens=180,
        tokens_saved=1250,
        latency_ms=315.4,
        git_sha="head"
    )
    tracker.record_call(
        agent="jules",
        action="Async PR Maintenance Task",
        model="gemini-3.7-flash",
        prompt_tokens=560,
        completion_tokens=220,
        tokens_saved=2400,
        latency_ms=410.2,
        git_sha="head"
    )
    print("=== LIVE TELEMETRY SUMMARY ===")
    print(json.dumps(tracker.get_summary(), indent=2))
