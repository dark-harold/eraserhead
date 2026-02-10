#!/usr/bin/env bash
# 😐 Test execution script
# Tests that pass locally and fail everywhere else

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "😐 Harold's Test Suite: Breaking code with a smile"
echo "=================================================="
echo ""

cd "$PROJECT_ROOT"

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# 😐 Run pytest with coverage
echo "🧪 Running tests with coverage..."
if pytest \
    --cov=src \
    --cov-report=term-missing \
    --cov-report=html:htmlcov \
    --tb=short \
    -v; then
    echo -e "${GREEN}✓${NC} Tests passed! Harold is pleasantly surprised."
else
    echo -e "${RED}✗${NC} Tests failed! Harold expected this."
    exit 1
fi

echo ""

# 😐 Check coverage threshold
echo "📊 Checking coverage threshold (>80%)..."
COVERAGE=$(pytest --cov=src --cov-report=term | grep "TOTAL" | awk '{print $NF}' | sed 's/%//')

if [ -z "$COVERAGE" ]; then
    echo -e "${RED}✗${NC} Could not determine coverage. Harold is confused."
    exit 1
fi

if (( $(echo "$COVERAGE >= 80" | bc -l) )); then
    echo -e "${GREEN}✓${NC} Coverage: ${COVERAGE}% (meets 80% threshold)"
    echo "Harold demands quality while hiding pain."
else
    echo -e "${RED}✗${NC} Coverage: ${COVERAGE}% (below 80% threshold)"
    echo "Harold is disappointed. More tests required."
    exit 1
fi

echo ""
echo "=================================================="
echo -e "${GREEN}😐 All tests passed with sufficient coverage!${NC}"
echo "Harold smiles confidently while knowing edge cases lurk."
