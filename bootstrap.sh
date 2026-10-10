#!/usr/bin/env bash
# Bootstrap research workspace and check all tools
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python3"

if [ ! -f "$VENV_PYTHON" ]; then
    echo "❌ Virtual environment .venv not found! Creating..."
    python3 -m venv "$SCRIPT_DIR/.venv"
fi

"$VENV_PYTHON" "$SCRIPT_DIR/bootstrap_workspace.py"
