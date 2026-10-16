#!/bin/bash
# Gemini CLI Wrapper for Antigravity — 100% REALITY-GROUNDED PRODUCTION MODE
# Usage: ./gemini_cli.sh '<action description>' [optional command to execute]

ACTION=$1
COMMAND_TO_RUN=$2

if [ -z "$ACTION" ]; then
    echo ""
    echo "  Usage: gemini_cli.sh '<action description>' [optional command]"
    echo ""
    echo "  Examples:"
    echo "    ./gemini_cli.sh 'Update model configuration'"
    echo "    ./gemini_cli.sh 'Run test suite' 'pytest tests/'"
    echo ""
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python3"
if [ ! -f "$VENV_PYTHON" ]; then
    VENV_PYTHON="python3"
fi

# Source .env so GEMINI_API_KEY and other secrets are available to judge_guard.py
if [ -f "$SCRIPT_DIR/.env" ]; then
    set -a
    # shellcheck disable=SC1090
    source "$SCRIPT_DIR/.env"
    set +a
fi

export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"

# Generate unique cryptographic Run ID
RAND_SUFFIX=$(head -c 4 /dev/urandom | xxd -p 2>/dev/null || od -N 4 -tx1 /dev/urandom | head -1 | awk '{print $2$3$4$5}')
RUN_ID="run_$(date +%Y%m%d_%H%M%S)_${RAND_SUFFIX:-0000}"

CONTRACT_DIR="$SCRIPT_DIR/.cache/contracts"
MANIFEST_DIR="$SCRIPT_DIR/.cache/manifests"
EVIDENCE_DIR="$SCRIPT_DIR/.cache/runtime_evidence"
VERDICT_DIR="$SCRIPT_DIR/.cache/verdicts"
mkdir -p "$CONTRACT_DIR" "$MANIFEST_DIR" "$EVIDENCE_DIR" "$VERDICT_DIR"

CONTRACT_FILE="$CONTRACT_DIR/contract_${RUN_ID}.json"
EVIDENCE_FILE="$EVIDENCE_DIR/evidence_${RUN_ID}.json"
MANIFEST_FILE="$MANIFEST_DIR/manifest_${RUN_ID}.json"
VERDICT_FILE="$VERDICT_DIR/verdict_${RUN_ID}.json"

echo "🆔 Initializing Reality-Grounded Run: $RUN_ID"

# 1. Pre-Flight Acceptance Contract Generation
echo "📜 Locking Immutable Acceptance Contract..."
"$VENV_PYTHON" "$SCRIPT_DIR/judge_guard.py" --contract "$RUN_ID" "$ACTION" "{}" "$CONTRACT_FILE"
if [ $? -ne 0 ]; then
    echo "🛑 Failed to create Acceptance Contract. Aborting."
    exit 1
fi

# 2. Synchronize TICKET.md and WORK_LOG.md
echo "🎫 Synchronizing TICKET.md for: $ACTION"
"$VENV_PYTHON" "$SCRIPT_DIR/src/antigravity_core/ticket_verifier.py" "$ACTION" create > /dev/null 2>&1

echo "" >> "$SCRIPT_DIR/WORK_LOG.md"
echo "🟡 Starting $ACTION (Run: $RUN_ID)" >> "$SCRIPT_DIR/WORK_LOG.md"

# 3. Pre-Action JudgeGuard Safety Gate (Layers 00, 000, 0, 1, 2, 3)
echo "🛡️ Running Pre-Action JudgeGuard Verification..."
cd "$SCRIPT_DIR" && "$VENV_PYTHON" judge_guard.py "$ACTION"
PRE_RESULT=$?

if [ $PRE_RESULT -ne 0 ]; then
    echo "🛑 Action BLOCKED by JudgeGuard Pre-Flight."
    echo "🛑 Blocked: $ACTION (Run: $RUN_ID)" >> "$SCRIPT_DIR/WORK_LOG.md"
    exit 1
fi
echo "✅ Pre-Action Approved by JudgeGuard."

# 4. Trusted Execution (Independent capture of exit code, duration, hashes)
if [ -n "$COMMAND_TO_RUN" ]; then
    echo "🚀 TrustedRunner executing command: $COMMAND_TO_RUN"
    "$VENV_PYTHON" "$SCRIPT_DIR/judge_guard.py" --run-trusted "$RUN_ID" "$COMMAND_TO_RUN" "$EVIDENCE_FILE"
    CMD_EXIT=$?
    if [ $CMD_EXIT -ne 0 ]; then
        echo "❌ Execution failed with exit code $CMD_EXIT (Recorded in Trusted Evidence)"
        echo "🛑 Failed during execution: $ACTION (exit code $CMD_EXIT)" >> "$SCRIPT_DIR/WORK_LOG.md"
        exit $CMD_EXIT
    fi
fi

# 5. Build or Validate Evidence Manifest
# If user/agent didn't supply custom manifest, compile manifest from working tree changes
if [ ! -f "$MANIFEST_FILE" ]; then
    # Auto-compile manifest of changed files
    python3 -c "
import os, sys, json, hashlib
files = [f for f in os.popen('git status --porcelain').read().splitlines() if f.strip()]
artifacts = []
for line in files:
    parts = line.strip().split(maxsplit=1)
    if len(parts) == 2:
        rel_p = parts[1]
        if os.path.exists(rel_p) and os.path.isfile(rel_p):
            h = hashlib.sha256(open(rel_p,'rb').read()).hexdigest()
            artifacts.append({'path': rel_p, 'sha256': h, 'min_size_bytes': 1})
manifest = {
    'run_id': '$RUN_ID',
    'artifacts': artifacts,
    'executions': [{'command': '$COMMAND_TO_RUN', 'exit_code': ${CMD_EXIT:-0}}] if '$COMMAND_TO_RUN' else []
}
with open('$MANIFEST_FILE', 'w') as mf:
    json.dump(manifest, mf, indent=2)
"
fi

# Check git status and current HEAD
HEAD_SHA=$(git -C "$SCRIPT_DIR" rev-parse HEAD)

# 6. Layer 4: Reality-Grounded Outcome Verification
echo "⚖️ Evaluating Layer 4 Reality-Grounded Outcome..."
"$VENV_PYTHON" "$SCRIPT_DIR/judge_guard.py" --verify-outcome "$RUN_ID" "$MANIFEST_FILE" "$CONTRACT_FILE" "$HEAD_SHA" "$EVIDENCE_FILE"
OUTCOME_EXIT=$?

if [ $OUTCOME_EXIT -ne 0 ]; then
    echo "🛑 Layer 4 Outcome Verification REJECTED. Changes quarantined."
    echo "🛑 Rejected at Outcome Gate: $ACTION" >> "$SCRIPT_DIR/WORK_LOG.md"
    exit 1
fi

# 7. Verify Cryptographic Verdict Signature before Checkpoint
echo "🔐 Validating Cryptographic Verdict Signature..."
"$VENV_PYTHON" "$SCRIPT_DIR/judge_guard.py" --verify-signature "$VERDICT_FILE" "$HEAD_SHA"
SIG_EXIT=$?

if [ $SIG_EXIT -ne 0 ]; then
    echo "🚨 Cryptographic Signature Verification FAILED! Refusing checkpoint."
    exit 1
fi

echo "✅ Verdict Cryptographically Verified: $VERDICT_FILE"

# 8. Post-Action Ticket Closure Verification with Gemma 4
echo "🎫 Closing ticket with verified verdict ticket..."
"$VENV_PYTHON" "$SCRIPT_DIR/src/antigravity_core/ticket_verifier.py" "$ACTION" verify_complete "$VERDICT_FILE"
TICKET_CLOSE_EXIT=$?

if [ $TICKET_CLOSE_EXIT -ne 0 ]; then
    echo "🛑 Ticket closure rejected by ticket gate."
    exit 1
fi

# 9. Automatic Git Checkpoint & Telemetry
CHANGES_COUNT=$(git -C "$SCRIPT_DIR" status --porcelain | wc -l)
if [ "$CHANGES_COUNT" -gt 0 ]; then
    echo "🔍 Running Token Cleaner Audit..."
    if [ -f "$SCRIPT_DIR/git_bolt_jules_gate.py" ]; then
        "$VENV_PYTHON" "$SCRIPT_DIR/git_bolt_jules_gate.py" audit
    fi
    echo "📦 Staging changes and committing checkpoint..."
    git -C "$SCRIPT_DIR" add .
    git -C "$SCRIPT_DIR" commit -m "checkpoint: $ACTION"
    COMMIT_EXIT=$?
    if [ $COMMIT_EXIT -ne 0 ]; then
        echo "❌ Git checkpoint commit failed!"
        echo "🛑 Checkpoint commit failed for: $ACTION" >> "$SCRIPT_DIR/WORK_LOG.md"
        exit 1
    fi
    COMMIT_SHA=$(git -C "$SCRIPT_DIR" rev-parse --short HEAD)
    echo "📌 Git checkpoint SHA: $COMMIT_SHA" >> "$SCRIPT_DIR/WORK_LOG.md"
    echo "✅ Git checkpoint created: $COMMIT_SHA"
    if [ -f "$SCRIPT_DIR/git_bolt_jules_gate.py" ]; then
        BADGE=$("$VENV_PYTHON" "$SCRIPT_DIR/git_bolt_jules_gate.py" badge --agent gemini --action "$ACTION" 2>/dev/null)
        if [ -n "$BADGE" ]; then
            echo "$BADGE" >> "$SCRIPT_DIR/WORK_LOG.md"
        fi
    fi
else
    echo "ℹ️ No file changes detected; recording NO_CHANGES."
    echo "📌 Checkpoint: NO_CHANGES" >> "$SCRIPT_DIR/WORK_LOG.md"
fi

echo "✅ Completed $ACTION (Run: $RUN_ID)" >> "$SCRIPT_DIR/WORK_LOG.md"

# 10. Codex Log Monitoring & Cleanup
if [ -f "$SCRIPT_DIR/scripts/codex_log_cleaner.py" ]; then
    "$VENV_PYTHON" "$SCRIPT_DIR/scripts/codex_log_cleaner.py" > /dev/null 2>&1
fi

echo "🎉 Action '$ACTION' successfully verified against reality, signed, and checkpointed."
exit 0
