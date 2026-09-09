#!/usr/bin/env python3
"""
NotebookLM Orchestrator Agent v1.0
===================================
Autonomous orchestrator for NotebookLM pitch preparation and content generation.
Wraps the `nlm` CLI as the "Brain" (Source of Truth).

Usage:
    python3 nlm_orchestrator.py query   <notebook_id> "question"
    python3 nlm_orchestrator.py status  <notebook_id>
    python3 nlm_orchestrator.py fetch   <notebook_id> [--output DIR] [--convert-mp3]
    python3 nlm_orchestrator.py pipeline <notebook_id> "question" [--generate report,audio] [--fetch]

Authority: MASTER_ORCHESTRATION.md
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent
WORK_LOG = PROJECT_ROOT / "WORK_LOG.md"
DEFAULT_EXPORT_DIR = PROJECT_ROOT / "exports" / "general"
NLM_BIN = "nlm"  # Assumes nlm is on PATH

# Known notebook aliases for convenience
NOTEBOOK_ALIASES = {
    "pitch":         "7c85c185-28bb-4585-b77f-987d3f3dabfb",
    "nexus-rag":     "83fc213b-0684-4251-8980-42e0610a6742",
    "pitch-nexus":   "83fc213b-0684-4251-8980-42e0610a6742",
    "linkedin":      "4f6b5323-3465-4071-851d-e153416be6d3",
    "nexus":         "4f6b5323-3465-4071-851d-e153416be6d3",
    "elegant-franklin": "4f6b5323-3465-4071-851d-e153416be6d3",
    "fk-sava-45":    "3d33925e-5929-445b-8870-25f3dc23bf2b",
    "fine-tuning":   "eeb2676d-bd7f-4e73-a29b-38c43b9359d1",
    "web-ui":         "04ca32da-7d57-4722-889c-e85a89053051",
    "orchestration": "accc0826-6eed-456a-8b3f-5aab8d1496b8",
    "e2e-web":        "56a8e99f-ab95-4d7e-b076-66ba11595101",
    "business":       "baa27d6f-25f4-4b66-afcc-ded160bf146d",
    "openwebui":      "2e9ea5b4-e16e-4374-a2e1-22919f82e7da",
    "ai-coaching":    "f0e758cb-0897-46ea-9c84-330ad01597ee",
}

# Artifact types the nlm CLI can download (normalized for hyphen and underscore)
DOWNLOADABLE_ARTIFACTS = {
    "audio":       {"cmd": "audio",      "ext": ".m4a"},
    "video":       {"cmd": "video",      "ext": ".mp4"},
    "report":      {"cmd": "report",     "ext": ".md"},
    "slide-deck":  {"cmd": "slide-deck", "ext": ".pdf"},
    "slide_deck":  {"cmd": "slide-deck", "ext": ".pdf"},
    "infographic": {"cmd": "infographic","ext": ".png"},
    "flashcards":  {"cmd": "flashcards", "ext": ".json"},
    "mind-map":    {"cmd": "mind-map",   "ext": ".json"},
    "mind_map":    {"cmd": "mind-map",   "ext": ".json"},
    "data-table":  {"cmd": "data-table", "ext": ".csv"},
    "data_table":  {"cmd": "data-table", "ext": ".csv"},
    "quiz":        {"cmd": "quiz",       "ext": ".json"},
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def log_work(message: str) -> None:
    """Append a timestamped entry to WORK_LOG.md."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(WORK_LOG, "a") as f:
        f.write(f"{message}\n")


def resolve_notebook_id(identifier: str) -> str:
    """Resolve a notebook alias to its UUID, or return the identifier as-is."""
    return NOTEBOOK_ALIASES.get(identifier.lower(), identifier)


def run_nlm(args: list, timeout: int = 120) -> subprocess.CompletedProcess:
    """Execute an nlm CLI command and return the result."""
    cmd = [NLM_BIN] + args
    print(f"🔧 Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(PROJECT_ROOT),
        )
        return result
    except subprocess.TimeoutExpired:
        print(f"⏰ Command timed out after {timeout}s: {' '.join(cmd)}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"❌ nlm CLI not found. Install it first: pip install notebooklm-tools")
        sys.exit(1)


def print_header(title: str) -> None:
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


# ---------------------------------------------------------------------------
# Core Actions
# ---------------------------------------------------------------------------

def cmd_query(notebook_id: str, question: str, json_output: bool = False) -> str:
    """
    Query the NotebookLM Brain.
    Protocol A from System Instructions.
    """
    print_header(f"🧠 Querying Brain: {notebook_id[:12]}...")
    log_work(f"🟡 Starting [NLM Query]: \"{question[:60]}...\"")

    args = ["notebook", "query", notebook_id, question]
    if json_output:
        args.append("--json")

    result = run_nlm(args, timeout=120)

    if result.returncode != 0:
        error_msg = result.stderr.strip()
        if "NOT_FOUND" in error_msg:
            print(f"❌ Notebook not found: {notebook_id}")
            print(f"   Hint: Double-check the notebook_id. Use 'nlm notebook list' to see available notebooks.")
        else:
            print(f"❌ Query failed: {error_msg}")
        log_work(f"🛑 Blocked [NLM Query]: {error_msg[:80]}")
        return ""

    answer = result.stdout.strip()
    print(f"\n📝 Answer:\n{answer}\n")
    log_work(f"✅ Completed [NLM Query]: \"{question[:60]}...\"")
    return answer


def cmd_status(notebook_id: str) -> list:
    """
    Check studio artifact status.
    Protocol B from System Instructions.
    """
    print_header(f"📊 Studio Status: {notebook_id[:12]}...")

    result = run_nlm(["studio", "status", notebook_id], timeout=30)

    if result.returncode != 0:
        print(f"❌ Status check failed: {result.stderr.strip()}")
        return []

    try:
        artifacts = json.loads(result.stdout)
    except json.JSONDecodeError:
        # Fallback: print raw output
        print(result.stdout)
        return []

    if not artifacts:
        print("📭 No studio artifacts found for this notebook.")
        return []

    # Pretty-print status table
    print(f"{'Type':<15} {'Status':<12} {'ID':<38}")
    print(f"{'-'*15} {'-'*12} {'-'*38}")
    for a in artifacts:
        status_icon = "✅" if a.get("status") == "completed" else "⏳"
        print(f"{a.get('type', '?'):<15} {status_icon} {a.get('status', '?'):<10} {a.get('id', '?')[:36]}")

    completed = [a for a in artifacts if a.get("status") == "completed"]
    print(f"\n📈 {len(completed)}/{len(artifacts)} artifacts completed")
    return artifacts


def cmd_fetch(notebook_id: str, output_dir: str, convert_mp3: bool = True) -> list:
    """
    Download all completed artifacts.
    Protocol C from System Instructions.
    """
    print_header(f"📥 Fetching Artifacts: {notebook_id[:12]}...")
    log_work(f"🟡 Starting [NLM Fetch]: notebook={notebook_id[:12]}...")

    # Step 1: Check status first (MANDATORY per system instructions)
    artifacts = cmd_status(notebook_id)
    completed = [a for a in artifacts if a.get("status") == "completed"]

    if not completed:
        print("⚠️  No completed artifacts to download.")
        log_work(f"⚠️  [NLM Fetch]: No completed artifacts for {notebook_id[:12]}")
        return []

    # Create output directory
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    downloaded = []
    for artifact in completed:
        art_type = artifact.get("type", "unknown")
        art_info = DOWNLOADABLE_ARTIFACTS.get(art_type)

        if not art_info:
            print(f"  ⏭️  Skipping unsupported type: {art_type}")
            continue

        # Build output filename (collision-free if multiple artifacts of same type)
        art_slug = art_type.replace("_", "-")
        base_name = f"{art_slug}{art_info['ext']}"
        output_file = out_path / base_name
        if output_file.exists():
            short_id = artifact.get("id", "")[:8]
            output_file = out_path / f"{art_slug}_{short_id}{art_info['ext']}"

        cmd_name = art_info["cmd"]

        print(f"  📦 Downloading {art_type} → {output_file}")
        result = run_nlm(
            ["download", cmd_name, notebook_id, "-o", str(output_file)],
            timeout=60
        )

        if result.returncode == 0:
            downloaded.append(str(output_file))
            print(f"  ✅ Downloaded: {output_file}")

            # Auto-convert audio to mp3 if requested
            if art_type == "audio" and convert_mp3:
                mp3_file = out_path / "audio.mp3"
                print(f"  🔄 Converting {output_file} → {mp3_file}")
                ffmpeg_result = subprocess.run(
                    [
                        "ffmpeg", "-y",  # overwrite
                        "-i", str(output_file),
                        "-acodec", "libmp3lame",
                        "-q:a", "2",
                        str(mp3_file),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                if ffmpeg_result.returncode == 0:
                    downloaded.append(str(mp3_file))
                    print(f"  ✅ Converted: {mp3_file}")
                else:
                    print(f"  ⚠️  ffmpeg conversion failed: {ffmpeg_result.stderr[:120]}")
        else:
            print(f"  ❌ Download failed for {art_type}: {result.stderr.strip()[:120]}")

    print(f"\n📦 Total downloaded: {len(downloaded)} files")
    log_work(f"✅ Completed [NLM Fetch]: {len(downloaded)} files → {output_dir}")
    return downloaded


def cmd_pipeline(
    notebook_id: str,
    question: str,
    generate_types: list = None,
    do_fetch: bool = True,
    output_dir: str = None,
    convert_mp3: bool = True,
) -> dict:
    """
    Full pipeline: Query → Generate (optional) → Wait → Fetch.
    Workflow Pattern from System Instructions.
    """
    print_header("🚀 Full Orchestration Pipeline")
    log_work(f"🟡 Starting [NLM Pipeline]: notebook={notebook_id[:12]}...")

    results = {
        "query_answer": None,
        "generated": [],
        "downloaded": [],
    }

    # Step 1: Understand + Consult Brain
    if question:
        results["query_answer"] = cmd_query(notebook_id, question)

    # Step 2: Generate artifacts (if requested)
    if generate_types:
        print_header("🏭 Generating Studio Artifacts")
        for art_type in generate_types:
            print(f"  🔧 Generating {art_type}...")
            gen_result = run_nlm(
                [art_type, "create", notebook_id] if art_type in ("audio", "report", "slides", "video")
                else [art_type, notebook_id],
                timeout=30,
            )
            if gen_result.returncode == 0:
                results["generated"].append(art_type)
                print(f"  ✅ Generation triggered: {art_type}")
            else:
                print(f"  ⚠️  Generation failed for {art_type}: {gen_result.stderr.strip()[:80]}")

        # Wait for artifacts to complete (poll every 15s, max 5 min)
        if results["generated"]:
            print("\n⏳ Waiting for artifacts to complete...")
            for attempt in range(20):
                time.sleep(15)
                artifacts = cmd_status(notebook_id)
                completed = [a for a in artifacts if a.get("status") == "completed"]
                pending = [a for a in artifacts if a.get("status") != "completed"]
                if not pending:
                    print("✅ All artifacts completed!")
                    break
                print(f"  ⏳ {len(completed)}/{len(artifacts)} completed... (attempt {attempt+1}/20)")
            else:
                print("⚠️  Timed out waiting for artifacts. Fetching what's available.")

    # Step 3: Fetch & download
    if do_fetch:
        out = output_dir or str(DEFAULT_EXPORT_DIR)
        results["downloaded"] = cmd_fetch(notebook_id, out, convert_mp3)

    log_work(f"✅ Completed [NLM Pipeline]: query={'yes' if question else 'no'}, "
             f"generated={len(results['generated'])}, downloaded={len(results['downloaded'])}")

    # Summary
    print_header("📋 Pipeline Summary")
    print(f"  Brain query:    {'✅' if results['query_answer'] else '⏭️  skipped'}")
    print(f"  Generated:      {len(results['generated'])} artifacts")
    print(f"  Downloaded:     {len(results['downloaded'])} files")

    return results


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="NotebookLM Orchestrator Agent — Query, Generate, Fetch from the Brain",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Notebook Aliases:
  pitch        → Vlada Stojanovic & Pocarr Investor Pitch
  fk-sava-45   → FK Sava 45
  fine-tuning  → Fine-Tuning & OpenWebUI 2026
  web-ui       → Web UI Best Practices 2026
  business     → Strategic Business Automation 2026
  openwebui    → OpenWebUI Massive Knowledge System
  ai-coaching  → AI Coaching 2026

Examples:
  python3 nlm_orchestrator.py query pitch "What is the core value proposition?"
  python3 nlm_orchestrator.py status pitch
  python3 nlm_orchestrator.py fetch pitch --output exports/pitch/
  python3 nlm_orchestrator.py pipeline pitch "Summarize the pitch" --fetch
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- query ---
    p_query = subparsers.add_parser("query", help="Query the NotebookLM Brain")
    p_query.add_argument("notebook_id", help="Notebook ID or alias")
    p_query.add_argument("question", help="Question to ask the Brain")
    p_query.add_argument("--json", action="store_true", dest="json_output", help="Output as JSON")

    # --- status ---
    p_status = subparsers.add_parser("status", help="Check studio artifact status")
    p_status.add_argument("notebook_id", help="Notebook ID or alias")

    # --- fetch ---
    p_fetch = subparsers.add_parser("fetch", help="Download all completed artifacts")
    p_fetch.add_argument("notebook_id", help="Notebook ID or alias")
    p_fetch.add_argument("--output", "-o", default=None, help="Output directory (default: exports/general/)")
    p_fetch.add_argument("--no-mp3", action="store_true", help="Skip .m4a → .mp3 conversion")

    # --- pipeline ---
    p_pipe = subparsers.add_parser("pipeline", help="Full orchestration pipeline")
    p_pipe.add_argument("notebook_id", help="Notebook ID or alias")
    p_pipe.add_argument("question", nargs="?", default="", help="Question to ask (optional)")
    p_pipe.add_argument("--generate", "-g", default="", help="Comma-separated artifact types to generate")
    p_pipe.add_argument("--fetch", action="store_true", help="Download completed artifacts after pipeline")
    p_pipe.add_argument("--output", "-o", default=None, help="Output directory for fetched artifacts")
    p_pipe.add_argument("--no-mp3", action="store_true", help="Skip .m4a → .mp3 conversion")

    # --- list ---
    p_list = subparsers.add_parser("list", help="List known notebook aliases")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    # --- list ---
    if args.command == "list":
        print_header("📚 Known Notebook Aliases")
        for alias, nid in sorted(NOTEBOOK_ALIASES.items()):
            print(f"  {alias:<16} → {nid}")
        sys.exit(0)

    # Resolve alias
    notebook_id = resolve_notebook_id(args.notebook_id)

    # --- query ---
    if args.command == "query":
        answer = cmd_query(notebook_id, args.question, args.json_output)
        if not answer:
            sys.exit(1)

    # --- status ---
    elif args.command == "status":
        cmd_status(notebook_id)

    # --- fetch ---
    elif args.command == "fetch":
        out = args.output or str(DEFAULT_EXPORT_DIR)
        cmd_fetch(notebook_id, out, convert_mp3=not args.no_mp3)

    # --- pipeline ---
    elif args.command == "pipeline":
        gen_types = [t.strip() for t in args.generate.split(",") if t.strip()] if args.generate else None
        out = args.output or str(DEFAULT_EXPORT_DIR)
        cmd_pipeline(
            notebook_id,
            args.question,
            generate_types=gen_types,
            do_fetch=args.fetch,
            output_dir=out,
            convert_mp3=not args.no_mp3,
        )


if __name__ == "__main__":
    main()
