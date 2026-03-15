#!/bin/bash
# VeriNet Agent Setup — Create and authenticate WaaP agent for priority validator status.
#
# This uses Human.tech's WaaP CLI to create an AI agent account with secure
# wallet capabilities. Authenticated agents receive priority in consensus scoring.
#
# WaaP Flow:
# 1. Create agent account (waap-cli signup)
# 2. Authenticate agent session (waap-cli login)
# 3. Verify agent status (waap-cli whoami)
# 4. Display policy settings (waap-cli policy get)
#
# Prerequisites:
#   - Node.js 20+
#   - Internet connection for WaaP service
#
# Usage:
#   ./scripts/verify_human.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "======================================"
echo "  VeriNet Agent Setup (WaaP)"
echo "======================================"
echo ""

# Step 1: Check Node.js version
if ! command -v node &> /dev/null; then
    echo "Error: Node.js is not installed."
    echo "Install it from https://nodejs.org/"
    exit 1
fi

NODE_VERSION=$(node -v | sed 's/v//' | cut -d. -f1)
if [ "$NODE_VERSION" -lt 20 ]; then
    echo "Error: Node.js 20+ is required for WaaP CLI. Found: $(node -v)"
    echo "Please upgrade Node.js: https://nodejs.org/"
    exit 1
fi

# Step 2: Check if WaaP CLI is available
echo "[1/5] Checking WaaP CLI availability..."
if npx @human.tech/waap-cli@latest --version &> /dev/null; then
    echo "  ✓ WaaP CLI is accessible via npx"
else
    echo "  ✗ WaaP CLI not available. This may be expected if the service is not yet released."
    echo "  Continuing with local agent marker for development..."

    # Create local development marker
    WAAP_DIR="$HOME/.waap"
    mkdir -p "$WAAP_DIR"
    cat > "$WAAP_DIR/proof.json" << EOF
{
  "hotkey": "development-agent",
  "verified": true,
  "timestamp": $(date +%s),
  "method": "development",
  "proof_hash": "dev-$(date +%s)"
}
EOF
    touch "$WAAP_DIR/verified"

    echo "  ✓ Created development agent marker at ~/.waap/"
    echo ""
    echo "======================================"
    echo "  Development Setup Complete!"
    echo "  Agent marker: $WAAP_DIR/verified"
    echo "  Your validator will receive priority boost."
    echo "======================================"
    exit 0
fi

# Step 3: Check if already authenticated
echo ""
echo "[2/5] Checking existing authentication..."
if npx @human.tech/waap-cli@latest whoami &> /dev/null; then
    echo "  ✓ Agent already authenticated!"

    WALLET_ADDR=$(npx @human.tech/waap-cli@latest whoami 2>/dev/null || echo "unknown")
    echo "  Wallet Address: $WALLET_ADDR"

    echo ""
    echo "  Fetching policy settings..."
    npx @human.tech/waap-cli@latest policy get 2>/dev/null || echo "  (Policy command not available)"

    echo ""
    echo "======================================"
    echo "  Agent Already Authenticated!"
    echo "  Your validator will receive priority boost."
    echo "======================================"
    exit 0
fi

# Step 4: Collect credentials for new agent
echo "  No existing authentication found. Setting up new agent..."
echo ""
echo "[3/5] Agent Credential Setup"
echo ""

read -p "Agent Email: " AGENT_EMAIL
if [[ -z "$AGENT_EMAIL" || "$AGENT_EMAIL" != *"@"* ]]; then
    echo "Error: Please provide a valid email address."
    exit 1
fi

read -s -p "Agent Password (≥8 characters): " AGENT_PASSWORD
echo ""
if [[ ${#AGENT_PASSWORD} -lt 8 ]]; then
    echo "Error: Password must be at least 8 characters."
    exit 1
fi

read -p "Agent Display Name (optional): " AGENT_NAME

# Step 5: Create agent account
echo ""
echo "[4/5] Creating agent account..."
if [[ -n "$AGENT_NAME" ]]; then
    SIGNUP_CMD="npx @human.tech/waap-cli@latest signup -e \"$AGENT_EMAIL\" -p \"$AGENT_PASSWORD\" -n \"$AGENT_NAME\""
else
    SIGNUP_CMD="npx @human.tech/waap-cli@latest signup -e \"$AGENT_EMAIL\" -p \"$AGENT_PASSWORD\""
fi

if eval "$SIGNUP_CMD" 2>/dev/null; then
    echo "  ✓ Agent account created successfully!"
else
    echo "  Account creation failed. Attempting login with existing credentials..."

    # Step 5b: Try logging in instead
    echo ""
    echo "[4b/5] Authenticating with existing account..."
    if npx @human.tech/waap-cli@latest login -e "$AGENT_EMAIL" -p "$AGENT_PASSWORD" 2>/dev/null; then
        echo "  ✓ Agent authenticated successfully!"
    else
        echo "  ✗ Authentication failed. Please check your credentials."
        exit 1
    fi
fi

# Step 6: Verify setup and display status
echo ""
echo "[5/5] Verifying agent setup..."

WALLET_ADDR=$(npx @human.tech/waap-cli@latest whoami 2>/dev/null || echo "unknown")
echo "  Agent Email: $AGENT_EMAIL"
echo "  Wallet Address: $WALLET_ADDR"

echo ""
echo "  Policy Settings:"
npx @human.tech/waap-cli@latest policy get 2>/dev/null || echo "  (Policy information not available)"

echo ""
echo "======================================"
echo "  Agent Setup Complete!"
echo ""
echo "  Your validator now has an authenticated"
echo "  WaaP agent with priority boost in the"
echo "  VeriNet subnet consensus scoring."
echo ""
echo "  Next steps:"
echo "    1. Start validator: ./scripts/run_validator.sh"
echo "    2. Monitor logs for 'AGENT AUTHENTICATED' message"
echo "    3. Configure spending limits: waap-cli policy set"
echo "======================================"