#!/usr/bin/env python3
"""
Guardian Agent Web UI Server — JudgeGuard Edition
Serves the dashboard and processes real JudgeGuard verification requests.

Usage:
    PYTHONPATH=. .venv/bin/python3 web_ui/server.py
    # Open http://localhost:8080
"""

import os
import sys
import json
import time
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

PORT = int(os.getenv("PORT", 8080))
WEB_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(WEB_DIR)
JUDGE_GUARD_SCRIPT = os.path.join(PROJECT_ROOT, "judge_guard.py")

# Use the venv python if available
VENV_PYTHON = os.path.join(PROJECT_ROOT, ".venv", "bin", "python3")
PYTHON_BIN = VENV_PYTHON if os.path.exists(VENV_PYTHON) else sys.executable


class GuardianHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        print(f"[{time.strftime('%H:%M:%S')}] {format % args}")

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/" or path == "/index.html":
            self.serve_file(os.path.join(WEB_DIR, "index.html"), "text/html")
        elif path == "/health":
            self.json_response({
                "status": "ok",
                "agent": "JudgeGuard v2.0",
                "python": PYTHON_BIN,
                "mock_mode": not bool(os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEYS"))
            })
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        path = urlparse(self.path).path

        if path == "/execute":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            action = body.get("action", "").strip()
            scope = body.get("scope", "read:data")

            if not action:
                self.json_response({"error": "action is required", "approved": False})
                return

            result = self.run_judgeguard(action, scope)
            self.json_response(result)
        else:
            self.send_error(404, "Not Found")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def serve_file(self, path, content_type):
        try:
            with open(path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", len(content))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self.send_error(404, f"File not found: {path}")

    def json_response(self, data):
        content = json.dumps(data).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(content))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(content)

    def run_judgeguard(self, action: str, scope: str) -> dict:
        """
        Run judge_guard.py directly and return a structured per-layer result.
        The Python process writes to WORK_LOG.md and returns exit 0 (PASSED) or 1 (BLOCKED).
        """
        # Pre-step: log to WORK_LOG.md
        work_log_path = os.path.join(PROJECT_ROOT, "WORK_LOG.md")
        try:
            with open(work_log_path, "a", encoding="utf-8") as f:
                f.write(f"\n🟡 Starting [{scope}]: {action}\n")
        except Exception:
            pass

        layers_log = []
        approved = False
        block_layer = None
        block_reason = ""

        # Layer 00: Security pre-check (fast, local — mirror judge_guard.py logic)
        dangerous_keywords = ["sudo", "rm -rf /", "rm -rf /*", "chmod -r 777"]
        action_lower = action.lower()
        if any(k in action_lower for k in dangerous_keywords):
            block_layer = "L00"
            block_reason = "Dangerous command detected (sudo/rm-rf/chmod)"
            layers_log.append({"layer": "L00", "status": "BLOCKED", "msg": block_reason})
        else:
            layers_log.append({"layer": "L00", "status": "PASSED", "msg": "No dangerous commands"})

            # Run the real judge_guard.py for the full pipeline
            try:
                result = subprocess.run(
                    [PYTHON_BIN, JUDGE_GUARD_SCRIPT, action],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=PROJECT_ROOT,
                    env={**os.environ, "PYTHONPATH": PROJECT_ROOT}
                )
                full_output = result.stdout + result.stderr
                approved = result.returncode == 0

                # Parse layer results from output
                if "Layer 1 Block" in full_output:
                    block_layer = "L1"
                    block_reason = "Tool enforcement violation (Phase rules)"
                    layers_log.append({"layer": "L1", "status": "BLOCKED", "msg": block_reason})
                else:
                    layers_log.append({"layer": "L1", "status": "PASSED", "msg": "Tool usage matches phase"})

                if approved:
                    layers_log.append({"layer": "L3", "status": "PASSED", "msg": "Semantic drift < 20% — action aligns with Project Essence"})
                elif "Violation detected" in full_output or "BLOCKED" in full_output:
                    if not block_layer:
                        block_layer = "L3"
                        block_reason = "Semantic drift or Master Orchestration violation"
                    layers_log.append({"layer": "L3", "status": "BLOCKED", "msg": block_reason})
                else:
                    layers_log.append({"layer": "L3", "status": "PASSED", "msg": "Essence check passed"})

            except subprocess.TimeoutExpired:
                approved = False
                block_reason = "JudgeGuard verification timeout (30s)"
                layers_log.append({"layer": "L3", "status": "BLOCKED", "msg": block_reason})
            except Exception as e:
                approved = False
                block_reason = f"Server error: {str(e)}"
                layers_log.append({"layer": "L3", "status": "BLOCKED", "msg": block_reason})

        # Post-step: log result to WORK_LOG.md
        try:
            with open(work_log_path, "a", encoding="utf-8") as f:
                if approved:
                    f.write(f"✅ Approved [{scope}]: {action}\n")
                else:
                    f.write(f"🛑 Blocked [{scope}]: {action} — {block_reason}\n")
        except Exception:
            pass

        return {
            "action": action,
            "scope": scope,
            "approved": approved,
            "block_layer": block_layer,
            "block_reason": block_reason,
            "layers": layers_log,
            "auth0_token": f"eyJhbGciOiJSUzI1NiJ9.mock.{scope.replace(':', '_')}" if approved else None,
            "timestamp": time.strftime("%H:%M:%S")
        }


def main():
    server = HTTPServer(("0.0.0.0", PORT), GuardianHandler)
    mock = not bool(os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEYS"))
    print(f"\n🛡️  JudgeGuard Web UI Server")
    print(f"   Running at: http://localhost:{PORT}")
    print(f"   Mode: {'⚠️  MOCK (set GEMINI_API_KEY for real AI)' if mock else '✅ LIVE Gemini AI'}")
    print(f"   Python: {PYTHON_BIN}")
    print(f"\n   Press Ctrl+C to stop\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n✋ Server stopped.")


if __name__ == "__main__":
    main()
