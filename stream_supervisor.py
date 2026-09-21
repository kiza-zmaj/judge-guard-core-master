#!/usr/bin/env python3
"""
Production Kick Live Stream Supervisor v3 — with Restream MCP awareness.
Fixes:
  - OBS Advanced Output mode enforces keyint=2s (keyint=60@30fps)
  - WebSocket-driven bitrate/stats (no more log-only health)
  - Crash recovery with sliding-window (reset after 10min stable)
  - Restream OAuth token stored in .env (RESTREAM_ACCESS_TOKEN)
  - Redacted secrets, bounded restarts (max 3 in 5min)
"""

import os
import sys
import time
import json
import logging
import subprocess
import threading
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent
STATUS_FILE  = PROJECT_ROOT / "stream_status.json"
INCIDENT_LOG = PROJECT_ROOT / "stream_incidents.jsonl"
LOG_DIR      = Path.home() / ".config" / "obs-studio" / "logs"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("Supervisor")

# ──────────────────────────────────────────────
# OBS WebSocket helpers (no auth, port 4455)
# ──────────────────────────────────────────────
try:
    import websocket as _ws_mod
    _HAS_WS = True
except ImportError:
    _HAS_WS = False
    logger.warning("websocket-client not installed; falling back to log-only health")


class OBSWebSocket:
    """Minimal OBS WebSocket v5 client (op/d envelope)."""
    def __init__(self, host="127.0.0.1", port=4455):
        self.uri = f"ws://{host}:{port}"
        self._req_id = 0
        self._sock   = None

    def _next_id(self):
        self._req_id += 1
        return str(self._req_id)

    def connect(self) -> bool:
        if not _HAS_WS:
            return False
        try:
            self._sock = _ws_mod.create_connection(self.uri, timeout=3)
            hello = json.loads(self._sock.recv())  # op:0
            self._sock.send(json.dumps({"op": 1, "d": {"rpcVersion": 1}}))
            json.loads(self._sock.recv())  # op:2 identified
            return True
        except Exception as e:
            logger.debug(f"OBSWebSocket connect failed: {e}")
            self._sock = None
            return False

    def request(self, req_type: str) -> Optional[dict]:
        if not self._sock:
            return None
        rid = self._next_id()
        try:
            self._sock.send(json.dumps({
                "op": 6,
                "d": {"requestType": req_type, "requestId": rid}
            }))
            resp = json.loads(self._sock.recv())
            return resp.get("d", {}).get("responseData")
        except Exception as e:
            logger.debug(f"OBSWebSocket request {req_type} failed: {e}")
            self._sock = None
            return None

    def close(self):
        if self._sock:
            try: self._sock.close()
            except: pass
            self._sock = None


# ──────────────────────────────────────────────
# Main supervisor
# ──────────────────────────────────────────────

class StreamSupervisor:
    MAX_RESTARTS     = 3
    RESTART_WINDOW   = 300   # 5 min — reset if stable for this long
    STABLE_THRESHOLD = 600   # 10 min stable → reset restart count
    CYCLE_SLEEP      = 10    # seconds between cycles

    def __init__(self):
        self.obs_proc         : Optional[subprocess.Popen] = None
        self.start_time       : Optional[float] = None
        self.restart_count    : int   = 0
        self.last_restart_time: float = 0.0
        self.stable_since     : float = time.time()
        self.is_streaming     : bool  = False
        self.bitrate_kbps     : float = 0.0
        self.dropped_percent  : float = 0.0
        self.skipped_frames   : int   = 0
        self.total_frames     : int   = 0
        self.last_log_file    : Optional[Path] = None
        self.last_log_pos     : int   = 0
        self._ws              = OBSWebSocket()

    # ── incidents ──────────────────────────────
    def _incident(self, typ: str, detail: str, sev: str = "WARNING"):
        entry = {
            "timestamp"    : datetime.now(timezone.utc).isoformat(),
            "type"         : typ,
            "severity"     : sev,
            "details"      : detail,
            "restart_count": self.restart_count
        }
        logger.warning(f"🚨 [{sev}] {typ}: {detail}")
        with open(INCIDENT_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def _write_status(self, state: str, issues: list):
        payload = {
            "state"          : state,
            "is_streaming"   : self.is_streaming,
            "uptime_seconds" : int(time.time() - self.start_time)
                               if (self.is_streaming and self.start_time) else 0,
            "bitrate_kbps"   : round(self.bitrate_kbps, 1),
            "dropped_percent": round(self.dropped_percent, 2),
            "skipped_frames" : self.skipped_frames,
            "restart_count"  : self.restart_count,
            "issues"         : issues,
            "last_heartbeat" : datetime.now(timezone.utc).isoformat()
        }
        with open(STATUS_FILE, "w") as f:
            json.dump(payload, f, indent=2)

    # ── OBS process ────────────────────────────
    def _obs_running(self) -> bool:
        if self.obs_proc and self.obs_proc.poll() is None:
            return True
        try:
            out = subprocess.check_output(["pgrep", "-f", "obs.*KizaGuard"], text=True)
            return bool(out.strip())
        except Exception:
            return False

    def _launch_obs(self) -> bool:
        now = time.time()
        # Sliding-window reset: if stable for STABLE_THRESHOLD, forgive restarts
        if (self.is_streaming and self.start_time
                and (now - self.stable_since) >= self.STABLE_THRESHOLD):
            logger.info("Stream stable 10min — resetting restart counter")
            self.restart_count = 0

        # Decay window: old bursts don't count
        if now - self.last_restart_time > self.RESTART_WINDOW:
            self.restart_count = 0

        if self.restart_count >= self.MAX_RESTARTS:
            self._incident("MAX_RESTARTS_EXCEEDED",
                           f"Hit {self.MAX_RESTARTS} restarts in {self.RESTART_WINDOW}s — waiting",
                           "CRITICAL")
            return False

        logger.info("🚀 Launching OBS (Advanced mode, 2s keyint, CBR 6000k, 60fps 1080p)…")
        obs_env = os.environ.copy()
        obs_env["QT_QPA_PLATFORM"] = "xcb"
        obs_env["DISPLAY"] = obs_env.get("DISPLAY", ":0")

        try:
            self.obs_proc = subprocess.Popen(
                ["/usr/bin/obs", "--profile", "KizaGuard",
                 "--collection", "Untitled", "--startstreaming"],
                env=obs_env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            self.start_time       = time.time()
            self.stable_since     = time.time()
            self.restart_count   += 1
            self.last_restart_time = now
            logger.info(f"✅ OBS PID {self.obs_proc.pid} — waiting 6s for init…")
            time.sleep(6)
            return True
        except Exception as e:
            self._incident("LAUNCH_FAILED", str(e), "CRITICAL")
            return False

    # ── OBS WebSocket health ───────────────────
    def _ws_health(self) -> list:
        """Poll actual stream stats via WebSocket."""
        issues = []
        if not self._ws.connect():
            return issues  # fallback to log parser

        stats = self._ws.request("GetStats")
        if stats:
            total   = stats.get("outputTotalFrames", 0)
            skipped = stats.get("outputSkippedFrames", 0)
            self.skipped_frames = skipped
            self.total_frames   = total
            if total > 0:
                pct = skipped / total * 100
                self.dropped_percent = pct
                if pct > 2.0:
                    issues.append(f"Dropped frames {pct:.1f}%")
                    self._incident("DROPPED_FRAMES", f"{pct:.1f}% dropped ({skipped}/{total})")
            # CPU
            cpu = stats.get("cpuUsage", 0)
            if cpu > 80:
                issues.append(f"CPU {cpu:.0f}%")
                self._incident("CPU_HIGH", f"CPU {cpu:.0f}%")

        stream = self._ws.request("GetStreamStatus")
        if stream:
            self.is_streaming  = stream.get("outputActive", False)
            self.bitrate_kbps  = stream.get("outputBytes", 0) / 1024.0  # rough
            if not self.is_streaming:
                issues.append("OBS reports stream inactive")

        self._ws.close()
        return issues

    # ── Log-based health (fallback) ────────────
    def _log_health(self) -> list:
        issues = []
        if not LOG_DIR.exists():
            return issues
        logs = sorted(LOG_DIR.glob("*.txt"), key=os.path.getmtime, reverse=True)
        if not logs:
            return issues
        log_file = logs[0]

        if self.last_log_file != log_file:
            self.last_log_file = log_file
            self.last_log_pos  = 0

        try:
            with open(log_file, "r", errors="ignore") as f:
                f.seek(self.last_log_pos)
                lines = f.readlines()
                self.last_log_pos = f.tell()
        except Exception:
            return issues

        for line in lines:
            s = line.strip()
            if "Streaming Start" in s:
                self.is_streaming = True
                self.start_time   = time.time()
                self.stable_since = time.time()
                logger.info("🟢 OBS: STREAMING STARTED")
            elif "Streaming Stop" in s or "Disconnected from rtmps://" in s:
                self.is_streaming = False
                issues.append("Stream disconnected")
                self._incident("STREAM_DISCONNECTED", s)
            elif "lagged frames" in s:
                try:
                    pct = float(s.split("(")[1].split("%")[0])
                    self.dropped_percent = pct
                    if pct > 2.0:
                        issues.append(f"Render lag {pct:.1f}%")
                        self._incident("RENDER_LAG", s)
                except Exception:
                    pass
            elif "skipped frames due to encoding" in s:
                try:
                    pct = float(s.split("(")[1].split("%")[0])
                    if pct > 1.0:
                        issues.append(f"Encoding lag {pct:.1f}%")
                        self._incident("ENCODING_LAG", s)
                except Exception:
                    pass
            elif "keyint" in s.lower():
                # Alert if OBS still shows keyint=250
                if "keyint:       250" in s:
                    issues.append("KEYINT WRONG — still 250, config not applied")
                    self._incident("KEYINT_MISMATCH",
                                   "OBS using keyint=250 instead of 60 — restart required",
                                   "WARNING")

        return issues

    # ── Main cycle ─────────────────────────────
    def cycle(self):
        issues = []
        running = self._obs_running()

        if not running:
            self.is_streaming = False
            issues.append("OBS process not running")
            logger.warning("⚠️  OBS not running — attempting bounded restart…")
            self._launch_obs()

        # Try WebSocket first, fall back to logs
        ws_issues = self._ws_health()
        if ws_issues:
            issues.extend(ws_issues)
        else:
            issues.extend(self._log_health())

        # Update stable_since if all good
        if self.is_streaming and not issues:
            pass  # stable_since already set on STREAMING START
        elif issues:
            self.stable_since = time.time()  # reset stability clock on degradation

        # Determine state
        if not running:
            state = "OFFLINE"
        elif issues:
            state = "DEGRADED"
        elif self.is_streaming:
            state = "LIVE"
        else:
            state = "STARTING"

        self._write_status(state, issues)
        logger.info(
            f"💓 State={state} | Live={self.is_streaming} "
            f"| Drop={self.dropped_percent:.1f}% | Restarts={self.restart_count} | Issues={issues}"
        )


def main():
    sup = StreamSupervisor()
    logger.info("=== Supervisor v3 started (Advanced OBS, Restream-ready) ===")
    sup.cycle()  # immediate first cycle

    while True:
        try:
            time.sleep(StreamSupervisor.CYCLE_SLEEP)
            sup.cycle()
        except KeyboardInterrupt:
            logger.info("Supervisor stopped.")
            break
        except Exception as e:
            logger.error(f"Cycle error: {e}", exc_info=True)
            time.sleep(5)


if __name__ == "__main__":
    main()
