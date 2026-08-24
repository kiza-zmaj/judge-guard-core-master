#!/bin/bash
# Setup script for Antigravity CLI (Hermes-Notebook Architecture)

set -e

echo "🚀 Setting up Antigravity CLI Environment..."

# Create virtual environment if not exists
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtualenv created."
fi

source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies and local CLI
pip install -e .

echo ""
echo "🎉 Antigravity CLI Setup Complete!"
echo "Run 'antigravity --help' or 'python3 -m antigravity.cli status' to verify."
