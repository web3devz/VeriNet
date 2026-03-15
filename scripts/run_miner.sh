#!/bin/bash
# VeriNet Miner — Start the fact-verification miner neuron.
#
# Usage:
#   ./scripts/run_miner.sh [--netuid 1] [--subtensor.network local]
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
WALLET_NAME="${WALLET_NAME:-miner}"
WALLET_HOTKEY="${WALLET_HOTKEY:-default}"
AXON_PORT="${AXON_PORT:-8901}"

echo "======================================"
echo "  VeriNet Miner"
echo "======================================"
echo "  Network:    $NETWORK"
echo "  NetUID:     $NETUID"
echo "  Wallet:     $WALLET_NAME / $WALLET_HOTKEY"
echo "  Axon Port:  $AXON_PORT"
echo "======================================"
echo ""

python neurons/miner.py \
    --netuid "$NETUID" \
    --wallet.name "$WALLET_NAME" \
    --wallet.hotkey "$WALLET_HOTKEY" \
    --axon.port "$AXON_PORT" \
    --subtensor.network "$NETWORK" \
    --logging.info \
    "$@"
