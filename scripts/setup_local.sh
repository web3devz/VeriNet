#!/bin/bash
# VeriNet Local Setup — Full local subnet setup for development.
#
# This script:
# 1. Installs Python dependencies
# 2. Creates wallets for owner, miner, and validator
# 3. Sets up a local subnet
# 4. Registers neurons
# 5. Starts all components
#
# Prerequisites:
#   - Python 3.10+
#   - Node.js 18+
#   - Local Subtensor running on ws://127.0.0.1:9945
#
# Usage:
#   ./scripts/setup_local.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

NETWORK="local"
CHAIN_ENDPOINT="ws://127.0.0.1:9945"

echo "======================================"
echo "  VeriNet Local Setup"
echo "======================================"
echo ""

# Step 1: Install Python dependencies
echo "[1/6] Installing Python dependencies..."
pip install -e . 2>&1 | tail -5
echo ""

# Step 2: Install UI dependencies
echo "[2/6] Installing UI dependencies..."
cd ui/webapp && npm install 2>&1 | tail -3
cd "$PROJECT_ROOT"
echo ""

# Step 3: Create wallets
echo "[3/6] Creating wallets..."
echo "  Creating owner wallet..."
btcli wallet create --wallet-name owner --no-password 2>/dev/null || true
echo "  Creating miner wallet..."
btcli wallet create --wallet-name miner --no-password 2>/dev/null || true
echo "  Creating validator wallet..."
btcli wallet create --wallet-name validator --no-password 2>/dev/null || true
echo ""

# Step 4: Create subnet
echo "[4/6] Creating subnet..."
echo "  Note: Ensure local Subtensor is running at $CHAIN_ENDPOINT"
btcli subnet create --wallet-name owner --network "$CHAIN_ENDPOINT" 2>/dev/null || echo "  Subnet may already exist."
echo ""

# Step 5: Register neurons
echo "[5/6] Registering neurons..."
echo "  Registering miner..."
btcli subnets register --netuid 1 --wallet-name miner --hotkey default --network "$CHAIN_ENDPOINT" 2>/dev/null || echo "  Miner may already be registered."
echo "  Registering validator..."
btcli subnets register --netuid 1 --wallet-name validator --hotkey default --network "$CHAIN_ENDPOINT" 2>/dev/null || echo "  Validator may already be registered."
echo ""

# Step 6: Stake for validator permit
echo "[6/6] Staking for validator permit..."
btcli stake add --netuid 1 --wallet-name validator --hotkey default --partial --network "$CHAIN_ENDPOINT" 2>/dev/null || echo "  Staking may require manual interaction."
echo ""

echo "======================================"
echo "  Setup complete!"
echo ""
echo "  Start components in separate terminals:"
echo ""
echo "  Terminal 1 (API):       ./scripts/run_api.sh"
echo "  Terminal 2 (Miner):     ./scripts/run_miner.sh"
echo "  Terminal 3 (Validator): ./scripts/run_validator.sh"
echo "  Terminal 4 (UI):        ./scripts/run_ui.sh"
echo "======================================"
