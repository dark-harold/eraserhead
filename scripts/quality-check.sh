#!/usr/bin/env bash
# 😐 Harold's Full Quality Check Suite
# Everything. All at once. Harold's comprehensive nightmare.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}😐${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}😐${NC} $1"
}

log_error() {
    echo -e "${RED}😐${NC} $1"
}

log_section() {
    echo ""
    echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
}

cd "$PROJECT_ROOT"

log_section "Harold's Full Quality Check"
log_info "Running all checks. Harold prepares for the worst."
echo ""

# Track failures
declare -a failed_checks=()

# 😐 Check 1: Format check
log_info "[1/6] Format check (ruff format --check)"
if ruff format --check src/ tests/; then
    log_info "✓ Format check passed"
else
    log_error "✗ Format check failed (run: ./scripts/format.sh)"
    failed_checks+=("format")
fi

# 😐 Check 2: Linting
log_info "[2/6] Linting (ruff check)"
if ruff check src/ tests/; then
    log_info "✓ Lint check passed"
else
    log_error "✗ Lint check failed"
    failed_checks+=("lint")
fi

# 😐 Check 3: Type checking
log_info "[3/6] Type checking (mypy)"
if mypy src/; then
    log_info "✓ Type check passed"
else
    log_error "✗ Type check failed"
    failed_checks+=("types")
fi

# 😐 Check 4: Security scanning
log_info "[4/6] Security scan (bandit)"
if bandit -r src/ -c pyproject.toml --quiet; then
    log_info "✓ Security scan passed"
else
    log_error "✗ Security issues found"
    failed_checks+=("security")
fi

# 😐 Check 5: Tests
log_info "[5/6] Running tests (pytest)"
if pytest tests/ --cov=src --cov-report=term-missing --tb=short; then
    log_info "✓ Tests passed"
else
    log_error "✗ Tests failed"
    failed_checks+=("tests")
fi

# 😐 Check 6: Dependency vulnerabilities
log_info "[6/6] Dependency scan (safety)"
if command -v safety &> /dev/null; then
    if safety scan --json; then
        log_info "✓ No vulnerable dependencies"
    else
        log_warn "⚠ Vulnerable dependencies found"
        failed_checks+=("dependencies")
    fi
else
    log_warn "Safety not installed, skipping dependency check"
fi

# Summary
log_section "Quality Check Summary"
if [ ${#failed_checks[@]} -eq 0 ]; then
    log_info "🎉 ALL CHECKS PASSED! 😐"
    log_info "Harold is shocked but ships anyway."
    exit 0
else
    log_error "Failed checks: ${failed_checks[*]}"
    log_error "Dark Harold refuses to ship broken code."
    exit 1
fi
