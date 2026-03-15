#!/bin/bash
# VeriNet UI — Start the Next.js web interface.
#
# Usage:
#   ./scripts/run_ui.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT/ui/webapp"

echo "======================================"
echo "  VeriNet UI"
echo "======================================"

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

echo "Starting Next.js dev server on http://localhost:3000"
echo ""

npm run dev
