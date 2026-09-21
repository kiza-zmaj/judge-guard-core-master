#!/usr/bin/env python3
"""
Stream Launcher for Kick.com & OBS Studio.
Configures OBS Studio with Kick RTMP settings and launches OBS.
Works from any working directory.
"""

import os
import sys
import json
import subprocess
import webbrowser
from pathlib import Path
from dotenv import load_dotenv

# Find project root
CURRENT = Path(__file__).resolve()
if (CURRENT.parent / ".env").exists():
    PROJECT_ROOT = CURRENT.parent
elif (CURRENT.parent.parent / ".env").exists():
    PROJECT_ROOT = CURRENT.parent.parent
elif (CURRENT.parent.parent.parent / ".env").exists():
    PROJECT_ROOT = CURRENT.parent.parent.parent
else:
    PROJECT_ROOT = Path("/home/kizamladjanijebac/Documents/jude guard/judge-guard-core-master")

ENV_FILE = PROJECT_ROOT / ".env"
if ENV_FILE.exists():
    load_dotenv(dotenv_path=ENV_FILE)

RTMP_SERVER = "rtmps://fa723fc1b171.global-contribute.live-video.net/app"


def setup_obs_profile(stream_key: str):
    """Write OBS native service.json with Kick RTMP server and key."""
    service_data = {
        "type": "rtmp_custom",
        "settings": {
            "server": RTMP_SERVER,
            "key": stream_key.strip(),
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
                "[Video]\nBaseCX=1920\nBaseCY=1080\nOutputCX=1920\nOutputCY=1080\nFPSCommon=60\nScaleType=lanczos\n\n"
                "[Output]\nMode=Advanced\nDelayEnable=false\nLowLatencyEnable=true\n\n"
                "[AdvOut]\nEncoder=obs_x264\nTrack1Bitrate=192\n\n"
                "[Encoder]\nrate_control=CBR\nbitrate=6000\nbuffer_size=6000\nkeyint_sec=2\npreset=veryfast\ntune=zerolatency\nprofile=main\n\n"
                "[Audio]\nSampleRate=48000\nChannelSetup=Stereo\n"
            )


def launch_obs():
    """Launch OBS Studio."""
    obs_paths = ["/usr/bin/obs", "/usr/local/bin/obs", "/snap/bin/obs-studio"]
    obs_bin = next((p for p in obs_paths if Path(p).exists()), "obs")
    print(f"🚀 Launching OBS Studio ({obs_bin})...")
    obs_env = os.environ.copy()
    obs_env["QT_QPA_PLATFORM"] = "xcb"
    obs_env["DISPLAY"] = obs_env.get("DISPLAY", ":0")
    return subprocess.Popen([obs_bin, "--profile", "KizaGuard"], env=obs_env)


def main():
    print("=" * 65)
    print("📺 KICK LIVE STREAM LAUNCHER — JUDGEGUARD AI")
    print("=" * 65)

    stream_key = os.environ.get("KICK_STREAM_KEY", "").strip()

    # Check if stream key is already saved
    if not stream_key:
        print("\n⚠️  KICK_STREAM_KEY nije pronađen u .env")
        print("Kick stream key se nalazi na Creator Dashboard-u:")
        print("🔗 https://kick.com/dashboard/settings/stream\n")

        # Open dashboard in browser
        try:
            webbrowser.open("https://kick.com/dashboard/settings/stream")
        except Exception:
            pass

        user_input = input("👉 Nalepi svoj Kick Stream Key ovde (ili pritisni Enter za nastavak ako si ga već uneo): ").strip()
        if user_input:
            stream_key = user_input
            # Append/update .env
            with open(ENV_FILE, "a") as f:
                f.write(f"\nKICK_STREAM_KEY={stream_key}\n")
            print("✅ KICK_STREAM_KEY sačuvan u .env!")

    if stream_key:
        setup_obs_profile(stream_key)
        print("✅ OBS Studio podešen sa Kick RTMP serverom i Stream Key-om.")
    else:
        print("⚠️ Pokrećem OBS bez novog ključa (koristiće postojeći OBS profil).")

    launch_obs()
    print("\n" + "=" * 65)
    print("🎬 OBS JE POKRENUT!")
    print("U OBS-u samo klikni na: [ Start Streaming ]")
    print("Kaggle Challenge: playground-series-s6e9 (EV Purchase Prediction)")
    print("=" * 65)


if __name__ == "__main__":
    main()
