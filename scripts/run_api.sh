#!/bin/bash
# VeriNet API Server — Start the REST API.
#
# Usage:
#   ./scripts/run_api.sh [--port 8080] [--subnet-mode]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

PORT="${PORT:-8080}"

echo "======================================"
echo "  VeriNet API Server"
echo "======================================"
echo "  Port: $PORT"
echo "======================================"
echo ""

python api/server.py --port "$PORT" "$@"
