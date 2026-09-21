#!/usr/bin/env python3
"""
Restream.io MCP Integration Setup
Handles OAuth 2.0 authorization and saves token to .env
MCP endpoint: https://mcp.restream.io/mcp
"""
import os
import sys
import json
import time
import webbrowser
import urllib.parse
import urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

# ─── Config ───────────────────────────────────────────
PROJECT_ROOT  = Path(__file__).resolve().parent
ENV_FILE      = PROJECT_ROOT / ".env"

# Restream OAuth endpoints
RESTREAM_AUTH_URL   = "https://api.restream.io/login"
RESTREAM_TOKEN_URL  = "https://api.restream.io/oauth/token"
RESTREAM_API_BASE   = "https://api.restream.io/v2"
RESTREAM_MCP_URL    = "https://mcp.restream.io/mcp"

# Read from env or prompt
CLIENT_ID     = os.getenv("RESTREAM_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("RESTREAM_CLIENT_SECRET", "")
REDIRECT_URI  = "http://localhost:9877/callback"

# ─── Helpers ──────────────────────────────────────────

def update_env(key: str, value: str):
    """Upsert key=value in .env file."""
    lines = []
    found = False
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            if line.startswith(f"{key}="):
                lines.append(f"{key}={value}")
                found = True
            else:
                lines.append(line)
    if not found:
        lines.append(f"{key}={value}")
    ENV_FILE.write_text("\n".join(lines) + "\n")
    print(f"✅ {key} saved to .env")


class CallbackHandler(BaseHTTPRequestHandler):
    """One-shot local callback server."""
    code = None

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = dict(urllib.parse.parse_qsl(parsed.query))
        CallbackHandler.code = params.get("code")
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"<h1>Restream auth complete! Close this tab.</h1>")

    def log_message(self, *args):
        pass  # quiet


def oauth_flow():
    """Run OAuth 2.0 Authorization Code flow."""
    if not CLIENT_ID:
        print("""
❌  RESTREAM_CLIENT_ID not set.

Steps to get credentials:
1. Go to https://restream.io/settings/app
2. Create a new app  →  Redirect URI: http://localhost:9877/callback
3. Copy Client ID and Client Secret
4. Add to .env:
     RESTREAM_CLIENT_ID=<your-id>
     RESTREAM_CLIENT_SECRET=<your-secret>
5. Re-run this script
""")
        sys.exit(1)

    auth_url = (
        f"{RESTREAM_AUTH_URL}"
        f"?client_id={urllib.parse.quote(CLIENT_ID)}"
        f"&response_type=code"
        f"&redirect_uri={urllib.parse.quote(REDIRECT_URI)}"
        f"&scope=channel_read%20channel_write%20stream_start%20stream_stop"
    )

    print(f"\n🌐 Opening browser for Restream authorization…\n{auth_url}\n")
    webbrowser.open(auth_url)

    # One-shot server
    server = HTTPServer(("127.0.0.1", 9877), CallbackHandler)
    server.timeout = 120
    print("⏳ Waiting for callback (2 min timeout)…")
    server.handle_request()

    code = CallbackHandler.code
    if not code:
        print("❌ No code received — auth failed")
        sys.exit(1)

    print(f"✅ Got auth code, exchanging for token…")

    # Token exchange
    data = urllib.parse.urlencode({
        "grant_type"   : "authorization_code",
        "code"         : code,
        "redirect_uri" : REDIRECT_URI,
        "client_id"    : CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }).encode()

    req = urllib.request.Request(
        RESTREAM_TOKEN_URL,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    with urllib.request.urlopen(req) as resp:
        token_data = json.loads(resp.read())

    access_token  = token_data.get("access_token", "")
    refresh_token = token_data.get("refresh_token", "")

    update_env("RESTREAM_ACCESS_TOKEN",  access_token)
    update_env("RESTREAM_REFRESH_TOKEN", refresh_token)
    print(f"🎉 Restream tokens saved!")
    return access_token


def test_mcp_connection(token: str):
    """Quick MCP handshake — list available tools."""
    import json
    print(f"\n🔌 Testing Restream MCP: {RESTREAM_MCP_URL}")

    # MCP initialize request (JSON-RPC 2.0 over HTTP)
    payload = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "JudgeGuard", "version": "1.0"}
        }
    }).encode()

    req = urllib.request.Request(
        RESTREAM_MCP_URL,
        data=payload,
        headers={
            "Content-Type" : "application/json",
            "Authorization": f"Bearer {token}",
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            print("✅ MCP initialized:", json.dumps(result, indent=2)[:400])
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"❌ MCP init failed {e.code}: {body[:300]}")
    except Exception as e:
        print(f"❌ MCP error: {e}")


def get_channel_info(token: str):
    """Fetch Restream channel / stream status via REST API."""
    req = urllib.request.Request(
        f"{RESTREAM_API_BASE}/user/channel",
        headers={"Authorization": f"Bearer {token}"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            print("\n📡 Restream Channel Info:")
            print(json.dumps(data, indent=2)[:600])
    except Exception as e:
        print(f"⚠️  Channel info error: {e}")


if __name__ == "__main__":
    existing_token = os.getenv("RESTREAM_ACCESS_TOKEN", "")

    if "--auth" in sys.argv or not existing_token:
        token = oauth_flow()
    else:
        token = existing_token
        print(f"✅ Using existing RESTREAM_ACCESS_TOKEN from env")

    test_mcp_connection(token)
    get_channel_info(token)
