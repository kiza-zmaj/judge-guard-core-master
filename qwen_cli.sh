#!/bin/bash
# Qwen CLI Wrapper for Antigravity — 100% PRODUCT MODE
# Matches gemini_cli.sh production standard.

ACTION=$1
if [ -z "$ACTION" ]; then
    echo ""
    echo "  Usage: qwen_cli.sh '<action description>'"
    echo ""
    echo "  Examples:"
    echo "    ./qwen_cli.sh 'Deploy new model'"
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

if [ ! -f "$VENV_PYTHON" ]; then
    echo "⚠️  .venv not found. Using system python3."
    VENV_PYTHON="python3"
fi

echo "" >> "$SCRIPT_DIR/WORK_LOG.md"
echo "🟡 Starting QWEN: $ACTION" >> "$SCRIPT_DIR/WORK_LOG.md"

cd "$SCRIPT_DIR" && PYTHONPATH="$SCRIPT_DIR" "$VENV_PYTHON" judge_guard.py "QWEN: $ACTION"
RESULT=$?

if [ $RESULT -eq 0 ]; then
    echo "✅ Action Approved by JudgeGuard"
    echo "✅ Completed QWEN: $ACTION" >> "$SCRIPT_DIR/WORK_LOG.md"
else
    echo "🛑 Action BLOCKED by JudgeGuard"
    echo "🛑 Failed: QWEN: $ACTION" >> "$SCRIPT_DIR/WORK_LOG.md"
    exit 1
fi
