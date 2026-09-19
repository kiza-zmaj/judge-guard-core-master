#!/usr/bin/env python3
"""
Cloud Kernel Poller & Automated Submission Pipeline.
Monitors Kaggle Cloud GPU kernel execution, pulls generated submissions,
verifies integrity via JudgeGuard, and submits all 5 tiers to Kaggle.
"""

import os
import sys
import time
import subprocess
from pathlib import Path

# Add src to path
SRC_DIR = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(SRC_DIR))

from config import SAMPLE_SUB_PATH, SUBMISSIONS_DIR
from verify_submission import verify_submission_file

KERNEL_ID = "kiza123123/s6e9-generator-forensics-5-submission-pipeline"
COMPETITION_ID = "playground-series-s6e9"

def check_kernel_status() -> str:
    cmd = ["kaggle", "kernels", "status", KERNEL_ID]
    res = subprocess.run(cmd, capture_output=True, text=True)
    out = res.stdout.strip()
    return out

def get_kernel_logs() -> str:
    cmd = ["kaggle", "kernels", "logs", KERNEL_ID]
    res = subprocess.run(cmd, capture_output=True, text=True)
    return res.stdout.strip()

def download_kernel_outputs() -> bool:
    print(f"\n📥 [Kaggle CLI] Downloading kernel outputs from {KERNEL_ID}...")
    cmd = ["kaggle", "kernels", "output", KERNEL_ID, "-p", str(SUBMISSIONS_DIR)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print(f"  {res.stdout.strip()}")
    return res.returncode == 0

def submit_to_competition(file_path: Path, message: str) -> bool:
    print(f"\n📤 [JudgeGuard -> Kaggle] Submitting {file_path.name}...")
    cmd = [
        "kaggle", "competitions", "submit",
        "-c", COMPETITION_ID,
        "-f", str(file_path),
        "-m", message
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"  ✅ {res.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ⚠️ Submission error: {e.stderr.strip()}")
        return False

def print_leaderboard_status():
    print(f"\n📊 [Kaggle Submissions Status] Checking recent submissions for {COMPETITION_ID}...")
    cmd = ["kaggle", "competitions", "submissions", "-c", COMPETITION_ID]
    res = subprocess.run(cmd, capture_output=True, text=True)
    lines = res.stdout.strip().split("\n")
    for line in lines[:15]:
        print(f"  {line}")

def main():
    print("=" * 80)
    print("☁️ KAGGLE CLOUD KERNEL MONITOR & SUBMISSION ENGINE")
    print(f"Kernel ID: {KERNEL_ID}")
    print("=" * 80)
    
    poll_count = 0
    while True:
        status_str = check_kernel_status()
        poll_count += 1
        print(f"[{time.strftime('%H:%M:%S')}] Attempt {poll_count}: {status_str}")
        
        if "COMPLETE" in status_str:
            print("\n🎉 Kernel execution COMPLETED on Kaggle Cloud GPU!")
            break
        elif "ERROR" in status_str or "FAILED" in status_str:
            print(f"\n🛑 Kernel execution FAILED! Logs:")
            print(get_kernel_logs())
            sys.exit(1)
        elif "CANCELLED" in status_str:
            print("\n⚠️ Kernel was cancelled.")
            sys.exit(1)
            
        time.sleep(30)
        
    # Download output files
    if not download_kernel_outputs():
        print("Failed to download kernel outputs.")
        sys.exit(1)
        
    # Verify and submit all 5 submission files for Round 2 (Top 10 Assault)
    submission_files = [
        ("submission_6_xgb_triple_te.csv", "Sub 6: Lossguide XGBoost with Triple Target Encoding (Najiama ~0.94639)"),
        ("submission_7_xgb_recipe_base_margin.csv", "Sub 7: Lossguide XGBoost + Chris Deotte Recipe base_margin (Top 10 Target)"),
        ("submission_8_lgbm_triple_te_init_score.csv", "Sub 8: LightGBM Triple TE with Recipe init_score"),
        ("submission_9_catboost_triple_te.csv", "Sub 9: CatBoost Oblivious Trees on Triple TE Features"),
        ("submission_10_top10_master_blend.csv", "Sub 10: Master Rank Nelder-Mead Blend (Top 10 Target >=0.94670)")
    ]
    
    for filename, message in submission_files:
        file_path = SUBMISSIONS_DIR / filename
        if file_path.exists():
            verify_submission_file(file_path, SAMPLE_SUB_PATH)
            submit_to_competition(file_path, message)
            time.sleep(5)
        else:
            print(f"⚠️ Warning: File {filename} not found in outputs directory.")
            
    # Final check of leaderboard status
    time.sleep(15)
    print_leaderboard_status()

if __name__ == "__main__":
    main()
