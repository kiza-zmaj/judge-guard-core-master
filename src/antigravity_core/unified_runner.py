#!/usr/bin/env python3
"""
Unified Production System Runner
Orchestrates continuous live verification cycles, JudgeGuard anti-drift monitoring,
and real-time PWA telemetry dispatch without mocks.
"""

import os
import sys
import time
import signal
import sqlite3
import logging
import argparse
from typing import Dict, Any, Optional, Callable

# Ensure root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from judge_guard import JudgeGuard, PROJECT_ESSENCE
try:
    from src.antigravity_core.mobile_bridge import get_bridge
    BRIDGE_AVAILABLE = True
except ImportError:
    BRIDGE_AVAILABLE = False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("UnifiedProductionRunner")


class UnifiedProductionRunner:
    """
    Production-grade runner unifying 8-stage verification, anti-drift sentinels,
    and live mobile bridge telemetry.
    """

    def __init__(self, db_path: str = "research.db", work_log_path: str = "WORK_LOG.md"):
        self.db_path = os.path.join(PROJECT_ROOT, db_path) if not os.path.isabs(db_path) else db_path
        self.work_log_path = os.path.join(PROJECT_ROOT, work_log_path) if not os.path.isabs(work_log_path) else work_log_path
        self.guard = JudgeGuard(work_log_path=self.work_log_path)
        self.bridge = get_bridge() if BRIDGE_AVAILABLE else None
        self._running = False

    def run_probe(self) -> bool:
        """
        Execute the live 8-stage cycle probe against physical runtime.
        Returns True if all stages pass, False otherwise.
        """
        logger.info("⚡ Executing Live 8-Stage Cycle Verification Probe...")
        try:
            from tests.live_8stage_probe import (
                stage_1_discovery,
                stage_2_awareness,
                stage_3_pattern_recognition,
                stage_4_experimentation,
                stage_5_latent_drift,
                stage_6_detection,
                stage_7_correction,
                stage_8_resilience,
            )

            res = stage_1_discovery()
            guard = res["guard"]
            stage_2_awareness(guard)
            stage_3_pattern_recognition()
            stage_4_experimentation(guard)
            stage_5_latent_drift()
            stage_6_detection(guard)
            stage_7_correction(guard)
            stage_8_resilience(guard)

            if self.bridge:
                self.bridge.push_verdict(
                    "Live 8-Stage Cycle Verification Probe",
                    "PASSED",
                    "All 8 verification stages succeeded"
                )
            logger.info("✅ Live 8-Stage Cycle Verification Probe COMPLETED successfully.")
            return True
        except Exception as e:
            logger.error(f"🛑 Live 8-Stage Probe failed: {e}")
            if self.bridge:
                self.bridge.push_verdict(
                    "Live 8-Stage Cycle Verification Probe",
                    "BLOCKED",
                    f"Probe failure: {str(e)}"
                )
            return False

    def run_health_check(self) -> Dict[str, Any]:
        """
        Perform physical invariant and telemetry freshness check.
        """
        results = {
            "timestamp": time.time(),
            "work_log_exists": os.path.exists(self.work_log_path),
            "work_log_fresh": False,
            "db_connected": False,
            "bridge_connected": self.bridge is not None,
        }

        if results["work_log_exists"]:
            mtime = os.path.getmtime(self.work_log_path)
            delta_t = time.time() - mtime
            results["work_log_fresh"] = delta_t < 120.0
            results["work_log_delta_seconds"] = round(delta_t, 2)

        if os.path.exists(self.db_path):
            try:
                conn = sqlite3.connect(self.db_path)
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table';")
                results["table_count"] = cur.fetchone()[0]
                conn.close()
                results["db_connected"] = True
            except Exception as e:
                results["db_error"] = str(e)

        logger.info(f"Health Check Results: {results}")
        return results

    def execute_gated_action(self, action_name: str, action_fn: Callable[[], bool]) -> bool:
        """
        Executes an action wrapped in the Mandatory Pre/Post Verification Workflow.
        """
        logger.info(f"Initiating Gated Action: '{action_name}'")

        # Step 1: Update Work Log
        with open(self.work_log_path, "a", encoding="utf-8") as f:
            f.write(f"🟡 Starting {action_name}\n")

        # Step 2: Pre-check
        pre_passed = self.guard.verify_action(f"Start {action_name}")
        if not pre_passed:
            logger.error(f"🛑 Pre-check BLOCKED action: '{action_name}'")
            return False

        # Step 3: Execute
        try:
            success = action_fn()
            if not success:
                logger.error(f"🛑 Execution failed for action: '{action_name}'")
                return False
        except Exception as e:
            logger.error(f"🛑 Exception during action '{action_name}': {e}")
            return False

        # Step 4: Update Work Log
        with open(self.work_log_path, "a", encoding="utf-8") as f:
            f.write(f"✅ Completed {action_name}\n")

        # Step 5: Post-check
        post_passed = self.guard.verify_action(f"Verify {action_name} Complete")
        if not post_passed:
            logger.error(f"🛑 Post-check BLOCKED for action: '{action_name}'")
            return False

        logger.info(f"✅ Gated Action '{action_name}' fully verified and completed.")
        return True

    def start_daemon(self, interval_seconds: int = 60):
        """
        Run continuous periodic health checks and probe telemetry.
        """
        self._running = True
        logger.info(f"🚀 Starting Unified Production Runner daemon (interval={interval_seconds}s)")

        def handle_signal(sig, frame):
            logger.info("Graceful shutdown received. Stopping daemon...")
            self._running = False

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

        while self._running:
            self.run_health_check()
            time.sleep(interval_seconds)

        logger.info("Daemon stopped.")


def main():
    parser = argparse.ArgumentParser(description="Unified Production System Runner")
    parser.add_argument("--probe", action="store_true", help="Execute the 8-Stage Cycle Probe")
    parser.add_argument("--health", action="store_true", help="Perform physical health and telemetry checks")
    parser.add_argument("--daemon", action="store_true", help="Run in continuous background daemon mode")
    parser.add_argument("--interval", type=int, default=60, help="Interval for daemon mode in seconds")
    args = parser.parse_args()

    runner = UnifiedProductionRunner()

    if args.probe:
        success = runner.run_probe()
        sys.exit(0 if success else 1)
    elif args.health:
        results = runner.run_health_check()
        is_ok = results.get("work_log_exists") and results.get("db_connected")
        sys.exit(0 if is_ok else 1)
    elif args.daemon:
        runner.start_daemon(args.interval)
    else:
        # Default: Run probe once and exit
        success = runner.run_probe()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
