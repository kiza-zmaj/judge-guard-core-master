#!/usr/bin/env bash
# AURI Deploy Script — Build and deploy to AWS
# Usage: chmod +x scripts/deploy.sh && ./scripts/deploy.sh
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LAMBDA_DIR="$PROJECT_DIR/lambda"

echo "============================================"
echo "  AURI — Deploy Script"
echo "============================================"
echo ""

# -------------------------------------------------------------------
# 1. Install/update dependencies
# -------------------------------------------------------------------
echo "📦 Installing dependencies..."
pip install -r "$LAMBDA_DIR/requirements.txt" -t "$LAMBDA_DIR/" --quiet --upgrade
echo "  ✅ Dependencies installed."
echo ""

# -------------------------------------------------------------------
# 2. Deploy with ASK CLI
# -------------------------------------------------------------------
echo "🚀 Deploying with ASK CLI..."
cd "$PROJECT_DIR"
ask deploy

echo ""
echo "  ✅ Deployment complete!"
echo ""

# -------------------------------------------------------------------
# 3. Get skill info
# -------------------------------------------------------------------
echo "📋 Skill Information:"
SKILL_ID=$(cat .ask/ask-states.json 2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
profiles = data.get('profiles', {})
default = profiles.get('default', {})
print(default.get('skillId', 'N/A'))
" 2>/dev/null || echo "N/A")

echo "  Skill ID: $SKILL_ID"
echo ""

# -------------------------------------------------------------------
# 4. Print test commands
# -------------------------------------------------------------------
echo "============================================"
echo "  Test Commands"
echo "============================================"
echo ""
echo "  # Simulate a conversation:"
echo "  ask simulate --text 'abrir auri' --locale pt-BR --skill-id $SKILL_ID"
echo ""
echo "  # Interactive dialog:"
echo "  ask dialog --locale pt-BR"
echo ""
echo "  # Validate the model:"
echo "  ask validate --locales pt-BR"
echo ""
echo "  # View Lambda logs:"
echo "  aws logs tail /aws/lambda/auri-skill --follow"
echo ""
