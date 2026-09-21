#!/usr/bin/env python3
"""
Guardian Agent Web UI Server — JudgeGuard Edition
Serves the dashboard and processes real JudgeGuard verification requests.

Usage:
    PYTHONPATH=. .venv/bin/python3 web_ui/server.py
    # Open http://localhost:8055
"""

import os
import sys
import json
import time
import queue
import threading
import logging
from dotenv import load_dotenv

# Load .env file automatically
load_dotenv()
import subprocess
import uuid
import jwt
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# ── Kick modules (PYTHONPATH must include project root) ───────────────────────
PROJECT_ROOT_FOR_IMPORT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT_FOR_IMPORT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT_FOR_IMPORT)

try:
    from src.kick import oauth as kick_oauth
    from src.kick import webhook as kick_webhook
    from src.kick import events as kick_events
    from src.kick.client import KickClient
    from src.kick.stream import KickStreamManager
    KICK_ENABLED = bool(os.getenv("KICK_CLIENT_ID"))
except ImportError:
    KICK_ENABLED = False
    logging.warning("Kick modules not found — Kick integration disabled.")

# ── Webhook processing queue (fast-ack architecture) ─────────────────────────
_webhook_queue: queue.Queue = queue.Queue(maxsize=1000)


def _webhook_worker():
    """Background thread: drain webhook queue and process events."""
    while True:
        try:
            item = _webhook_queue.get(timeout=5)
            meta, payload = item
            kick_events.handle_event(meta, payload)
        except queue.Empty:
            continue
        except Exception:
            logging.exception("Webhook worker error")


if KICK_ENABLED:
    _wh_thread = threading.Thread(target=_webhook_worker, daemon=True)
    _wh_thread.start()

# ── In-memory Kick session store (replace with encrypted DB in prod) ──────────
# { state: { "access_token": ..., "refresh_token": ..., "expires_at": ... } }
_kick_sessions: dict = {}

PORT = int(os.getenv("PORT", 8080))
WEB_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(WEB_DIR)
JUDGE_GUARD_SCRIPT = os.path.join(PROJECT_ROOT, "judge_guard.py")
JWT_SECRET = os.getenv("JWT_SECRET", str(uuid.uuid4()))

# Use the venv python if available
VENV_PYTHON = os.path.join(PROJECT_ROOT, ".venv", "bin", "python3")
PYTHON_BIN = VENV_PYTHON if os.path.exists(VENV_PYTHON) else sys.executable


class GuardianHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        print(f"[{time.strftime('%H:%M:%S')}] {format % args}")

    def do_GET(self):
        parsed = urlparse(self.path)
        path   = parsed.path
        params = parse_qs(parsed.query)

        if path == "/" or path == "/index.html":
            self.serve_file(os.path.join(WEB_DIR, "index.html"), "text/html")

        elif path == "/health":
            self.json_response({
                "status": "ok",
                "agent": "JudgeGuard v2.0",
                "python": PYTHON_BIN,
                "mode": "100% PRODUCT",
                "kick_enabled": KICK_ENABLED,
            })

        # ── Kick: Start OAuth flow ────────────────────────────────────────────
        elif path == "/kick/login" and KICK_ENABLED:
            try:
                url, state = kick_oauth.build_authorize_url()
                self.send_response(302)
                self.send_header("Location", url)
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
            except Exception as e:
                self.json_response({"error": str(e)}, status=500)

        # ── Kick: OAuth callback ──────────────────────────────────────────────
        # Kick redirect URL is localhost:3000/callback
        # This handler covers if you run a second server on 3000, OR you
        # proxy /callback from port 3000 to here.
        elif path == "/callback" and KICK_ENABLED:
            code  = (params.get("code")  or [None])[0]
            state = (params.get("state") or [None])[0]
            error = (params.get("error") or [None])[0]

            if error:
                self.json_response({"error": error, "kick": False}, status=400)
                return
            if not code or not state:
                self.json_response({"error": "Missing code or state"}, status=400)
                return

            try:
                tokens = kick_oauth.exchange_code(code, state)
                session_id = str(uuid.uuid4())
                _kick_sessions[session_id] = {
                    "access_token":  tokens["access_token"],
                    "refresh_token": tokens.get("refresh_token"),
                    "expires_at":    time.time() + tokens.get("expires_in", 3600),
                }

                # Persist token for CLI and background workers
                token_file = os.path.join(PROJECT_ROOT_FOR_IMPORT, ".kick_token.json")
                with open(token_file, "w") as tf:
                    json.dump(_kick_sessions[session_id], tf, indent=2)
                try:
                    os.chmod(token_file, 0o600)
                except Exception:
                    pass

                # Auto-initialize Stream Manager
                client = KickClient(
                    client_id=os.environ["KICK_CLIENT_ID"],
                    access_token=tokens["access_token"],
                )
                stream_mgr = KickStreamManager(client)
                title = "🧠 Kaggle S6 Challenge | JudgeGuard AI Live Coding Session"
                try:
                    stream_mgr.update_channel(title=title)
                except Exception as ex:
                    logging.warning(f"Could not update channel title: {ex}")

                stream_key = None
                obs_launched = False
                try:
                    stream_key = stream_mgr.get_stream_key()
                    if stream_key:
                        obs_launched = stream_mgr.launch_obs(stream_key)
                except Exception as ex:
                    logging.warning(f"Could not fetch stream key or launch OBS: {ex}")

                html_resp = f"""<!DOCTYPE html>
<html>
<head><title>Kick Stream Ready</title><style>
body {{ font-family: -apple-system, sans-serif; background: #0b0e14; color: #00ff88; text-align: center; padding: 50px; }}
.card {{ background: #151921; border: 1px solid #222a36; border-radius: 12px; padding: 30px; max-width: 600px; margin: auto; }}
h1 {{ color: #ffffff; }}
.btn {{ background: #00ff88; color: #000; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: bold; display: inline-block; margin-top: 20px; }}
</style></head>
<body>
<div class="card">
  <h1>✅ Kick Authorized & Stream Ready!</h1>
  <p>Channel Title set: <strong>{title}</strong></p>
  <p>OBS Studio: <strong>{'🚀 Launched with KizaGuard Profile' if obs_launched else '⚠️ Profile generated (~/.config/obs-studio)'}</strong></p>
  <a class="btn" href="https://kick.com/dashboard" target="_blank">Open Kick Dashboard (Go Live)</a>
</div>
</body>
</html>"""
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(html_resp.encode("utf-8"))))
                self.end_headers()
                self.wfile.write(html_resp.encode("utf-8"))
            except ValueError as e:
                self.json_response({"error": str(e), "kick": False}, status=403)
            except Exception as e:
                logging.error(f"Token exchange failed: {e}")
                self.json_response({"error": "Token exchange failed", "kick": False}, status=500)

        else:
            self.send_error(404, "Not Found")

    def do_DELETE(self):
        path = urlparse(self.path).path

        # ── Kick: Disconnect / revoke tokens ─────────────────────────────────
        if path == "/kick/disconnect" and KICK_ENABLED:
            length = int(self.headers.get("Content-Length", 0))
            body   = json.loads(self.rfile.read(length)) if length else {}
            sid    = body.get("session_id", "")
            sess   = _kick_sessions.pop(sid, None)

            if sess and sess.get("access_token"):
                kick_oauth.revoke_token(sess["access_token"], "access_token")
                if sess.get("refresh_token"):
                    kick_oauth.revoke_token(sess["refresh_token"], "refresh_token")

            self.json_response({"kick": False, "disconnected": True})
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

        # ── Kick: Webhook endpoint ────────────────────────────────────────────
        elif path == "/kick/webhook" and KICK_ENABLED:
            # Read raw bytes BEFORE any parsing (P0 audit requirement)
            length   = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(length)

            # Fast-ack immediately — processing goes to queue
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", "2")
            self.end_headers()
            self.wfile.write(b"{}")

            # Now validate + enqueue (after 200 is sent)
            try:
                headers_dict = dict(self.headers)
                meta = kick_webhook.validate_webhook(raw_body, headers_dict)
                payload = json.loads(raw_body)
                _webhook_queue.put_nowait((meta, payload))
            except kick_webhook.WebhookError as e:
                logging.warning("Webhook rejected: %s", e)
            except queue.Full:
                logging.error("Webhook queue full — event dropped")
            except Exception:
                logging.exception("Webhook handling error")

        else:
            self.send_error(404, "Not Found")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
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

    def json_response(self, data, status=200):
        content = json.dumps(data).encode()
        self.send_response(status)
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

        # Generate REAL signed JWT if approved
        real_token = None
        if approved:
            payload = {
                "scope": scope,
                "iss": "judge-guard-auth0",
                "exp": time.time() + 3600
            }
            real_token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")

        return {
            "action": action,
            "scope": scope,
            "approved": approved,
            "block_layer": block_layer,
            "block_reason": block_reason,
            "layers": layers_log,
            "auth0_token": real_token,
            "timestamp": time.strftime("%H:%M:%S")
        }


def main():
    server = HTTPServer(("0.0.0.0", PORT), GuardianHandler)
    
    # Pre-flight check: ensure no mocks
    has_keys = bool(os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEYS"))
    if not has_keys:
        print("\n❌ CRITICAL ERROR: GEMINI_API_KEY is missing.")
        print("   This project operates in 100% PRODUCT MODE.")
        print("   Mocks and simulations are strictly forbidden.")
        print("   Please create a .env file with a valid GEMINI_API_KEY.\n")
        sys.exit(1)
        
    print(f"\n🛡️  JudgeGuard Web UI Server")
    print(f"   Running at: http://localhost:{PORT}")
    print(f"   Mode: ✅ 100% PRODUCT MODE (Mocks FORBIDDEN)")
    print(f"   Python: {PYTHON_BIN}")
    print(f"\n   Press Ctrl+C to stop\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n✋ Server stopped.")


if __name__ == "__main__":
    main()
