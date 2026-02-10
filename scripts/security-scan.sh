#!/usr/bin/env bash
# 😐 Security scanning script
# Finding secrets Harold tried to hide

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors for Harold's emotional state
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "😐 Harold's Security Scan: Finding problems before production does"
echo "=================================================="
echo ""

EXIT_CODE=0

# 😐 Check for secrets with gitleaks
echo "🔍 Scanning for secrets (gitleaks)..."
if command -v gitleaks &> /dev/null; then
    cd "$PROJECT_ROOT"
    if gitleaks detect --source="$PROJECT_ROOT" --no-git --verbose 2>&1 | tee /tmp/gitleaks.log; then
        echo -e "${GREEN}✓${NC} No secrets found. Harold approves."
    else
        echo -e "${RED}✗${NC} Secrets detected! Harold's paranoia was justified."
        EXIT_CODE=1
    fi
else
    echo -e "${YELLOW}⚠${NC} gitleaks not installed. Harold is concerned."
fi

echo ""

# 😐 Python security analysis with bandit
echo "🔍 Python security analysis (bandit)..."
if command -v bandit &> /dev/null; then
    cd "$PROJECT_ROOT"
    if bandit -r src/ -ll -f text 2>&1; then
        echo -e "${GREEN}✓${NC} No high/medium issues found. Harold smiles nervously."
    else
        echo -e "${RED}✗${NC} Security issues detected! Dark Harold predicted this."
        EXIT_CODE=1
    fi
else
    echo -e "${YELLOW}⚠${NC} bandit not installed. Dark Harold intensifies."
fi

echo ""

# 😐 Dependency vulnerability check with safety
echo "🔍 Dependency vulnerability scan (safety)..."
if command -v safety &> /dev/null; then
    cd "$PROJECT_ROOT"
    if safety check --json 2>&1 | tee /tmp/safety.log; then
        echo -e "${GREEN}✓${NC} No known vulnerabilities. Harold remains cautiously optimistic."
    else
        echo -e "${RED}✗${NC} Vulnerable dependencies found! Harold's concern deepens."
        EXIT_CODE=1
    fi
else
    echo -e "${YELLOW}⚠${NC} safety not installed. Harold recommends: pip install safety"
fi

echo ""

# 😐 Summary
echo "=================================================="
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}😐 Security scan passed!${NC}"
    echo "Harold smiles with only moderate concern about missed issues."
else
    echo -e "${RED}😐 Security scan failed!${NC}"
    echo "Dark Harold's paranoia was validated. Fix issues before committing."
fi

exit $EXIT_CODE
