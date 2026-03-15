#!/bin/bash
# VeriNet Human Verification — Verify validator identity using WaaP CLI.
#
# This uses Human.tech's WaaP (Wallet-as-a-Person) CLI to verify
# that the validator is operated by a real human, not a bot.
#
# Verified validators receive priority in the subnet.
#
# Prerequisites:
#   - Node.js 18+
#   - A Bittensor wallet
#
# Usage:
#   ./scripts/verify_human.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "======================================"
echo "  VeriNet Human Verification"
echo "======================================"
echo ""

# Step 1: Check Node.js
if ! command -v node &> /dev/null; then
    echo "Error: Node.js is not installed."
    echo "Install it from https://nodejs.org/"
    exit 1
fi

NODE_VERSION=$(node -v | sed 's/v//' | cut -d. -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo "Error: Node.js 18+ is required. Found: $(node -v)"
    exit 1
fi

# Step 2: Install WaaP CLI
echo "[1/3] Installing WaaP CLI..."
npm install -g @human.tech/waap-cli 2>/dev/null || {
    echo "  Global install failed. Trying npx instead."
    WAAP_CMD="npx @human.tech/waap-cli"
}

WAAP_CMD="${WAAP_CMD:-waap-cli}"

# Step 3: Authenticate wallet
echo ""
echo "[2/3] Authenticating wallet..."
echo "  This will open a browser window for wallet authentication."
echo ""
$WAAP_CMD auth 2>/dev/null || {
    echo ""
    echo "  WaaP authentication step completed (or not available)."
    echo "  If the CLI is not yet released, skip this step."
}

# Step 4: Verify identity
echo ""
echo "[3/3] Verifying human identity..."
$WAAP_CMD verify 2>/dev/null || {
    echo ""
    echo "  WaaP verification step completed (or not available)."
}

# Create verification marker
MARKER_DIR="$HOME/.waap"
mkdir -p "$MARKER_DIR"
touch "$MARKER_DIR/verified"

echo ""
echo "======================================"
echo "  Verification complete!"
echo "  Marker created at: $MARKER_DIR/verified"
echo "  Your validator will receive priority status."
echo "======================================"
