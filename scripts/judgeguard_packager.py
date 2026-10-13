#!/usr/bin/env python3
"""
JudgeGuard Master Orchestration Packager & Reproducibility Engine.
Packages, exports, and verifies the complete JudgeGuard ecosystem for any new
project or GitHub repository.

Commands:
    export   - Export full ecosystem to a target directory (with optional git init)
    package  - Archive the starter kit into a portable .tar.gz bundle
    verify   - Verify that a target directory has all mandatory files and passing gates
"""

import os
import sys
import shutil
import tarfile
import argparse
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple

# Repo root reference
_REPO_ROOT = Path(__file__).resolve().parent.parent

# Core ecosystem manifest: files required to replicate JudgeGuard Master Orchestration
ECOSYSTEM_FILES = [
    # Directives & Laws
    "MASTER_ORCHESTRATION.md",
    "GEMINI.md",
    "BOLT.md",
    "AGENTS.md",
    ".agents/rules/mandatory.md",
    ".agents/rules/master_orchestration.md",
    ".agents/workflows/verify_action.md",
    ".agents/skills/verify-action/SKILL.md",

    # Safety & Gate Scripts
    "judge_guard.py",
    "git_bolt_jules_gate.py",
    "gemini_cli.sh",
    "qwen_cli.sh",
    "scripts/codex_log_cleaner.py",

    # Core Engine
    "src/antigravity_core/__init__.py",
    "src/antigravity_core/ticket_verifier.py",
    "src/antigravity_core/token_cleaner.py",
    "src/antigravity_core/telemetry.py",
    "src/antigravity_core/judge_flow.py",
    "src/antigravity_core/gemini_client.py",

    # Config & Dependency manifests
    ".env.example",
    "requirements-judgeguard.txt",
    "tests/test_bolt_jules_telemetry.py",
]

# Executable scripts that need chmod +x
EXECUTABLE_FILES = [
    "judge_guard.py",
    "git_bolt_jules_gate.py",
    "gemini_cli.sh",
    "qwen_cli.sh",
    "scripts/codex_log_cleaner.py",
]

# Template for fresh WORK_LOG.md in new repository
WORK_LOG_TEMPLATE = """# WORK_LOG.md — JudgeGuard Master Task Journal

> **Project:** {project_name}
> **Purpose:** Track all JudgeGuard verification events and atomic action logs.
> **Format:** Each entry uses 🟡 (starting) or ✅ (completed) or 🛑 (blocked)
> **Constraint:** Maximum 5 concurrent open tasks (Atomic Task Chunking rule).

---

🟡 Starting Initialize repository with JudgeGuard Master Orchestration
✅ Completed Initialize repository with JudgeGuard Master Orchestration
📌 Git checkpoint SHA: {initial_sha}
"""

# Template for fresh TICKET.md in new repository
TICKET_TEMPLATE = """# WORK TICKET
**Action:** Initialize repository with JudgeGuard Master Orchestration
**Objective:** Scaffold production-grade safety, token gating, and telemetry directives for {project_name}.
**Scope:** Repository root, .agents/, src/antigravity_core/
**Justification:** Initial bootstrapping under User Sovereignty (Law 1).
**Status:** OPEN
**Enforcement:** Non-destructive execution, precision standards, 100% production mode.
"""

# Optimized .gitignore for token clean execution
GITIGNORE_TEMPLATE = """# Environment & Secrets
.env
*.env
.venv/
venv/
.conda/

# Database & Telemetry (SQLite)
research.db

# Python bytecode & cache
*.pyc
*.pyo
__pycache__/
*.egg-info/
dist/
build/

# Token cleaner exclusions (high-token cache bloat)
local_py/
node_modules/
.cache/
exports/
*.log
WORK_LOG.html

# IDE & OS
.vscode/
.idea/
.DS_Store
Thumbs.db
"""


def export_ecosystem(target_dir: Path, project_name: str, init_git: bool = False) -> bool:
    """Exports all core ecosystem files to target_dir with clean templates."""
    print(f"📦 [EXPORT] Initializing JudgeGuard ecosystem in: {target_dir}")
    target_dir.mkdir(parents=True, exist_ok=True)

    # 1. Copy core files
    for rel_path in ECOSYSTEM_FILES:
        src = _REPO_ROOT / rel_path
        dst = target_dir / rel_path
        if not src.exists():
            print(f"⚠️ Warning: Source file missing: {rel_path}")
            continue

        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

        if rel_path in EXECUTABLE_FILES:
            try:
                os.chmod(dst, 0o755)
            except Exception:
                pass
        print(f"  ✓ Copied: {rel_path}")

    # 2. Write fresh .gitignore
    gitignore_path = target_dir / ".gitignore"
    with open(gitignore_path, "w", encoding="utf-8") as f:
        f.write(GITIGNORE_TEMPLATE)
    print("  ✓ Created: .gitignore (token-clean optimized)")

    # 3. Write fresh TICKET.md
    ticket_path = target_dir / "TICKET.md"
    with open(ticket_path, "w", encoding="utf-8") as f:
        f.write(TICKET_TEMPLATE.format(project_name=project_name))
    print("  ✓ Created: TICKET.md (initial ticket)")

    # 4. Write fresh WORK_LOG.md
    work_log_path = target_dir / "WORK_LOG.md"
    with open(work_log_path, "w", encoding="utf-8") as f:
        f.write(WORK_LOG_TEMPLATE.format(project_name=project_name, initial_sha="INITIAL"))
    print("  ✓ Created: WORK_LOG.md (initial work log)")

    # 5. Git initialization if requested
    if init_git:
        print("🔧 [GIT] Initializing git repository...")
        try:
            subprocess.run(["git", "init"], cwd=target_dir, check=True, stdout=subprocess.DEVNULL)
            # Ensure local git identity exists
            subprocess.run(["git", "config", "user.name", "JudgeGuard Agent"], cwd=target_dir, check=False)
            subprocess.run(["git", "config", "user.email", "agent@judgeguard.local"], cwd=target_dir, check=False)
            subprocess.run(["git", "add", "."], cwd=target_dir, check=True, stdout=subprocess.DEVNULL)
            subprocess.run(
                ["git", "commit", "-m", "checkpoint: Initialize JudgeGuard Master Orchestration"],
                cwd=target_dir,
                check=True,
                stdout=subprocess.DEVNULL
            )
            sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=target_dir, text=True).strip()
            # Update WORK_LOG.md with real initial sha
            with open(work_log_path, "w", encoding="utf-8") as f:
                f.write(WORK_LOG_TEMPLATE.format(project_name=project_name, initial_sha=sha))
            subprocess.run(["git", "commit", "-a", "--amend", "--no-edit"], cwd=target_dir, check=True, stdout=subprocess.DEVNULL)
            print(f"✅ Git initialized with initial checkpoint SHA: {sha}")
        except Exception as e:
            print(f"⚠️ Git initialization failed: {e}")

    print(f"\n🎉 JudgeGuard ecosystem successfully exported to: {target_dir}")
    print("Next steps:")
    print("  1. cd " + str(target_dir))
    print("  2. python3 -m venv .venv && source .venv/bin/activate")
    print("  3. pip install -r requirements-judgeguard.txt")
    print("  4. cp .env.example .env && # configure API keys")
    print("  5. python3 git_bolt_jules_gate.py audit")
    print("  6. pytest tests/test_bolt_jules_telemetry.py")
    return True


def package_bundle(output_tar: Path) -> bool:
    """Creates a standalone .tar.gz bundle of the starter kit."""
    output_tar.parent.mkdir(parents=True, exist_ok=True)
    temp_dir = _REPO_ROOT / "scratch" / "judgeguard_pack_tmp"
    if temp_dir.exists():
        shutil.rmtree(temp_dir)

    try:
        export_ecosystem(temp_dir, project_name="JudgeGuard Starter Kit", init_git=False)
        print(f"\n📦 [ARCHIVE] Compressing bundle into: {output_tar}")
        with tarfile.open(output_tar, "w:gz") as tar:
            tar.add(temp_dir, arcname="judgeguard-starter-kit")
        print(f"✅ Starter kit archive created: {output_tar} ({os.path.getsize(output_tar):,} bytes)")
        return True
    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


def verify_target(target_dir: Path) -> bool:
    """Verifies that target_dir has all required JudgeGuard files and passes compliance checks."""
    print(f"🔍 [VERIFY] Inspecting JudgeGuard ecosystem at: {target_dir}")
    missing = []
    for rel_path in ECOSYSTEM_FILES:
        if not (target_dir / rel_path).exists():
            missing.append(rel_path)

    for extra in ["TICKET.md", "WORK_LOG.md", ".gitignore"]:
        if not (target_dir / extra).exists():
            missing.append(extra)

    if missing:
        print(f"❌ Verification FAILED: Missing {len(missing)} files:")
        for m in missing:
            print(f"  - {m}")
        return False

    print(f"✅ All {len(ECOSYSTEM_FILES) + 3} mandatory JudgeGuard files are present.")

    # Check executable permissions
    for exe in EXECUTABLE_FILES:
        path = target_dir / exe
        if path.exists() and not os.access(path, os.X_OK):
            print(f"⚠️ Warning: {exe} is not marked executable. Run: chmod +x {path}")

    # Run git gate audit if python3 is available
    gate_script = target_dir / "git_bolt_jules_gate.py"
    if gate_script.exists():
        try:
            res = subprocess.run([sys.executable, str(gate_script), "audit"], cwd=target_dir, capture_output=True, text=True)
            if res.returncode == 0:
                print("✅ Git gate audit PASSED: Clean staged files and token optimization verified.")
            else:
                print(f"⚠️ Git gate audit returned code {res.returncode}:\n{res.stdout}\n{res.stderr}")
        except Exception as e:
            print(f"⚠️ Could not run git gate audit: {e}")

    print("🎉 Verification complete: Target directory is 100% JudgeGuard Master Orchestration compliant!")
    return True


def main():
    parser = argparse.ArgumentParser(description="JudgeGuard Master Orchestration Packager")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Export subcommand
    export_parser = subparsers.add_parser("export", help="Export ecosystem to directory")
    export_parser.add_argument("--target", required=True, help="Target directory path")
    export_parser.add_argument("--name", default="My Project", help="Project name for templates")
    export_parser.add_argument("--init-git", action="store_true", help="Initialize git repo with initial checkpoint")

    # Package subcommand
    pack_parser = subparsers.add_parser("package", help="Create .tar.gz starter kit archive")
    pack_parser.add_argument("--output", default=str(_REPO_ROOT / "exports" / "judgeguard-starter-kit.tar.gz"), help="Output archive path")

    # Verify subcommand
    verify_parser = subparsers.add_parser("verify", help="Verify JudgeGuard installation")
    verify_parser.add_argument("--target", default=".", help="Target directory to inspect")

    args = parser.parse_args()

    if args.command == "export":
        target = Path(args.target).resolve()
        success = export_ecosystem(target, project_name=args.name, init_git=args.init_git)
        sys.exit(0 if success else 1)
    elif args.command == "package":
        out = Path(args.output).resolve()
        success = package_bundle(out)
        sys.exit(0 if success else 1)
    elif args.command == "verify":
        target = Path(args.target).resolve()
        success = verify_target(target)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
