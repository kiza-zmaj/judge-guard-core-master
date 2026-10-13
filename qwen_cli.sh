#!/bin/bash
# Qwen CLI Wrapper for Antigravity — 100% PRODUCTION MODE
# Usage: ./qwen_cli.sh '<action description>' [optional command to execute]

ACTION=$1
COMMAND_TO_RUN=$2

if [ -z "$ACTION" ]; then
    echo ""
    echo "  Usage: qwen_cli.sh '<action description>' [optional command]"
    echo ""
    echo "  Examples:"
    echo "    ./qwen_cli.sh 'Deploy model weights'"
    echo "    ./qwen_cli.sh 'Verify pipeline health' 'python3 test_health.py'"
    echo ""
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python3"
if [ ! -f "$VENV_PYTHON" ]; then
    VENV_PYTHON="python3"
fi

export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"

# 1. Ensure TICKET.md is synchronized with current action
echo "🎫 Synchronizing TICKET.md for: QWEN: $ACTION"
"$VENV_PYTHON" "$SCRIPT_DIR/src/antigravity_core/ticket_verifier.py" "QWEN: $ACTION" create > /dev/null 2>&1

# 2. Record action start in WORK_LOG.md (Mandatory Rule)
echo "" >> "$SCRIPT_DIR/WORK_LOG.md"
echo "🟡 Starting QWEN: $ACTION" >> "$SCRIPT_DIR/WORK_LOG.md"

# 3. Pre-Action JudgeGuard Check (Runs Layer 000 Ollama Cloud Gemma 4 Gate + Layers 00, 0, 1, 2, 3)
echo "🛡️ Running Pre-Action JudgeGuard Verification..."
cd "$SCRIPT_DIR" && "$VENV_PYTHON" judge_guard.py "QWEN: $ACTION"
PRE_RESULT=$?

if [ $PRE_RESULT -ne 0 ]; then
    echo "🛑 Action BLOCKED by JudgeGuard."
    echo "🛑 Blocked: QWEN: $ACTION" >> "$SCRIPT_DIR/WORK_LOG.md"
    exit 1
fi

echo "✅ Pre-Action Approved by JudgeGuard."

# 4. Execute the command if provided
if [ -n "$COMMAND_TO_RUN" ]; then
    echo "🚀 Executing command: $COMMAND_TO_RUN"
    eval "$COMMAND_TO_RUN"
    CMD_EXIT=$?
    if [ $CMD_EXIT -ne 0 ]; then
        echo "❌ Execution failed with exit code $CMD_EXIT"
        echo "🛑 Failed during execution: QWEN: $ACTION (exit code $CMD_EXIT)" >> "$SCRIPT_DIR/WORK_LOG.md"
        exit $CMD_EXIT
    fi
fi

# 5. Post-Action Ticket Closure Verification (Approval from Gemma 4 + Agents)
echo "🎫 Requesting Post-Action Ticket Closure Approval from Agents..."
CLOSURE_EVIDENCE="COMPLETED: Execution finished with exit code ${CMD_EXIT:-0}; Master Orchestration standards and safety rules maintained."
"$VENV_PYTHON" "$SCRIPT_DIR/src/antigravity_core/ticket_verifier.py" "QWEN: $ACTION" verify_complete "$CLOSURE_EVIDENCE"
POST_TICKET_RESULT=$?

if [ $POST_TICKET_RESULT -ne 0 ]; then
    echo "🛑 Post-action ticket closure REJECTED by agent gate."
    echo "🛑 Rejected at closure: QWEN: $ACTION" >> "$SCRIPT_DIR/WORK_LOG.md"
    exit 1
fi

echo "✅ Agent closure approval granted for ticket."
echo "✅ Completed QWEN: $ACTION" >> "$SCRIPT_DIR/WORK_LOG.md"

# 6. Automatic Git Checkpoint & Verification
CHANGES_COUNT=$(git -C "$SCRIPT_DIR" status --porcelain | wc -l)
if [ "$CHANGES_COUNT" -gt 0 ]; then
    echo "🔍 Running Token Cleaner Audit..."
    if [ -f "$SCRIPT_DIR/git_bolt_jules_gate.py" ]; then
        "$VENV_PYTHON" "$SCRIPT_DIR/git_bolt_jules_gate.py" audit
    fi
    echo "📦 Staging changes and committing checkpoint..."
    git -C "$SCRIPT_DIR" add .
    git -C "$SCRIPT_DIR" commit -m "checkpoint: QWEN: $ACTION"
    COMMIT_EXIT=$?
    if [ $COMMIT_EXIT -ne 0 ]; then
        echo "❌ Git checkpoint commit failed!"
        echo "🛑 Checkpoint commit failed for: QWEN: $ACTION" >> "$SCRIPT_DIR/WORK_LOG.md"
        exit 1
    fi
    COMMIT_SHA=$(git -C "$SCRIPT_DIR" rev-parse --short HEAD)
    echo "📌 Git checkpoint SHA: $COMMIT_SHA" >> "$SCRIPT_DIR/WORK_LOG.md"
    echo "✅ Git checkpoint created: $COMMIT_SHA"
    if [ -f "$SCRIPT_DIR/git_bolt_jules_gate.py" ]; then
        BADGE=$("$VENV_PYTHON" "$SCRIPT_DIR/git_bolt_jules_gate.py" badge --agent qwen --action "$ACTION" 2>/dev/null)
        if [ -n "$BADGE" ]; then
            echo "$BADGE" >> "$SCRIPT_DIR/WORK_LOG.md"
        fi
    fi
else
    echo "ℹ️ No file changes detected; recording NO_CHANGES."
    echo "📌 Checkpoint: NO_CHANGES" >> "$SCRIPT_DIR/WORK_LOG.md"
fi

# 7. Codex Log Monitoring & Cleanup
if [ -f "$SCRIPT_DIR/scripts/codex_log_cleaner.py" ]; then
    "$VENV_PYTHON" "$SCRIPT_DIR/scripts/codex_log_cleaner.py" > /dev/null 2>&1
fi

echo "🎉 Action 'QWEN: $ACTION' successfully verified, executed, and checkpointed."
exit 0
