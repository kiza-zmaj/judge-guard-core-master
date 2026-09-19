#!/usr/bin/env bash
# AURI Setup Script — One-time environment configuration
# Usage: chmod +x scripts/setup.sh && ./scripts/setup.sh
set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
TABLE_NAME="auri-users"
SECRET_NAME="auri/anthropic-key"
ROLE_NAME="auri-lambda-role"

echo "============================================"
echo "  AURI — Setup Script"
echo "============================================"
echo ""

# -------------------------------------------------------------------
# 1. Check prerequisites
# -------------------------------------------------------------------
echo "🔍 Checking prerequisites..."

command -v aws >/dev/null 2>&1 || { echo "❌ AWS CLI not found. Install: pip install awscli"; exit 1; }
command -v ask >/dev/null 2>&1 || { echo "❌ ASK CLI not found. Install: npm install -g ask-cli"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "❌ Python 3 not found."; exit 1; }

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "  ✅ AWS CLI:  $(aws --version 2>&1 | head -1)"
echo "  ✅ ASK CLI:  $(ask --version 2>&1 || echo 'installed')"
echo "  ✅ Python:   $PYTHON_VERSION"
echo ""

# -------------------------------------------------------------------
# 2. Create DynamoDB table
# -------------------------------------------------------------------
echo "📦 Setting up DynamoDB table '$TABLE_NAME'..."

if aws dynamodb describe-table --table-name "$TABLE_NAME" --region "$REGION" >/dev/null 2>&1; then
    echo "  ✅ Table '$TABLE_NAME' already exists."
else
    aws dynamodb create-table \
        --table-name "$TABLE_NAME" \
        --attribute-definitions AttributeName=userId,AttributeType=S \
        --key-schema AttributeName=userId,KeyType=HASH \
        --billing-mode PAY_PER_REQUEST \
        --region "$REGION" \
        --tags Key=Project,Value=AURI >/dev/null

    # Enable TTL
    aws dynamodb update-time-to-live \
        --table-name "$TABLE_NAME" \
        --time-to-live-specification "Enabled=true,AttributeName=ttl" \
        --region "$REGION" >/dev/null

    echo "  ✅ Table '$TABLE_NAME' created with TTL enabled."
fi
echo ""

# -------------------------------------------------------------------
# 3. Store Anthropic API key in Secrets Manager
# -------------------------------------------------------------------
echo "🔐 Setting up Secrets Manager..."

if aws secretsmanager describe-secret --secret-id "$SECRET_NAME" --region "$REGION" >/dev/null 2>&1; then
    echo "  ✅ Secret '$SECRET_NAME' already exists."
    read -rp "  ↳ Update the API key? (y/N): " update_key
    if [[ "$update_key" =~ ^[Yy]$ ]]; then
        read -rsp "  Enter your Anthropic API key: " api_key
        echo ""
        aws secretsmanager put-secret-value \
            --secret-id "$SECRET_NAME" \
            --secret-string "{\"ANTHROPIC_API_KEY\": \"$api_key\"}" \
            --region "$REGION" >/dev/null
        echo "  ✅ Secret updated."
    fi
else
    read -rsp "  Enter your Anthropic API key: " api_key
    echo ""
    aws secretsmanager create-secret \
        --name "$SECRET_NAME" \
        --description "Anthropic API key for AURI Alexa Skill" \
        --secret-string "{\"ANTHROPIC_API_KEY\": \"$api_key\"}" \
        --region "$REGION" >/dev/null
    echo "  ✅ Secret '$SECRET_NAME' created."
fi
echo ""

# -------------------------------------------------------------------
# 4. Install Python dependencies
# -------------------------------------------------------------------
echo "📦 Installing Python dependencies..."
LAMBDA_DIR="$(cd "$(dirname "$0")/../lambda" && pwd)"

if [ -f "$LAMBDA_DIR/requirements.txt" ]; then
    pip install -r "$LAMBDA_DIR/requirements.txt" -t "$LAMBDA_DIR/" --quiet --upgrade
    echo "  ✅ Dependencies installed to $LAMBDA_DIR/"
else
    echo "  ⚠️  No requirements.txt found at $LAMBDA_DIR/"
fi
echo ""

# -------------------------------------------------------------------
# 5. Configure ASK CLI (if needed)
# -------------------------------------------------------------------
echo "🔧 Checking ASK CLI configuration..."
if [ -f "$HOME/.ask/cli_config" ] || [ -f "$HOME/.ask/auth_info" ]; then
    echo "  ✅ ASK CLI is configured."
else
    echo "  ⚠️  ASK CLI not configured. Running 'ask configure'..."
    ask configure
fi
echo ""

# -------------------------------------------------------------------
# Done
# -------------------------------------------------------------------
echo "============================================"
echo "  ✅ AURI Setup Complete!"
echo "============================================"
echo ""
echo "  Next steps:"
echo "    1. cd auri/"
echo "    2. ./scripts/deploy.sh"
echo "    3. ./scripts/test.sh"
echo ""
echo "  Resources created:"
echo "    • DynamoDB: $TABLE_NAME"
echo "    • Secret:   $SECRET_NAME"
echo "    • Region:   $REGION"
echo ""
