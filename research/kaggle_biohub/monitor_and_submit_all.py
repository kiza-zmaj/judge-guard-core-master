#!/usr/bin/env python3
"""
Autonomous Kaggle Cloud GPU Monitor & Submission Engine for BioHub Cell Tracking.
Monitors Kernel 2 and Kernel 3 on Kaggle Cloud, submits them as soon as they complete,
and continuously polls the official Kaggle Leaderboard until final scores are recorded.
"""

import sys
import time
import subprocess
from datetime import datetime

COMPETITION = "biohub-cell-tracking-during-development"

KERNELS = [
    {
        "id": "kiza123123/biohub-gapclose-v2-dense-adaptive",
        "name": "Sub 2: GapClose V2 (Dense Continuity & Adaptive Gap-2)",
        "version": "3",
        "submitted": False
    },
    {
        "id": "kiza123123/biohub-mitosis-v3-lineage-precision",
        "name": "Sub 3: Mitosis V3 (Geometric Lineage & Division Weight)",
        "version": "3",
        "submitted": False
    }
]

def log(msg: str):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)

def get_status(kernel_id: str) -> str:
    res = subprocess.run(["kaggle", "kernels", "status", kernel_id], capture_output=True, text=True)
    out = res.stdout.strip()
    if "COMPLETE" in out:
        return "COMPLETE"
    elif "RUNNING" in out:
        return "RUNNING"
    elif "QUEUED" in out:
        return "QUEUED"
    elif "ERROR" in out or "FAILED" in out:
        return "ERROR"
    return out

def get_logs(kernel_id: str) -> str:
    res = subprocess.run(["kaggle", "kernels", "logs", kernel_id], capture_output=True, text=True)
    return res.stdout.strip()

def submit_kernel(kernel_id: str, version: str, message: str) -> bool:
    log(f"Submitting {kernel_id} (version {version}) to {COMPETITION}...")
    cmd = [
        "kaggle", "competitions", "submit",
        COMPETITION,
        "-k", kernel_id,
        "-v", version,
        "-f", "submission.csv",
        "-m", message
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    out = (res.stdout + "\n" + res.stderr).strip()
    log(f"  Submit response:\n{out}")
    return "remaining today" in out or "Successfully submitted" in out or res.returncode == 0

def check_leaderboard():
    log(f"Checking competition submissions list...")
    res = subprocess.run(["kaggle", "competitions", "submissions", "-c", COMPETITION], capture_output=True, text=True)
    print(res.stdout.strip(), flush=True)

def main():
    log("=" * 70)
    log("🚀 BIOHUB KAGGLE END-TO-END AUTONOMOUS CONTROLLER (ACTIVE)")
    log("=" * 70)
    
    poll_round = 0
    while True:
        poll_round += 1
        all_submitted = True
        
        for k in KERNELS:
            if k["submitted"]:
                continue
            
            all_submitted = False
            status = get_status(k["id"])
            log(f"{k['name']} -> {status}")
            
            if status == "COMPLETE":
                log(f"🎉 {k['name']} COMPLETED! Submitting to Kaggle Leaderboard...")
                success = submit_kernel(k["id"], k["version"], k["name"])
                k["submitted"] = True
                log(f"✅ Submission status updated for {k['name']}")
            elif status == "ERROR":
                log(f"❌ Kernel {k['id']} encountered an error. Logs:")
                log(get_logs(k["id"]))
                k["submitted"] = True  # Avoid infinite error loop
                
        if all_submitted:
            log("🎯 All targeted kernels have been processed!")
            break
            
        check_leaderboard()
        time.sleep(30)
        
    log("Final leaderboard status:")
    check_leaderboard()

if __name__ == "__main__":
    main()
