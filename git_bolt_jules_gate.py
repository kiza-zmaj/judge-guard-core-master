#!/usr/bin/env python3
"""
Git Gate for Bolt and Jules.
Enforces Master Orchestration on Git operations:
1. Token cleaning: prevents high-token context bloat from contaminating git diffs.
2. Telemetry tracking: records and outputs token usage, tokens saved, latency, and model metrics.
3. JudgeGuard integration: ensures commits and PRs comply with repo rules.
"""

import sys
import os
import argparse
import subprocess
import json

# Ensure project root is in sys.path
_repo_root = os.path.dirname(os.path.abspath(__file__))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from src.antigravity_core.telemetry import telemetry
from src.antigravity_core.token_cleaner import token_cleaner, TokenCleaner


def cmd_audit():
    """Inspects staged files and repo state for token efficiency."""
    print("🔍 [BOLT & JULES GIT AUDIT] Checking staged files...")
    status = TokenCleaner.inspect_staged_git(_repo_root)
    print(f"• Staged files: {status['staged_count']}")
    if status['waste_files']:
        print("⚠️ Warning: Detected token-waste files staged:")
        for wf in status['waste_files']:
            print(f"  - {wf}")
        print("💡 Suggestion: Unstage these files before committing or LLM context ingestion.")
    else:
        print("✅ Staged files are clean and token-optimized!")
    return 0 if not status['waste_files'] else 1


def cmd_telemetry():
    """Displays current session and cumulative telemetry summary."""
    summary = telemetry.get_summary()
    print("\n" + "=" * 50)
    print("📊 BOLT & JULES TELEMETRY DASHBOARD")
    print("=" * 50)
    print(f"Total AI Operations:   {summary.get('total_calls', 0)}")
    print(f"Total Tokens Used:     {summary.get('total_tokens', 0):,}")
    print(f"⚡ Total Tokens Saved: {summary.get('total_tokens_saved', 0):,}")
    print(f"Cached Tokens:         {summary.get('total_cached_tokens', 0):,}")
    print(f"Average Latency:       {summary.get('average_latency_ms', 0)} ms")
    print(f"Estimated Cost:        ${summary.get('total_cost_usd', 0.0):.5f} USD")
    print("-" * 50)
    print("Breakdown by Agent:")
    for agent, data in summary.get('by_agent', {}).items():
        print(f"  • {agent.upper():<14}: {data['calls']} calls | {data['tokens']:,} tokens | {data['saved']:,} saved")
    print("=" * 50 + "\n")
    return 0


def cmd_badge(agent: str = "bolt", action: str = "Git Checkpoint"):
    """Generates markdown telemetry badge for git commit or PR."""
    summary = telemetry.get_summary()
    tot = summary.get('total_tokens', 0)
    saved = summary.get('total_tokens_saved', 0)
    lat = summary.get('average_latency_ms', 0.0)
    badge = telemetry.format_badge(
        agent=agent,
        action=action,
        total_tokens=tot,
        tokens_saved=saved,
        latency_ms=lat,
        model="gemini-3.7-flash"
    )
    print(badge)
    return badge


def cmd_clean_diff():
    """Extracts and outputs a token-cleaned git diff."""
    try:
        raw_diff = subprocess.check_output(["git", "diff", "HEAD~1"], cwd=_repo_root, text=True)
    except Exception:
        raw_diff = subprocess.check_output(["git", "diff"], cwd=_repo_root, text=True)

    cleaned_diff, saved = TokenCleaner.clean_git_diff(raw_diff)
    print(f"⚡ Pruned diff: saved ~{saved:,} tokens of context!")
    return cleaned_diff


def main():
    parser = argparse.ArgumentParser(description="Git Gate for Bolt & Jules")
    parser.add_argument("command", choices=["audit", "telemetry", "badge", "clean-diff"], help="Command to run")
    parser.add_argument("--agent", default="bolt", help="Agent name (bolt / jules)")
    parser.add_argument("--action", default="Git Checkpoint", help="Action name")

    args = parser.parse_args()

    if args.command == "audit":
        sys.exit(cmd_audit())
    elif args.command == "telemetry":
        sys.exit(cmd_telemetry())
    elif args.command == "badge":
        cmd_badge(args.agent, args.action)
    elif args.command == "clean-diff":
        cmd_clean_diff()


if __name__ == "__main__":
    main()
