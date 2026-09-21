"""
Kick Stream Manager - live stream control for KizaGuard sessions.
Gets stream key, updates channel title/category, and monitors stream status.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

from .client import KickClient


class KickStreamManager:
    """Controls Kick channel + stream for a KizaGuard coding session."""

    # Kick category IDs (common ones for coding / IRL)
    CATEGORY_SOFTWARE_ENGINEERING = 15   # "Software and Game Development"
    CATEGORY_IRL = 37                    # "IRL"
    CATEGORY_JUST_CHATTING = 57          # "Just Chatting"

    def __init__(self, client: KickClient) -> None:
        self.client = client

    # ------------------------------------------------------------------
    # Channel helpers
    # ------------------------------------------------------------------

    def get_stream_key(self) -> Optional[str]:
        """Fetch the RTMP stream key. Requires streamkey:read scope."""
        data = self.client.get("/channel")
        return data.get("stream_key")

    def get_channel_info(self) -> dict:
        """Get current channel title, category, tags, etc."""
        return self.client.get("/channel")

    def update_channel(self, *, title: str, category_id: int = CATEGORY_SOFTWARE_ENGINEERING) -> dict:
        """Set stream title and category before going live.

        Args:
            title: Stream title (max 255 chars).
            category_id: Kick category ID (default = Software & Game Dev).
        """
        return self.client.patch("/channel", json={
            "stream_title": title,
            "category_id": category_id,
        })

    # ------------------------------------------------------------------
    # OBS integration
    # ------------------------------------------------------------------

    def build_obs_profile(self, stream_key: str) -> dict:
        """Return OBS websocket-ready scene collection config."""
        return {
            "rtmp_server": "rtmps://fa723fc1b171.global-contribute.live-video.net/app",
            "stream_key": stream_key,
            "kick_dashboard": "https://kick.com/dashboard",
        }

    def launch_obs(self, stream_key: str, scene: str = "Kaggle-Challenge") -> bool:
        """Try to open OBS with the correct stream settings via CLI args.

        This writes a minimal OBS global.ini override and then launches OBS.
        Returns True if OBS was found and launched, False otherwise.
        """
        obs_paths = [
            "/usr/bin/obs",
            "/usr/local/bin/obs",
            "/snap/bin/obs-studio",
            "/opt/obs-studio/bin/obs",
        ]
        obs_bin = next((p for p in obs_paths if Path(p).exists()), None)
        if not obs_bin:
            return False

        # Write service.json (OBS native RTMP configuration) to both KizaGuard and Untitled profiles
        service_data = {
            "type": "rtmp_custom",
            "settings": {
                "server": "rtmps://fa723fc1b171.global-contribute.live-video.net/app",
                "key": stream_key,
                "use_auth": False,
                "bwtest": False,
            }
        }

        for prof_name in ["KizaGuard", "Untitled"]:
            prof_dir = Path.home() / ".config" / "obs-studio" / "basic" / "profiles" / prof_name
            prof_dir.mkdir(parents=True, exist_ok=True)
            (prof_dir / "service.json").write_text(json.dumps(service_data, indent=2))
            basic_ini = prof_dir / "basic.ini"
            if not basic_ini.exists():
                basic_ini.write_text(
                    f"[General]\nName={prof_name}\n\n"
                    "[Output]\nMode=Simple\n\n"
                    "[SimpleOutput]\nStreamEncoder=obs_x264\nVBitrate=4500\nABitrate=192\n"
                )

        subprocess.Popen([obs_bin, "--profile", "KizaGuard", "--scene", scene])
        return True


# ------------------------------------------------------------------
# CLI entry point: python -m src.kick.stream
# ------------------------------------------------------------------

def main() -> None:
    """Bootstrap a Kick coding stream for a Kaggle challenge."""
    import os
    from dotenv import load_dotenv
    load_dotenv()

    token = os.environ.get("KICK_ACCESS_TOKEN", "")
    token_file = Path(__file__).resolve().parent.parent.parent / ".kick_token.json"
    if not token and token_file.exists():
        try:
            with open(token_file) as f:
                sdata = json.load(f)
                token = sdata.get("access_token", "")
        except Exception:
            pass

    client = KickClient(
        client_id=os.environ["KICK_CLIENT_ID"],
        access_token=token,
    )
    mgr = KickStreamManager(client)

    # 1) Update channel info
    challenge_title = "🧠 Kaggle S6 Challenge | JudgeGuard AI Live Coding Session"
    print(f"Setting channel title: {challenge_title!r} ...")
    try:
        mgr.update_channel(title=challenge_title)
        print("  ✅ Channel updated")
    except Exception as exc:
        print(f"  ⚠️  Could not update channel: {exc}")

    # 2) Get stream key
    print("Fetching stream key ...")
    try:
        key = mgr.get_stream_key()
        if key:
            obs = mgr.build_obs_profile(key)
            print("\n" + "=" * 60)
            print("  OBS RTMP Settings")
            print("=" * 60)
            print(f"  Server : {obs['rtmp_server']}")
            print(f"  Key    : {key[:8]}{'*' * (len(key) - 8)}")
            print("=" * 60)

            # 3) Try to launch OBS
            launched = mgr.launch_obs(key)
            if launched:
                print("\n  🚀 OBS launched with KizaGuard profile")
            else:
                print("\n  ℹ️  OBS not found — add settings manually:")
                print(f"      Server: {obs['rtmp_server']}")
                print(f"      Key:    {key}")
        else:
            print("  ❌ No stream key returned (check streamkey:read scope is approved in Kick Dev Console)")
    except Exception as exc:
        print(f"  ❌ Stream key error: {exc}")

    print("\n  Done. Open https://kick.com/dashboard and click Go Live!")


if __name__ == "__main__":
    main()
