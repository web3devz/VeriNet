#!/bin/bash
# VeriNet Validator — Start the fact-verification validator neuron.
#
# Usage:
#   ./scripts/run_validator.sh [--netuid 1] [--subtensor.network local]
#
# Prerequisites:
#   pip install -e .

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Default arguments
NETUID="${NETUID:-1}"
NETWORK="${NETWORK:-local}"
WALLET_NAME="${WALLET_NAME:-validator}"
WALLET_HOTKEY="${WALLET_HOTKEY:-default}"

echo "======================================"
echo "  VeriNet Validator"
echo "======================================"
echo "  Network:    $NETWORK"
echo "  NetUID:     $NETUID"
echo "  Wallet:     $WALLET_NAME / $WALLET_HOTKEY"
echo "======================================"
echo ""

python neurons/validator.py \
    --netuid "$NETUID" \
    --wallet.name "$WALLET_NAME" \
    --wallet.hotkey "$WALLET_HOTKEY" \
    --subtensor.network "$NETWORK" \
    --logging.info \
    "$@"
