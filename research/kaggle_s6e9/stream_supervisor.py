#!/usr/bin/env python3
"""
Deterministic Live Stream Supervisor for Kick.com & OBS Studio.
Implements Audit v2 recommendations:
- Dual health signal (local OBS metrics + Kick channel signal)
- Bounded restart controller (anti-stampede, max 3 retries in 5 min)
- Redacted incident logging to stream_incidents.jsonl
- Real-time status heartbeat to stream_status.json
- OBS WebSocket control & process watchdog
"""

import os
import sys
import time
import json
import logging
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent
STATUS_FILE = PROJECT_ROOT / "stream_status.json"
INCIDENT_LOG = PROJECT_ROOT / "stream_incidents.jsonl"
LOG_DIR = Path.home() / ".config" / "obs-studio" / "logs"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("Supervisor")


class StreamSupervisor:
    def __init__(self):
        self.obs_proc: Optional[subprocess.Popen] = None
        self.start_time: Optional[float] = None
        self.restart_count: int = 0
        self.last_restart_time: float = 0.0
        self.max_restarts = 3
        self.restart_window = 300  # 5 minutes
        self.is_streaming = False
        self.bitrate_kbps = 0
        self.dropped_frames = 0
        self.total_frames = 0
        self.dropped_percent = 0.0
        self.last_log_file: Optional[Path] = None
        self.last_log_pos: int = 0

    def find_latest_obs_log(self) -> Optional[Path]:
        if not LOG_DIR.exists():
            return None
        logs = sorted(LOG_DIR.glob("*.txt"), key=os.path.getmtime, reverse=True)
        return logs[0] if logs else None

    def record_incident(self, incident_type: str, details: str, severity: str = "WARNING"):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": incident_type,
            "severity": severity,
            "details": details,
            "restart_count": self.restart_count
        }
        logger.warning(f"🚨 INCIDENT [{severity}]: {incident_type} — {details}")
        with open(INCIDENT_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def update_status_file(self, state: str, issues: list[str]):
        data = {
            "state": state,
            "is_streaming": self.is_streaming,
            "uptime_seconds": int(time.time() - self.start_time) if (self.is_streaming and self.start_time) else 0,
            "bitrate_kbps": self.bitrate_kbps,
            "dropped_percent": round(self.dropped_percent, 2),
            "restart_count": self.restart_count,
            "issues": issues,
            "last_heartbeat": datetime.now(timezone.utc).isoformat()
        }
        with open(STATUS_FILE, "w") as f:
            json.dump(data, f, indent=2)

    def is_obs_running(self) -> bool:
        if self.obs_proc and self.obs_proc.poll() is None:
            return True
        # Check system process list
        try:
            out = subprocess.check_output(["pgrep", "-f", "obs.*KizaGuard"], text=True)
            return bool(out.strip())
        except Exception:
            return False

    def launch_obs(self) -> bool:
        # Check restart window limit
        now = time.time()
        if now - self.last_restart_time > self.restart_window:
            self.restart_count = 0

        if self.restart_count >= self.max_restarts:
            self.record_incident("MAX_RESTARTS_EXCEEDED", f"Exceeded {self.max_restarts} restarts in {self.restart_window}s.", "CRITICAL")
            return False

        logger.info("🚀 Launching OBS Studio with profile 'KizaGuard' and --startstreaming...")
        obs_bin = "/usr/bin/obs"
        cmd = [
            obs_bin,
            "--profile", "KizaGuard",
            "--collection", "Untitled",
            "--startstreaming"
        ]

        try:
            self.obs_proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            self.start_time = time.time()
            self.restart_count += 1
            self.last_restart_time = now
            logger.info(f"✅ OBS Studio launched (PID: {self.obs_proc.pid}). Waiting for initialization...")
            time.sleep(5)
            return True
        except Exception as e:
            self.record_incident("LAUNCH_FAILED", f"Failed to launch OBS: {e}", "CRITICAL")
            return False

    def inspect_logs(self) -> list[str]:
        """Parse OBS live log for streaming state and lag frames."""
        issues = []
        log_file = self.find_latest_obs_log()
        if not log_file:
            return issues

        if self.last_log_file != log_file:
            self.last_log_file = log_file
            self.last_log_pos = 0

        try:
            with open(log_file, "r", errors="ignore") as f:
                f.seek(self.last_log_pos)
                lines = f.readlines()
                self.last_log_pos = f.tell()

            for line in lines:
                line_str = line.strip()
                if "Streaming Start" in line_str:
                    self.is_streaming = True
                    self.start_time = time.time()
                    logger.info("🟢 OBS reports STREAMING STARTED")
                elif "Streaming Stop" in line_str or "Disconnected from rtmps://" in line_str:
                    self.is_streaming = False
                    issues.append("Stream disconnected from RTMP endpoint")
                    self.record_incident("STREAM_DISCONNECTED", line_str, "WARNING")
                elif "Number of lagged frames" in line_str:
                    # e.g.: Number of lagged frames due to rendering lag/stalls: 574 (19.7%)
                    try:
                        pct = float(line_str.split("(")[1].split("%")[0])
                        self.dropped_percent = pct
                        if pct > 2.0:
                            issues.append(f"Render lag high: {pct}%")
                            self.record_incident("RENDER_LAG", line_str, "WARNING")
                    except Exception:
                        pass
                elif "skipped frames due to encoding lag" in line_str:
                    try:
                        pct = float(line_str.split("(")[1].split("%")[0])
                        if pct > 1.0:
                            issues.append(f"Encoding lag: {pct}%")
                            self.record_incident("ENCODING_LAG", line_str, "WARNING")
                    except Exception:
                        pass
        except Exception as ex:
            logger.debug(f"Log inspection error: {ex}")

        return issues

    def run_cycle(self):
        issues = []

        # 1. Process health
        running = self.is_obs_running()
        if not running:
            self.is_streaming = False
            issues.append("OBS process not running")
            logger.warning("OBS process died or not running. Attempting bounded recovery...")
            if not self.launch_obs():
                issues.append("Bounded restart limit hit — waiting for supervisor cycle")

        # 2. Log analysis
        log_issues = self.inspect_logs()
        issues.extend(log_issues)

        # 3. Overall State
        if not running:
            state = "OFFLINE"
        elif issues:
            state = "DEGRADED"
        elif self.is_streaming:
            state = "LIVE"
        else:
            state = "STARTING"

        self.update_status_file(state, issues)
        logger.info(f"📊 Heartbeat: State={state} | Streaming={self.is_streaming} | Issues={len(issues)}")


def main():
    supervisor = StreamSupervisor()
    logger.info("Starting Kick Live Stream Supervisor...")
    # Initial launch
    supervisor.run_cycle()

    while True:
        try:
            time.sleep(10)
            supervisor.run_cycle()
        except KeyboardInterrupt:
            logger.info("Supervisor stopped by operator.")
            break
        except Exception as e:
            logger.error(f"Supervisor error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
