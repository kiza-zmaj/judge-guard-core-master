#!/usr/bin/env python3
"""
SharpBet v12 Kaggle Runner
===========================
Lightweight CLI to:
  1. Generate the v12 Kaggle notebook (if not already present)
  2. Push the notebook as a Kaggle Kernel
  3. Poll kernel execution until complete
  4. Pull gate_verdicts.json artifact back to local workspace

Usage:
    python3 unified_betting_core/runners/run_kaggle_v12.py --push-and-monitor
    python3 unified_betting_core/runners/run_kaggle_v12.py --verify-env
    python3 unified_betting_core/runners/run_kaggle_v12.py --generate-only

Disk budget: Kernel metadata ≤ 5 KB, output artifacts ≤ 500 KB.
All heavy computation offloaded to Kaggle Cloud GPU.
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional

# ── Path bootstrap ─────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.kaggle_stream.kaggle_cli_runner import KaggleCLIRunner  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("run_kaggle_v12")

# ── Constants ──────────────────────────────────────────────────────────────────
KERNEL_SLUG        = "sharpbet-v12-halftime-goals-audit"
KAGGLE_DISPLAY_URL = "https://www.kaggle.com/code/kiza123123/sharpbet-v12-halftime-goals-audit"
# NOTE: Kaggle public username for kernel URL is 'kiza123123'; credentials username is 'kizabgd123'
# The kernel push API resolves the correct display username automatically.
NOTEBOOK_ROOT_PATH = PROJECT_ROOT / "sharpbet-v12-halftime-goals-audit.ipynb"
KERNEL_META_PATH   = PROJECT_ROOT / "kernel-metadata.json"
OUTPUT_DIR         = PROJECT_ROOT / "kaggle_pulled_kernel"
MAX_POLL_SECONDS   = 600   # 10 minutes max polling
POLL_INTERVAL      = 20    # seconds between status checks
MAX_OUTPUT_BYTES   = 500_000  # 500 KB disk cap for pulled artifacts


# ── Helper Functions ───────────────────────────────────────────────────────────

def generate_notebook_if_needed() -> bool:
    """Generate v12 notebook via generate_kaggle_v12.py if not already present."""
    if NOTEBOOK_ROOT_PATH.exists() and NOTEBOOK_ROOT_PATH.stat().st_size > 1000:
        logger.info(f"✅ Notebook already present: {NOTEBOOK_ROOT_PATH.name} "
                    f"({NOTEBOOK_ROOT_PATH.stat().st_size // 1024} KB)")
        return True

    logger.info("🔨 Generating v12 notebook...")
    gen_script = PROJECT_ROOT / "unified_betting_core" / "generate_kaggle_v12.py"
    result = subprocess.run(
        [sys.executable, str(gen_script)],
        cwd=str(PROJECT_ROOT),
        capture_output=True, text=True
    )
    if result.returncode != 0:
        logger.error(f"Notebook generation FAILED:\n{result.stderr}")
        return False
    logger.info(result.stdout.strip())
    return NOTEBOOK_ROOT_PATH.exists()


def write_kernel_metadata(username: str) -> Path:
    """Write Kaggle kernel-metadata.json required for `kaggle kernels push`."""
    metadata = {
        "id": f"{username}/{KERNEL_SLUG}",
        "title": "SharpBet v12 Halftime Goals Audit",
        "code_file": str(NOTEBOOK_ROOT_PATH),
        "language": "python",
        "kernel_type": "notebook",
        "is_private": "true",
        "enable_gpu": "true",
        "enable_internet": "true",
        "dataset_sources": [],
        "competition_sources": [],
        "kernel_sources": []
    }
    with open(KERNEL_META_PATH, "w") as f:
        json.dump(metadata, f, indent=2)
    logger.info(f"📝 Kernel metadata written to {KERNEL_META_PATH}")
    return KERNEL_META_PATH


def push_kernel(username: str) -> bool:
    """Push the notebook to Kaggle as a kernel."""
    write_kernel_metadata(username)

    cmd = ["kaggle", "kernels", "push", "-p", str(PROJECT_ROOT)]
    logger.info(f"🚀 Pushing kernel: {' '.join(cmd)}")

    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"Push FAILED:\n{result.stderr}\n{result.stdout}")
        return False

    logger.info(f"✅ Push successful: {result.stdout.strip()}")
    return True


def poll_kernel_status(username: str, max_seconds: int = MAX_POLL_SECONDS) -> Dict[str, Any]:
    """Poll Kaggle kernel status until complete or timeout."""
    kernel_ref = f"{username}/{KERNEL_SLUG}"
    cmd = ["kaggle", "kernels", "status", kernel_ref]
    start = time.time()

    logger.info(f"⏳ Polling kernel status for {kernel_ref} (max {max_seconds}s)...")

    while (time.time() - start) < max_seconds:
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = (result.stdout + result.stderr).strip().lower()

        if "complete" in output or "success" in output:
            logger.info("✅ Kernel execution COMPLETE.")
            return {"status": "COMPLETE", "output": output, "elapsed": int(time.time() - start)}
        elif "error" in output or "fail" in output:
            logger.error(f"❌ Kernel execution FAILED: {output}")
            return {"status": "FAILED", "output": output, "elapsed": int(time.time() - start)}
        elif "running" in output or "queued" in output or "pending" in output:
            elapsed = int(time.time() - start)
            logger.info(f"  [{elapsed}s] Status: running/queued — waiting {POLL_INTERVAL}s...")
            time.sleep(POLL_INTERVAL)
        else:
            # Unknown state — log and keep polling
            logger.info(f"  Status unknown ('{output[:80]}') — continuing poll...")
            time.sleep(POLL_INTERVAL)

    return {"status": "TIMEOUT", "output": "", "elapsed": max_seconds}


def pull_kernel_output(username: str) -> Dict[str, Any]:
    """Pull output files from Kaggle kernel, respecting the 500 KB disk budget."""
    kernel_ref = f"{username}/{KERNEL_SLUG}"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    cmd = ["kaggle", "kernels", "output", kernel_ref, "-p", str(OUTPUT_DIR)]
    logger.info(f"📥 Pulling kernel output to {OUTPUT_DIR}...")

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.warning(f"Output pull returned non-zero: {result.stderr.strip()}")

    pulled_files = []
    total_bytes = 0

    for f in sorted(OUTPUT_DIR.iterdir()):
        if f.is_file():
            size = f.stat().st_size
            if total_bytes + size > MAX_OUTPUT_BYTES:
                logger.warning(f"  ⚠ Skipping {f.name} — would exceed 500 KB disk budget")
                f.unlink()
                continue
            total_bytes += size
            pulled_files.append(str(f))
            logger.info(f"  ✅ Pulled: {f.name} ({size // 1024} KB)")

    return {
        "pulled_files": pulled_files,
        "total_bytes": total_bytes,
        "output_dir": str(OUTPUT_DIR)
    }


def display_gate_verdicts() -> None:
    """Parse and display gate_verdicts.json from pulled kernel output."""
    verdict_paths = list(OUTPUT_DIR.glob("gate_verdicts.json"))
    if not verdict_paths:
        # Also check project root (fallback from local run)
        verdict_paths = list(PROJECT_ROOT.glob("gate_verdicts.json"))

    if not verdict_paths:
        logger.warning("⚠ gate_verdicts.json not found in output — kernel may not have completed.")
        return

    with open(verdict_paths[0]) as f:
        v = json.load(f)

    print("\n" + "="*70)
    print("🛡️  SHARPBET v12 THREE-GATE GOVERNANCE AUDIT RESULTS")
    print("="*70)
    print(f"  Pipeline Version : {v.get('pipeline_version', 'N/A')}")

    ga = v.get("gate_a_calibration", {})
    print(f"  Gate A (Calibration)  : {ga.get('status','?'):8s} | "
          f"ECE={ga.get('ece', 0):.2%}  Brier={ga.get('brier', 0):.4f}")

    gb = v.get("gate_b_market_alpha", {})
    print(f"  Gate B (Market Alpha) : {gb.get('status','?'):8s} | "
          f"Mean Fair CLV={gb.get('mean_clv', 0):.2%}")

    gc = v.get("gate_c_economics", {})
    print(f"  Gate C (Economics)    : {gc.get('status','?'):8s} | "
          f"ROI={gc.get('roi', 0):.2%}  Bets={gc.get('bets', 0)}")

    final = v.get("final_verdict", "UNKNOWN")
    icon = "✅" if final == "APPROVED" else "🛑"
    print(f"\n  {icon} FINAL VERDICT: {final}")
    print("="*70 + "\n")


# ── Main CLI ───────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="SharpBet v12 Kaggle Kernel Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument("--push-and-monitor", action="store_true",
                        help="Generate notebook, push to Kaggle, poll status, pull results.")
    parser.add_argument("--verify-env", action="store_true",
                        help="Check Kaggle credentials and CLI availability.")
    parser.add_argument("--generate-only", action="store_true",
                        help="Generate the v12 notebook locally without pushing.")
    parser.add_argument("--show-verdicts", action="store_true",
                        help="Display gate verdicts from the last pulled kernel output.")
    return parser.parse_args()


def main():
    args = parse_args()
    runner = KaggleCLIRunner()

    if args.verify_env:
        env = runner.check_environment()
        if env["ready"]:
            print(f"✅ Kaggle environment READY — username: {env['username']}")
        else:
            print(f"❌ Kaggle environment NOT READY — {env.get('message', env.get('status'))}")
        return

    if args.generate_only:
        ok = generate_notebook_if_needed()
        if ok:
            print(f"✅ Notebook ready at: {NOTEBOOK_ROOT_PATH}")
        else:
            print("❌ Notebook generation FAILED.")
            sys.exit(1)
        return

    if args.show_verdicts:
        display_gate_verdicts()
        return

    if args.push_and_monitor:
        # ── Step 1: Verify Kaggle environment ──
        env = runner.check_environment()
        if not env["ready"]:
            logger.error(f"Kaggle not ready: {env.get('message', env.get('status'))}")
            sys.exit(1)
        username = env["username"]
        logger.info(f"✅ Kaggle authenticated as: {username}")

        # ── Step 2: Generate notebook ──
        ok = generate_notebook_if_needed()
        if not ok:
            logger.error("Notebook generation failed — aborting.")
            sys.exit(1)

        # ── Step 3: Push kernel ──
        pushed = push_kernel(username)
        if not pushed:
            logger.error("Kernel push failed — check kaggle CLI config.")
            sys.exit(1)

        # ── Step 4: Poll status ──
        status = poll_kernel_status(username)
        logger.info(f"Kernel final status: {status['status']} (elapsed: {status['elapsed']}s)")

        if status["status"] not in ("COMPLETE", "TIMEOUT"):
            logger.warning("Kernel did not complete successfully.")

        # ── Step 5: Pull outputs ──
        pull_result = pull_kernel_output(username)
        logger.info(f"Pulled {len(pull_result['pulled_files'])} files "
                    f"({pull_result['total_bytes'] // 1024} KB total)")

        # ── Step 6: Display verdicts ──
        display_gate_verdicts()

        print(f"\n🏁 Run complete. Artifacts saved to: {OUTPUT_DIR}")
        return

    # No args — print help
    parse_args().print_help() if hasattr(parse_args(), 'print_help') else None


if __name__ == "__main__":
    main()
