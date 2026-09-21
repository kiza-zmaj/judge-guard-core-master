#!/usr/bin/env python3
"""
Interactive & Automated Kaggle Submission Tool for S6E9.
Submits candidate CSV files to playground-series-s6e9 cleanly.
"""

import sys
import os
import subprocess
from pathlib import Path

COMPETITION = "playground-series-s6e9"
CURRENT_DIR = Path(__file__).resolve().parent

# Candidate submission files to offer
CANDIDATE_PATHS = [
    CURRENT_DIR / "kaggle_kernel" / "submission_v2_ultimate.csv",
    CURRENT_DIR / "kaggle_kernel" / "submission_raw_blend.csv",
    CURRENT_DIR / "submissions" / "sub16_kernel_v2_ultimate.csv",
    CURRENT_DIR / "submissions" / "submission_10_top10_master_blend.csv",
    CURRENT_DIR / "submissions" / "submission_15_top10_master_assault.csv",
    CURRENT_DIR / "submissions" / "submission_14_multiseed_tri_engine.csv",
]


def list_and_pick_file():
    available = [p for p in CANDIDATE_PATHS if p.exists()]
    if not available:
        print("❌ Nema pronađenih submission fajlova!")
        sys.exit(1)

    # Check CLI arguments first
    if len(sys.argv) > 1:
        arg_file = Path(sys.argv[1])
        if not arg_file.is_absolute():
            arg_file = CURRENT_DIR / arg_file
        if arg_file.exists():
            return arg_file

    print("=" * 70)
    print(f"🏆 KAGGLE S6E9 SUBMISSION HELPER ({COMPETITION})")
    print("=" * 70)
    print("Dostupni submission fajlovi:")
    for idx, path in enumerate(available, 1):
        size_mb = path.stat().st_size / (1024 * 1024)
        print(f"  [{idx}] {path.relative_to(CURRENT_DIR)} ({size_mb:.2f} MB)")

    print(f"\nDefault izbor je [1]: {available[0].name}")
    choice = input("Unesi broj fajla [1] ili pritisni Enter za default: ").strip()

    if choice.isdigit() and 1 <= int(choice) <= len(available):
        return available[int(choice) - 1]
    return available[0]


def main():
    selected_file = list_and_pick_file()
    print(f"\n🎯 Izabran fajl za submission: {selected_file}")

    # Prompt or auto-generate message
    default_msg = f"Submission: {selected_file.stem} via JudgeGuard Core"
    custom_msg = input(f"Unesi opis submission-a (ili Enter za '{default_msg}'): ").strip()
    msg = custom_msg if custom_msg else default_msg

    print(f"\n📤 Šaljem na Kaggle ({COMPETITION})...")
    cmd = [
        "kaggle", "competitions", "submit",
        "-c", COMPETITION,
        "-f", str(selected_file),
        "-m", msg
    ]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"✅ {res.stdout.strip()}")
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Greška pri slanju: {e.stderr.strip()}")
        return

    print("\n📊 Proveravam status najnovijih predaja...")
    try:
        status_res = subprocess.run(
            ["kaggle", "competitions", "submissions", "-c", COMPETITION],
            capture_output=True, text=True
        )
        print(status_res.stdout)
    except Exception as ex:
        print(f"Ne mogu da dohvatim status: {ex}")


if __name__ == "__main__":
    main()
