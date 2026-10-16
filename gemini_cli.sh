#!/bin/bash
# Gemini CLI Wrapper for Antigravity — 100% REALITY-GROUNDED PRODUCTION MODE
# Usage: ./gemini_cli.sh [--contract-spec <spec>] '<action description>' [optional command to execute]
#
# Worktree isolation is MANDATORY by default (USE_WORKTREE=1).
# Direct non-worktree execution on master/main is always blocked.
# To explicitly disable worktree in tests, set USE_WORKTREE=0 externally — but this
# will be rejected when the active branch is master or main.

# External env override is respected; default is 1 (always isolate)
USE_WORKTREE="${USE_WORKTREE:-1}"
CONTRACT_SPEC="${JUDGEGUARD_CONTRACT_SPEC:-}"

while [ $# -gt 0 ]; do
    case "$1" in
        --contract-spec)
            CONTRACT_SPEC="$2"
            shift 2
            ;;
        *)
            break
            ;;
    esac
done

ACTION=$1
COMMAND_TO_RUN=$2

if [ -z "$ACTION" ]; then
    echo ""
    echo "  Usage: gemini_cli.sh [--contract-spec <spec>] '<action description>' [optional command]"
    echo ""
    echo "  Examples:"
    echo "    ./gemini_cli.sh 'Update model configuration'"
    echo "    ./gemini_cli.sh 'Run test suite' 'pytest tests/'"
    echo "    ./gemini_cli.sh --contract-spec '{\"min_files_changed\": 1}' 'Modify code'"
    echo ""
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || echo "$SCRIPT_DIR")"

VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python3"
if [ ! -f "$VENV_PYTHON" ]; then
    if [ -f "$REPO_ROOT/.venv/bin/python3" ]; then
        VENV_PYTHON="$REPO_ROOT/.venv/bin/python3"
    elif [ -f "$REPO_ROOT/../.venv/bin/python3" ]; then
        VENV_PYTHON="$REPO_ROOT/../.venv/bin/python3"
    elif [ -f "/home/testovinovi/judge-guard-core-master/.venv/bin/python3" ]; then
        VENV_PYTHON="/home/testovinovi/judge-guard-core-master/.venv/bin/python3"
    else
        VENV_PYTHON="python3"
    fi
fi

COMMON_DIR="$(git -C "$SCRIPT_DIR" rev-parse --git-common-dir 2>/dev/null || echo "")"
MAIN_ROOT="$(cd "$COMMON_DIR/.." 2>/dev/null && pwd)"

ENV_FILE=""
if [ -f "$SCRIPT_DIR/.env" ]; then
    ENV_FILE="$SCRIPT_DIR/.env"
elif [ -f "$REPO_ROOT/.env" ]; then
    ENV_FILE="$REPO_ROOT/.env"
elif [ -n "$MAIN_ROOT" ] && [ -f "$MAIN_ROOT/.env" ]; then
    ENV_FILE="$MAIN_ROOT/.env"
elif [ -f "/home/testovinovi/judge-guard-core-master/.env" ]; then
    ENV_FILE="/home/testovinovi/judge-guard-core-master/.env"
fi

if [ -n "$ENV_FILE" ]; then
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
fi

export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"

# Generate unique cryptographic Run ID
RAND_SUFFIX=$(head -c 4 /dev/urandom | xxd -p 2>/dev/null || od -N 4 -tx1 /dev/urandom | head -1 | awk '{print $2$3$4$5}')
RUN_ID="run_$(date +%Y%m%d_%H%M%S)_${RAND_SUFFIX:-0000}"

BASE_BRANCH="$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "master")"
BASE_COMMIT="$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || echo "")"

# Enforce mandatory worktree isolation against protected branches (master / main)
CURRENT_BRANCH="$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")"
if [ "$CURRENT_BRANCH" = "master" ] || [ "$CURRENT_BRANCH" = "main" ]; then
    if [ "$USE_WORKTREE" -ne 1 ]; then
        echo "🛑 Direct execution on protected branch '$CURRENT_BRANCH' is strictly forbidden. Draft worktree isolation is mandatory."
        exit 1
    fi
fi

if [ "$USE_WORKTREE" -eq 1 ]; then
    TARGET_DIR="$REPO_ROOT/.worktrees/draft-${RUN_ID}"
    DRAFT_BRANCH="draft/${RUN_ID}"
    mkdir -p "$REPO_ROOT/.worktrees"

    echo "🌳 [Isolation] Creating draft worktree: $TARGET_DIR on branch $DRAFT_BRANCH"
    git -C "$REPO_ROOT" worktree add "$TARGET_DIR" -b "$DRAFT_BRANCH" "$BASE_COMMIT" >/dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo "🛑 Failed to create git worktree. Aborting."
        exit 1
    fi
    [ -n "$ENV_FILE" ] && cp "$ENV_FILE" "$TARGET_DIR/.env" 2>/dev/null || true
else
    TARGET_DIR="$SCRIPT_DIR"
fi

export JUDGEGUARD_PROJECT_ROOT="$TARGET_DIR"
export PYTHONPATH="$TARGET_DIR:$SCRIPT_DIR:$PYTHONPATH"

CONTRACT_DIR="$TARGET_DIR/.cache/contracts"
MANIFEST_DIR="$TARGET_DIR/.cache/manifests"
EVIDENCE_DIR="$TARGET_DIR/.cache/runtime_evidence"
VERDICT_DIR="$TARGET_DIR/.cache/verdicts"
mkdir -p "$CONTRACT_DIR" "$MANIFEST_DIR" "$EVIDENCE_DIR" "$VERDICT_DIR"

CONTRACT_FILE="$CONTRACT_DIR/contract_${RUN_ID}.json"
EVIDENCE_FILE="$EVIDENCE_DIR/evidence_${RUN_ID}.json"
MANIFEST_FILE="$MANIFEST_DIR/manifest_${RUN_ID}.json"
VERDICT_FILE="$VERDICT_DIR/verdict_${RUN_ID}.json"

echo "🆔 Initializing Reality-Grounded Run: $RUN_ID (Target: $TARGET_DIR)"

# Default contract criteria when none provided: enforce executions and clean git state
if [ -z "$CONTRACT_SPEC" ]; then
    if [ -n "$COMMAND_TO_RUN" ]; then
        CONTRACT_SPEC="{\"required_executions\": [\"$COMMAND_TO_RUN\"], \"require_clean_git\": true}"
    else
        CONTRACT_SPEC="{\"require_clean_git\": true}"
    fi
fi

# 1. Pre-Flight Acceptance Contract Generation
echo "📜 Locking Immutable Acceptance Contract..."
"$VENV_PYTHON" "$SCRIPT_DIR/judge_guard.py" --contract "$RUN_ID" "$ACTION" "$CONTRACT_SPEC" "$CONTRACT_FILE"
if [ $? -ne 0 ]; then
    echo "🛑 Failed to create Acceptance Contract. Aborting."
    if [ "$USE_WORKTREE" -eq 1 ]; then
        git -C "$REPO_ROOT" worktree remove --force "$TARGET_DIR" >/dev/null 2>&1
        git -C "$REPO_ROOT" branch -D "$DRAFT_BRANCH" >/dev/null 2>&1
    fi
    exit 1
fi

# 2. Synchronize TICKET.md and WORK_LOG.md
echo "🎫 Synchronizing TICKET.md for: $ACTION"
(cd "$TARGET_DIR" && "$VENV_PYTHON" "$SCRIPT_DIR/src/antigravity_core/ticket_verifier.py" "$ACTION" create > /dev/null 2>&1)

echo "" >> "$TARGET_DIR/WORK_LOG.md"
echo "🟡 Starting $ACTION (Run: $RUN_ID)" >> "$TARGET_DIR/WORK_LOG.md"

# 3. Pre-Action JudgeGuard Safety Gate (Layers 00, 000, 0, 1, 2, 3)
echo "🛡️ Running Pre-Action JudgeGuard Verification..."
(cd "$TARGET_DIR" && "$VENV_PYTHON" "$SCRIPT_DIR/judge_guard.py" "$ACTION")
PRE_RESULT=$?

if [ $PRE_RESULT -ne 0 ]; then
    echo "🛑 Action BLOCKED by JudgeGuard Pre-Flight."
    if [ "$USE_WORKTREE" -eq 1 ]; then
        echo "🛑 Worktree quarantined: $TARGET_DIR (Base $BASE_BRANCH untouched)"
    else
        echo "🛑 Blocked: $ACTION (Run: $RUN_ID)" >> "$SCRIPT_DIR/WORK_LOG.md"
    fi
    exit 1
fi
echo "✅ Pre-Action Approved by JudgeGuard."

# 4. Trusted Execution (Independent capture of exit code, duration, hashes)
CMD_EXIT=0
if [ -n "$COMMAND_TO_RUN" ]; then
    echo "🚀 TrustedRunner executing command: $COMMAND_TO_RUN"
    "$VENV_PYTHON" "$SCRIPT_DIR/judge_guard.py" --run-trusted "$RUN_ID" "$COMMAND_TO_RUN" "$EVIDENCE_FILE"
    CMD_EXIT=$?
    if [ $CMD_EXIT -ne 0 ]; then
        echo "❌ Execution failed with exit code $CMD_EXIT (Recorded in Trusted Evidence)"
        if [ "$USE_WORKTREE" -eq 1 ]; then
            echo "🛑 Draft worktree quarantined at: $TARGET_DIR. Base branch $BASE_BRANCH remains at $BASE_COMMIT."
        else
            echo "🛑 Failed during execution: $ACTION (exit code $CMD_EXIT)" >> "$SCRIPT_DIR/WORK_LOG.md"
        fi
        exit $CMD_EXIT
    fi
fi

# 5. Checkpoint Commit (Create commit in draft branch/target before outcome verification)
if [ "$USE_WORKTREE" -eq 1 ]; then
    # Reset worktree WORK_LOG.md so it doesn't conflict with master's dirty WORK_LOG.md
    git -C "$TARGET_DIR" checkout HEAD -- WORK_LOG.md 2>/dev/null || rm -f "$TARGET_DIR/WORK_LOG.md"
fi

CHANGES_COUNT=$(git -C "$TARGET_DIR" status --porcelain | grep -v "^\?\? \.cache" | grep -v "research\.db" | wc -l)
if [ "$CHANGES_COUNT" -gt 0 ]; then
    if [ -f "$SCRIPT_DIR/git_bolt_jules_gate.py" ]; then
        (cd "$TARGET_DIR" && "$VENV_PYTHON" "$SCRIPT_DIR/git_bolt_jules_gate.py" audit 2>/dev/null || true)
    fi
    echo "📦 Staging draft changes..."
    git -C "$TARGET_DIR" add -A
    git -C "$TARGET_DIR" reset HEAD -- research.db 2>/dev/null || true
    git -C "$TARGET_DIR" reset HEAD -- WORK_LOG.md 2>/dev/null || true
    git -C "$TARGET_DIR" reset HEAD -- .cache 2>/dev/null || true
    git -C "$TARGET_DIR" commit -m "checkpoint: $ACTION" >/dev/null 2>&1
    TARGET_COMMIT_SHA=$(git -C "$TARGET_DIR" rev-parse HEAD)
else
    TARGET_COMMIT_SHA=$(git -C "$TARGET_DIR" rev-parse HEAD)
fi

# 6. Build or Validate Evidence Manifest
if [ ! -f "$MANIFEST_FILE" ]; then
    python3 -c "
import os, sys, json, hashlib
repo = sys.argv[1]
run_id = sys.argv[2]
commit_sha = sys.argv[3]
command = sys.argv[4] if len(sys.argv) > 4 else ''
cmd_exit = int(sys.argv[5]) if len(sys.argv) > 5 and sys.argv[5] != '' else 0
out_file = sys.argv[6]

files = [f for f in os.popen(f'git -C {repo} diff-tree --no-commit-id --name-only -r {commit_sha}').read().splitlines() if f.strip()]
artifacts = []
for rel_p in files:
    full_p = os.path.join(repo, rel_p)
    if os.path.exists(full_p) and os.path.isfile(full_p):
        h = hashlib.sha256(open(full_p,'rb').read()).hexdigest()
        artifacts.append({'path': rel_p, 'sha256': h, 'min_size_bytes': 1})
manifest = {
    'run_id': run_id,
    'artifacts': artifacts,
    'executions': [{'command': command, 'exit_code': cmd_exit}] if command else []
}
with open(out_file, 'w') as mf:
    json.dump(manifest, mf, indent=2)
" "$TARGET_DIR" "$RUN_ID" "$TARGET_COMMIT_SHA" "$COMMAND_TO_RUN" "$CMD_EXIT" "$MANIFEST_FILE"
fi

# 7. Layer 4: Reality-Grounded Outcome Verification
echo "⚖️ Evaluating Layer 4 Reality-Grounded Outcome on commit $TARGET_COMMIT_SHA..."
"$VENV_PYTHON" "$SCRIPT_DIR/judge_guard.py" --verify-outcome "$RUN_ID" "$MANIFEST_FILE" "$CONTRACT_FILE" "$TARGET_COMMIT_SHA" "$EVIDENCE_FILE"
OUTCOME_EXIT=$?

if [ $OUTCOME_EXIT -ne 0 ]; then
    echo "🛑 Layer 4 Outcome Verification REJECTED. Changes quarantined."
    if [ "$USE_WORKTREE" -eq 1 ]; then
        echo "🛑 Draft quarantined in $TARGET_DIR. Base branch $BASE_BRANCH untouched."
    else
        echo "🛑 Rejected at Outcome Gate: $ACTION" >> "$SCRIPT_DIR/WORK_LOG.md"
    fi
    exit 1
fi

# 8. Verify Cryptographic Verdict Signature
echo "🔐 Validating Cryptographic Verdict Signature..."
"$VENV_PYTHON" "$SCRIPT_DIR/judge_guard.py" --verify-signature "$VERDICT_FILE" "$TARGET_COMMIT_SHA"
SIG_EXIT=$?

if [ $SIG_EXIT -ne 0 ]; then
    echo "🚨 Cryptographic Signature Verification FAILED! Refusing integration."
    exit 1
fi
echo "✅ Verdict Cryptographically Verified: $VERDICT_FILE"

# 9. Post-Action Ticket Closure Verification
echo "🎫 Closing ticket with verified verdict ticket..."
(cd "$TARGET_DIR" && "$VENV_PYTHON" "$SCRIPT_DIR/src/antigravity_core/ticket_verifier.py" "$ACTION" verify_complete "$VERDICT_FILE" "$TARGET_COMMIT_SHA")
TICKET_CLOSE_EXIT=$?

if [ $TICKET_CLOSE_EXIT -ne 0 ]; then
    echo "🛑 Ticket closure rejected by ticket gate."
    exit 1
fi

# 10. Merge and Cleanup (If running in worktree)
if [ "$USE_WORKTREE" -eq 1 ]; then
    echo "🔀 Fast-forward merging verified commit $TARGET_COMMIT_SHA into $BASE_BRANCH..."
    # Verify that base commit is ancestor of target commit
    git -C "$REPO_ROOT" merge-base --is-ancestor "$BASE_COMMIT" "$TARGET_COMMIT_SHA"
    if [ $? -ne 0 ]; then
        echo "🚨 Ancestry violation! Target commit $TARGET_COMMIT_SHA is not descendant of $BASE_COMMIT"
        exit 1
    fi

    # Perform fast-forward merge into base branch
    git -C "$REPO_ROOT" merge --ff-only "$TARGET_COMMIT_SHA"
    MERGE_RES=$?
    if [ $MERGE_RES -ne 0 ]; then
        echo "🚨 Fast-forward merge failed. Preserving worktree at $TARGET_DIR."
        exit 1
    fi

    # Copy verdict cache to base repo for audit trail
    mkdir -p "$REPO_ROOT/.cache/verdicts"
    cp -r "$TARGET_DIR/.cache/verdicts/"* "$REPO_ROOT/.cache/verdicts/" 2>/dev/null || true

    # Clean up worktree
    git -C "$REPO_ROOT" worktree remove --force "$TARGET_DIR" >/dev/null 2>&1
    git -C "$REPO_ROOT" branch -d "$DRAFT_BRANCH" >/dev/null 2>&1

    if [ -f "$REPO_ROOT/WORK_LOG.md" ]; then
        echo "" >> "$REPO_ROOT/WORK_LOG.md"
        echo "✅ Merged $ACTION (Commit: $TARGET_COMMIT_SHA, Run: $RUN_ID)" >> "$REPO_ROOT/WORK_LOG.md"
    fi
else
    echo "✅ Completed $ACTION (Run: $RUN_ID, Commit: $TARGET_COMMIT_SHA)" >> "$SCRIPT_DIR/WORK_LOG.md"
fi

echo "🎉 Action '$ACTION' successfully verified against reality, signed, and integrated."
exit 0
