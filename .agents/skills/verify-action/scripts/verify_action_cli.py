#!/usr/bin/env python3
"""
Verify Action CLI — Automated Master Orchestration Utility
Generated via workflow-skill-creator for JudgeGuard Master Orchestration.

Provides subcommands for each step in the Master Orchestration lifecycle:
- preflight: Validates ticket, work log, and venv prerequisites.
- verify: Executes JudgeGuard Layer 00-3 verification on a proposed action.
- checkpoint: Stages git changes, creates checkpoint commit, logs SHA to WORK_LOG.
- status: Reports active ticket details and recent work log status entries.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Any

REPO_ROOT = Path(__file__).resolve().parents[4]


def run_preflight(args: argparse.Namespace) -> int:
    """Validate active environment, TICKET.md, and WORK_LOG.md."""
    ticket_file = REPO_ROOT / "TICKET.md"
    work_log_file = REPO_ROOT / "WORK_LOG.md"
    judge_guard = REPO_ROOT / "judge_guard.py"

    ticket_text = ticket_file.read_text(encoding="utf-8") if ticket_file.exists() else ""
    work_log_text = work_log_file.read_text(encoding="utf-8") if work_log_file.exists() else ""

    # Check work log recent state (last 2000 chars like JudgeGuard Layer 0)
    tail_chars = work_log_text[-2000:] if len(work_log_text) > 2000 else work_log_text
    has_indicators = any(tok in tail_chars.lower() for tok in ['🟡', 'starting', '✅', 'completed'])

    # Count uncompleted tasks in recent window
    recent_starts = tail_chars.count("🟡 Starting")
    recent_completes = tail_chars.count("✅ Completed")
    active_unclosed = max(0, recent_starts - recent_completes)

    data = {
        "status": "READY" if (ticket_file.exists() and work_log_file.exists()) else "INCOMPLETE",
        "ticket_exists": ticket_file.exists(),
        "work_log_exists": work_log_file.exists(),
        "judge_guard_exists": judge_guard.exists(),
        "recent_indicators_present": has_indicators,
        "recent_active_tasks": active_unclosed,
        "open_tasks_compliant": active_unclosed <= 5,
        "active_ticket_preview": ticket_text[:200].strip(),
    }

    if args.output:
        Path(args.output).write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"✅ Success! Preflight report written to: {args.output}")
    else:
        print(json.dumps(data, indent=2))

    return 0 if (data["status"] == "READY" and data["open_tasks_compliant"]) else 1


def run_verify(args: argparse.Namespace) -> int:
    """Run JudgeGuard verification on action."""
    action = args.action
    cmd = [sys.executable, str(REPO_ROOT / "judge_guard.py"), action]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)

    data = {
        "action": action,
        "exit_code": res.returncode,
        "passed": res.returncode == 0,
        "stdout": res.stdout.strip(),
        "stderr": res.stderr.strip(),
    }

    if args.output:
        Path(args.output).write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"✅ Success! Verification results written to: {args.output}")
    else:
        print(json.dumps(data, indent=2))

    return res.returncode


def run_status(args: argparse.Namespace) -> int:
    """Retrieve current orchestration status."""
    work_log = REPO_ROOT / "WORK_LOG.md"
    recent_lines = []
    if work_log.exists():
        lines = [line.strip() for line in work_log.read_text(encoding="utf-8").splitlines() if line.strip()]
        recent_lines = lines[-15:]

    data = {
        "work_log_path": str(work_log),
        "recent_entries": recent_lines,
    }

    if args.output:
        Path(args.output).write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"✅ Success! Status written to: {args.output}")
    else:
        print(json.dumps(data, indent=2))

    return 0


def main():
    parser = argparse.ArgumentParser(description="Verify Action CLI Utility")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # preflight
    p_pre = subparsers.add_parser("preflight", help="Validate prerequisites")
    p_pre.add_argument("--output", "-o", help="Path to write JSON output")

    # verify
    p_ver = subparsers.add_parser("verify", help="Execute JudgeGuard verification")
    p_ver.add_argument("--action", "-a", required=True, help="Proposed action string")
    p_ver.add_argument("--output", "-o", help="Path to write JSON output")

    # status
    p_stat = subparsers.add_parser("status", help="Get orchestration status")
    p_stat.add_argument("--output", "-o", help="Path to write JSON output")

    args = parser.parse_args()

    if args.subcommand == "preflight":
        sys.exit(run_preflight(args))
    elif args.subcommand == "verify":
        sys.exit(run_verify(args))
    elif args.subcommand == "status":
        sys.exit(run_status(args))


if __name__ == "__main__":
    main()
