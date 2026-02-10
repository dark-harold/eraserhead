#!/usr/bin/env bash
# 😐 Code formatting and linting
# Making ugly code presentably ugly

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "😐 Harold's Formatting: Polishing the pain"
echo "=================================================="
echo ""

cd "$PROJECT_ROOT"

# 😐 Format with ruff
echo "🎨 Formatting code with ruff..."
if command -v ruff &> /dev/null; then
    ruff format .
    echo -e "${GREEN}✓${NC} Code formatted. Harold approves of cosmetic improvements."
else
    echo -e "${YELLOW}⚠${NC} ruff not installed. Harold suggests: pip install ruff"
    exit 1
fi

echo ""

# 😐 Lint and auto-fix with ruff
echo "🔍 Linting and fixing issues..."
ruff check . --fix || true

echo ""

# 😐 Final lint check (no auto-fix)
echo "🔍 Final lint verification..."
if ruff check .; then
    echo -e "${GREEN}✓${NC} No linting issues. Harold's code is presentable."
else
    echo -e "${YELLOW}⚠${NC} Some linting issues remain. Harold hides them with a smile."
fi

echo ""
echo "=================================================="
echo "😐 Formatting complete. Code is as good as Harold's poker face."
