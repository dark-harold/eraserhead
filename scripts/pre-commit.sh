#!/usr/bin/env bash
# 😐 Pre-commit quality gates
# The Last Stand Before Committing to Disaster

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "😐 Harold's Pre-Commit Gates: Multiple layers of paranoia"
echo "========================================================"
echo ""

EXIT_CODE=0

# 😐 Gate 1: Formatting
echo "Gate 1: Formatting..."
if bash "$SCRIPT_DIR/format.sh"; then
    echo -e "${GREEN}✓${NC} Gate 1 passed"
else
    echo -e "${RED}✗${NC} Gate 1 failed"
    EXIT_CODE=1
fi

echo ""

# 😐 Gate 2: Security
echo "Gate 2: Security scanning..."
if bash "$SCRIPT_DIR/security-scan.sh"; then
    echo -e "${GREEN}✓${NC} Gate 2 passed"
else
    echo -e "${RED}✗${NC} Gate 2 failed"
    EXIT_CODE=1
fi

echo ""

# 😐 Gate 3: Tests (if tests exist)
if [ -d "tests" ] && [ "$(ls -A tests)" ]; then
    echo "Gate 3: Test suite..."
    if bash "$SCRIPT_DIR/test.sh"; then
        echo -e "${GREEN}✓${NC} Gate 3 passed"
    else
        echo -e "${RED}✗${NC} Gate 3 failed"
        EXIT_CODE=1
    fi
else
    echo -e "${YELLOW}⚠${NC} Gate 3: No tests found (Harold is concerned)"
fi

echo ""
echo "========================================================"

if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}😐 All gates passed!${NC}"
    echo "Harold approves your commit with nervous confidence."
    echo "You may proceed to: git commit"
else
    echo -e "${RED}😐 Quality gates failed!${NC}"
    echo "Dark Harold blocks your commit. Fix issues and try again."
    echo ""
    echo "Harold's wisdom: Quality gates exist for your future self."
fi

exit $EXIT_CODE
