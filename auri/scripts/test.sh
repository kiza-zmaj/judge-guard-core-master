#!/usr/bin/env bash
# AURI Test Script — Run simulation tests
# Usage: chmod +x scripts/test.sh && ./scripts/test.sh
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

echo "============================================"
echo "  AURI — Test Script"
echo "============================================"
echo ""

# Get skill ID
SKILL_ID=$(cat .ask/ask-states.json 2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
profiles = data.get('profiles', {})
default = profiles.get('default', {})
print(default.get('skillId', ''))
" 2>/dev/null || echo "")

if [ -z "$SKILL_ID" ]; then
    echo "❌ Skill ID not found. Run ./scripts/deploy.sh first."
    exit 1
fi

echo "Skill ID: $SKILL_ID"
echo ""

# Test phrases
declare -a TESTS=(
    "abrir auri"
    "me ajuda com o clima de hoje"
    "ativa rotina bom dia"
    "meu nome é João"
    "o que é inteligência artificial"
    "desliga"
)

PASSED=0
FAILED=0

for phrase in "${TESTS[@]}"; do
    echo "🧪 Testing: '$phrase'"
    echo "---"

    result=$(ask simulate \
        --text "$phrase" \
        --locale pt-BR \
        --skill-id "$SKILL_ID" 2>&1) || true

    if echo "$result" | grep -q "outputSpeech"; then
        echo "  ✅ PASSED"
        PASSED=$((PASSED + 1))
    else
        echo "  ❌ FAILED"
        echo "  Response: $(echo "$result" | head -5)"
        FAILED=$((FAILED + 1))
    fi
    echo ""
done

echo "============================================"
echo "  Results: $PASSED passed, $FAILED failed"
echo "============================================"

# Run pytest if available
if command -v pytest >/dev/null 2>&1; then
    echo ""
    echo "🧪 Running unit tests..."
    cd "$PROJECT_DIR"
    pytest tests/ -v --tb=short 2>&1 || true
fi
