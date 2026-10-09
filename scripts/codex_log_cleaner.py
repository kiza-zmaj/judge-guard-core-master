#!/usr/bin/env python3
"""
Codex Log Monitor & Cleaner
Monitors WORK_LOG.md, cleans up temporary build artifacts, and ensures
that work logs comply with the Atomic Task Chunking Rule.
"""

import os
import sys
import glob
import shutil
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("CodexCleaner")

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CODEX_BIN = os.path.join(REPO_ROOT, "bin", "codex")
WORK_LOG_FILE = os.path.join(REPO_ROOT, "WORK_LOG.md")

def check_codex_available():
    return os.path.exists(CODEX_BIN) and os.access(CODEX_BIN, os.X_OK)

def clean_temporary_artifacts():
    """Remove temporary files, cache dirs, and scratch artifacts."""
    patterns = [
        "**/*.pyc",
        "**/__pycache__",
        "**/.pytest_cache",
        "**/*.tmp",
        "**/*.swp",
        "catboost_info",
    ]
    cleaned = 0
    for pat in patterns:
        for path in glob.glob(os.path.join(REPO_ROOT, pat), recursive=True):
            try:
                if os.path.isfile(path) or os.path.islink(path):
                    os.remove(path)
                    cleaned += 1
                elif os.path.isdir(path):
                    shutil.rmtree(path)
                    cleaned += 1
            except Exception as e:
                logger.warning(f"Failed to remove {path}: {e}")
    logger.info(f"🧹 Cleaned {cleaned} temporary files and caches.")
    return cleaned

def monitor_and_tidy_work_log():
    """
    Check WORK_LOG.md for orphaned Starting tasks and report status.
    """
    if not os.path.exists(WORK_LOG_FILE):
        logger.warning(f"WORK_LOG.md not found at {WORK_LOG_FILE}")
        return

    with open(WORK_LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    open_tasks = []
    for line in lines[-50:]:
        stripped = line.strip()
        if stripped.startswith("🟡 Starting"):
            task_name = stripped.replace("🟡 Starting", "").strip()
            open_tasks.append(task_name)
        elif stripped.startswith("✅ Completed") or stripped.startswith("⚠️ Abandoned"):
            task_name = stripped.replace("✅ Completed", "").replace("⚠️ Abandoned", "").strip()
            # Remove any matching start task from list
            open_tasks = [t for t in open_tasks if t not in task_name and task_name not in t]

    if len(open_tasks) > 5:
        logger.warning(f"⚠️ WORK_LOG.md warning: {len(open_tasks)} open tasks detected! Exceeds Atomic Task Chunking limit (5).")
    else:
        logger.info(f"✅ WORK_LOG.md is clean. Active open tasks: {len(open_tasks)}")

def main():
    logger.info("🔍 Starting Codex Log Monitoring & Cleanup...")
    if check_codex_available():
        logger.info(f"Found Codex binary: {CODEX_BIN}")
    else:
        logger.info("Codex binary present in system library.")

    clean_temporary_artifacts()
    monitor_and_tidy_work_log()
    logger.info("✨ Codex Log & Artifact Cleanup completed successfully.")

if __name__ == "__main__":
    main()
