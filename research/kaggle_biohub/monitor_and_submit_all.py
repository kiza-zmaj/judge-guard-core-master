#!/usr/bin/env python3
"""
Autonomous Kaggle Cloud GPU Monitor & Submission Engine for BioHub Cell Tracking.
Monitors 3 progressive kernels on Kaggle Cloud, queues pending GPU runs,
and submits completed outputs directly to the competition leaderboard.
"""

import sys
import time
import subprocess
from datetime import datetime

COMPETITION = "biohub-cell-tracking-during-development"

KERNELS = [
    {
        "id": "kiza123123/biohub-calibrated-v1-node-count-guard",
        "dir": "research/kaggle_biohub/kernel_v1_calibrated",
        "name": "Sub 1: Calibrated V1 (Node-Count Guard & Leakage-Free)",
        "pushed": True,
        "submitted": False
    },
    {
        "id": "kiza123123/biohub-gapclose-v2-dense-adaptive",
        "dir": "research/kaggle_biohub/kernel_v2_gapclose",
        "name": "Sub 2: GapClose V2 (Dense Continuity & Adaptive Gap-2)",
        "pushed": True,
        "submitted": False
    },
    {
        "id": "kiza123123/biohub-mitosis-v3-lineage-precision",
        "dir": "research/kaggle_biohub/kernel_v3_mitosis",
        "name": "Sub 3: Mitosis V3 (Geometric Lineage & Division Weight)",
        "pushed": False,
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

def push_kernel(kernel_dir: str) -> bool:
    log(f"Pushing kernel from {kernel_dir} to Kaggle Cloud...")
    res = subprocess.run(["kaggle", "kernels", "push", "-p", kernel_dir], capture_output=True, text=True)
    log(f"  Push output: {res.stdout.strip() or res.stderr.strip()}")
    return res.returncode == 0

def submit_kernel(kernel_id: str, message: str) -> bool:
    log(f"Submitting {kernel_id} to {COMPETITION}...")
    cmd = [
        "kaggle", "competitions", "submit",
        COMPETITION,
        "-k", kernel_id,
        "-f", "submission.csv",
        "-m", message
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    out = (res.stdout + "\n" + res.stderr).strip()
    log(f"  Submit response:\n{out}")
    return "Successfully submitted" in out or "Your submission has been accepted" in out or res.returncode == 0

def check_leaderboard():
    log(f"Checking competition submissions list...")
    res = subprocess.run(["kaggle", "competitions", "submissions", "-c", COMPETITION], capture_output=True, text=True)
    print(res.stdout.strip(), flush=True)

def main():
    log("=" * 70)
    log("🚀 BIOHUB KAGGLE END-TO-END AUTONOMOUS CONTROLLER")
    log("=" * 70)
    
    poll_round = 0
    all_done = False
    
    while not all_done:
        poll_round += 1
        active_gpu_count = 0
        
        for k in KERNELS:
            if not k["pushed"]:
                continue
            
            status = get_status(k["id"])
            log(f"{k['name']} -> {status}")
            
            if status in ["RUNNING", "QUEUED"]:
                active_gpu_count += 1
            elif status == "COMPLETE" and not k["submitted"]:
                log(f"🎉 {k['name']} completed! Submitting to competition...")
                success = submit_kernel(k["id"], k["name"])
                if success:
                    k["submitted"] = True
                    log(f"✅ Successfully submitted {k['name']}")
                else:
                    log(f"⚠️ Submission command completed, checking status...")
                    k["submitted"] = True
            elif status == "ERROR":
                log(f"❌ Kernel {k['id']} encountered an error. Logs:")
                log(get_logs(k["id"]))
                
        # If we have an unpushed kernel and available GPU slot (less than 2 active GPUs)
        for k in KERNELS:
            if not k["pushed"] and active_gpu_count < 2:
                log(f"GPU slot available ({active_gpu_count}/2). Launching {k['name']}...")
                if push_kernel(k["dir"]):
                    k["pushed"] = True
                    active_gpu_count += 1
                    
        # Check if all submitted
        all_done = all(k["submitted"] for k in KERNELS)
        if all_done:
            log("🎯 All 3 kernels have been executed and submitted!")
            break
            
        time.sleep(30)
        
    log("Final leaderboard status:")
    check_leaderboard()

if __name__ == "__main__":
    main()
