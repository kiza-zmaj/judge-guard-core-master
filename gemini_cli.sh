#!/bin/bash
# Gemini CLI Wrapper for Antigravity
# Usage: ./gemini_cli.sh '<action description>'

ACTION=$1
if [ -z "$ACTION" ]; then
    echo ""
    echo "  Usage: gemini_cli.sh '<action description>'"
    echo ""
    echo "  Examples:"
    echo "    ./gemini_cli.sh 'Start Phase 2 Execution'"
    echo "    ./gemini_cli.sh 'Deploy to production'"
    echo ""
    echo "  This wrapper:"
    echo "    1. Logs 🟡 Starting [ACTION] to WORK_LOG.md"
    echo "    2. Runs JudgeGuard verification (judge_guard.py)"
    echo "    3. Logs ✅ or 🛑 result to WORK_LOG.md"
    echo ""
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python3"

# Fall back to system python3 if venv not available
if [ ! -f "$VENV_PYTHON" ]; then
    echo "⚠️  .venv not found. Using system python3. Run: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
    VENV_PYTHON="python3"
fi

# 1. Update WORK_LOG.md (Mandatory Rule)
echo "" >> "$SCRIPT_DIR/WORK_LOG.md"
echo "🟡 Starting $ACTION" >> "$SCRIPT_DIR/WORK_LOG.md"

# 2. Run JudgeGuard via venv Python
cd "$SCRIPT_DIR" && PYTHONPATH="$SCRIPT_DIR" "$VENV_PYTHON" judge_guard.py "$ACTION"
RESULT=$?

if [ $RESULT -eq 0 ]; then
    echo "✅ Action Approved by JudgeGuard"
    echo "✅ Completed $ACTION" >> "$SCRIPT_DIR/WORK_LOG.md"
else
    echo "🛑 Action BLOCKED by JudgeGuard"
    echo "🛑 Failed: $ACTION" >> "$SCRIPT_DIR/WORK_LOG.md"
    exit 1
fi
