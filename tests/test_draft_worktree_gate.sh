#!/bin/bash
# ==============================================================================
# Integration Test: JudgeGuard Layer 4 Draft Worktree Gate
#
# Validates the complete draft-quarantine workflow for gemini_cli.sh and qwen_cli.sh:
# 1. Base branch remains on the exact same commit upon failure (zero new commits).
# 2. Draft changes remain isolated in quarantine.
# 3. Existing uncommitted user changes are strictly preserved and untouched.
# 4. Successful tasks merge ONLY the cryptographically verified commit.
# 5. Cryptographic signature binds the verdict to the exact merged commit SHA.
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || echo "$SCRIPT_DIR")"

REAL_VENV=""
if [ -d "$SCRIPT_DIR/.venv" ]; then
    REAL_VENV="$SCRIPT_DIR/.venv"
elif [ -d "$REPO_ROOT/.venv" ]; then
    REAL_VENV="$REPO_ROOT/.venv"
elif [ -d "$REPO_ROOT/../.venv" ]; then
    REAL_VENV="$(cd "$REPO_ROOT/.." && pwd)/.venv"
elif [ -d "/home/testovinovi/judge-guard-core-master/.venv" ]; then
    REAL_VENV="/home/testovinovi/judge-guard-core-master/.venv"
fi

if [ -n "$REAL_VENV" ] && [ -f "$REAL_VENV/bin/python3" ]; then
    VENV_PYTHON="$REAL_VENV/bin/python3"
else
    VENV_PYTHON="python3"
fi

TEST_SANDBOX=$(mktemp -d /tmp/judgeguard_worktree_gate_XXXXXX)
echo "🧪 Setting up test sandbox in: $TEST_SANDBOX"

cleanup() {
    if [ "$KEEP_SANDBOX" != "1" ]; then
        rm -rf "$TEST_SANDBOX"
    else
        echo "ℹ️ Preserved sandbox at: $TEST_SANDBOX"
    fi
}
trap cleanup EXIT

# 1. Initialize Git sandbox repository
cd "$TEST_SANDBOX"
git init -b master >/dev/null 2>&1
git config user.name "JudgeGuard Tester"
git config user.email "tester@judgeguard.local"

# Copy essential files into sandbox
cp "$SCRIPT_DIR/judge_guard.py" "$TEST_SANDBOX/"
cp "$SCRIPT_DIR/gemini_cli.sh" "$TEST_SANDBOX/"
cp "$SCRIPT_DIR/qwen_cli.sh" "$TEST_SANDBOX/"
cp "$SCRIPT_DIR/research_pipeline.py" "$TEST_SANDBOX/" 2>/dev/null || true
cp -r "$SCRIPT_DIR/src" "$TEST_SANDBOX/"
mkdir -p "$TEST_SANDBOX/.cache"
[ -f "$SCRIPT_DIR/.gitignore" ] && cp "$SCRIPT_DIR/.gitignore" "$TEST_SANDBOX/.gitignore" 2>/dev/null || true
[ -f "$REPO_ROOT/.env" ] && cp "$REPO_ROOT/.env" "$TEST_SANDBOX/.env" 2>/dev/null || true

# Export TEST_MODE for ticket verification in test sandbox
export JUDGEGUARD_TEST_MODE=1

# Link virtual environment into sandbox
if [ -n "$REAL_VENV" ] && [ -d "$REAL_VENV" ]; then
    ln -s "$REAL_VENV" "$TEST_SANDBOX/.venv"
fi

# Initial commit on master
echo "# Initial Master File" > README.md
git add .
git commit -m "initial commit" >/dev/null 2>&1
INITIAL_MASTER_SHA=$(git rev-parse master)
echo "📍 Initial master commit: $INITIAL_MASTER_SHA"

# Simulate user's dirty working tree (uncommitted work)
echo "CRITICAL: USER UNCOMMITTED CHANGES - MUST NEVER BE LOST" > USER_DIRTY_WORK.txt
echo "User initial log" > WORK_LOG.md

chmod +x gemini_cli.sh qwen_cli.sh judge_guard.py

echo ""
echo "========================================================================"
echo "TEST 1: Failing Task under gemini_cli.sh (Intentional Failure)"
echo "========================================================================"

set +e
./gemini_cli.sh --worktree "Failing Test Action" "bash -c 'echo some_data > bad_output.txt; exit 1'"
FAIL_EXIT=$?
set -e

echo "Exit code of failing task: $FAIL_EXIT"
if [ $FAIL_EXIT -eq 0 ]; then
    echo "❌ Assertion Failed: gemini_cli.sh should have returned non-zero exit code!"
    exit 1
fi
echo "✅ Assertion 1 Passed: Process returned failure exit code ($FAIL_EXIT)"

CURRENT_MASTER_SHA=$(git rev-parse master)
if [ "$CURRENT_MASTER_SHA" != "$INITIAL_MASTER_SHA" ]; then
    echo "❌ Assertion Failed: Master commit moved! Expected $INITIAL_MASTER_SHA, got $CURRENT_MASTER_SHA"
    exit 1
fi
echo "✅ Assertion 2 Passed: Master branch remained on exact same commit ($INITIAL_MASTER_SHA)"

COMMITS_COUNT=$(git rev-list --count master)
if [ "$COMMITS_COUNT" -ne 1 ]; then
    echo "❌ Assertion Failed: New commits detected on master! Count: $COMMITS_COUNT"
    exit 1
fi
echo "✅ Assertion 3 Passed: Zero new commits on master branch"

if [ ! -f "USER_DIRTY_WORK.txt" ]; then
    echo "❌ Assertion Failed: User's uncommitted file was deleted!"
    exit 1
fi
USER_CONTENT=$(cat USER_DIRTY_WORK.txt)
if [ "$USER_CONTENT" != "CRITICAL: USER UNCOMMITTED CHANGES - MUST NEVER BE LOST" ]; then
    echo "❌ Assertion Failed: User's uncommitted content was modified!"
    exit 1
fi
echo "✅ Assertion 4 Passed: User uncommitted changes completely intact"

if [ -f "bad_output.txt" ]; then
    echo "❌ Assertion Failed: Leaked unverified artifact into master!"
    exit 1
fi
echo "✅ Assertion 5 Passed: No unverified changes leaked into master"

echo ""
echo "========================================================================"
echo "TEST 2: Successful Task under gemini_cli.sh (Golden Path Integration)"
echo "========================================================================"

set +e
./gemini_cli.sh --worktree "Successful Golden Action" "bash -c 'echo golden_data_123 > golden_output.txt'"
SUCCESS_EXIT=$?
set -e

echo "Exit code of successful task: $SUCCESS_EXIT"
if [ $SUCCESS_EXIT -ne 0 ]; then
    echo "❌ Assertion Failed: gemini_cli.sh failed with exit code $SUCCESS_EXIT"
    exit 1
fi
echo "✅ Assertion 6 Passed: gemini_cli.sh succeeded with exit code 0"

NEW_MASTER_SHA=$(git rev-parse master)
if [ "$NEW_MASTER_SHA" = "$INITIAL_MASTER_SHA" ]; then
    echo "❌ Assertion Failed: Master branch did not advance after successful task!"
    exit 1
fi
echo "✅ Assertion 7 Passed: Master branch advanced to verified commit ($NEW_MASTER_SHA)"

if [ ! -f "golden_output.txt" ]; then
    echo "❌ Assertion Failed: Expected artifact golden_output.txt was not integrated!"
    exit 1
fi
echo "✅ Assertion 8 Passed: Verified artifact successfully integrated into master"

USER_CONTENT_AFTER=$(cat USER_DIRTY_WORK.txt)
if [ "$USER_CONTENT_AFTER" != "CRITICAL: USER UNCOMMITTED CHANGES - MUST NEVER BE LOST" ]; then
    echo "❌ Assertion Failed: User dirty work corrupted during successful merge!"
    exit 1
fi
echo "✅ Assertion 9 Passed: User uncommitted file remained intact during integration"

# Verify cryptographic HMAC signature on the newly merged commit
LATEST_VERDICT=$(ls -t .cache/verdicts/verdict_*.json | head -1)
echo "Inspecting verdict ticket: $LATEST_VERDICT"

set +e
"$VENV_PYTHON" judge_guard.py --verify-signature "$LATEST_VERDICT" "$NEW_MASTER_SHA"
SIG_VERIFY_RES=$?
set -e

if [ $SIG_VERIFY_RES -ne 0 ]; then
    echo "❌ Assertion Failed: Cryptographic signature verification failed for merged commit $NEW_MASTER_SHA!"
    exit 1
fi
echo "✅ Assertion 10 Passed: Cryptographic signature is valid and bound to $NEW_MASTER_SHA"

# Verify that verifying with WRONG SHA is strictly rejected
set +e
WRONG_SHA="0000000000000000000000000000000000000000"
"$VENV_PYTHON" judge_guard.py --verify-signature "$LATEST_VERDICT" "$WRONG_SHA"
WRONG_SIG_RES=$?
set -e

if [ $WRONG_SIG_RES -eq 0 ]; then
    echo "❌ Assertion Failed: Signature check accepted invalid/wrong commit SHA!"
    exit 1
fi
echo "✅ Assertion 11 Passed: Wrong commit SHA correctly rejected by signature verifier"

echo ""
echo "========================================================================"
echo "TEST 3: Qwen CLI Worktree Gate (Failure & Success Checks)"
echo "========================================================================"

BEFORE_QWEN_SHA=$(git rev-parse master)

# Failing Qwen task
set +e
./qwen_cli.sh --worktree "Failing Qwen Action" "bash -c 'exit 2'"
QWEN_FAIL_EXIT=$?
set -e

if [ $QWEN_FAIL_EXIT -eq 0 ]; then
    echo "❌ Assertion Failed: qwen_cli.sh should have returned non-zero exit code!"
    exit 1
fi
QWEN_CHECK_SHA=$(git rev-parse master)
if [ "$QWEN_CHECK_SHA" != "$BEFORE_QWEN_SHA" ]; then
    echo "❌ Assertion Failed: Master moved after failing qwen task!"
    exit 1
fi
echo "✅ Assertion 12 Passed: Qwen failure quarantined, master unchanged"

# Successful Qwen task
set +e
./qwen_cli.sh --worktree "Successful Qwen Action" "bash -c 'echo qwen_success > qwen_out.txt'"
QWEN_SUCC_EXIT=$?
set -e

if [ $QWEN_SUCC_EXIT -ne 0 ]; then
    echo "❌ Assertion Failed: qwen_cli.sh failed with exit code $QWEN_SUCC_EXIT"
    exit 1
fi
QWEN_FINAL_SHA=$(git rev-parse master)
if [ "$QWEN_FINAL_SHA" = "$BEFORE_QWEN_SHA" ]; then
    echo "❌ Assertion Failed: Master did not advance after successful qwen task!"
    exit 1
fi
echo "✅ Assertion 13 Passed: Qwen success integrated into master ($QWEN_FINAL_SHA)"

echo ""
echo "========================================================================"
echo "🎉 ALL 13 DRAFT WORKTREE INTEGRATION ASSERTIONS PASSED!"
echo "========================================================================"
exit 0
