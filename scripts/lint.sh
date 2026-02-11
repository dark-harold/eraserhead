#!/usr/bin/env bash
# 😐 Harold's comprehensive linting and static analysis
# Dark Harold finds ALL the issues

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
    echo ""
}

cd "$PROJECT_ROOT"

exit_code=0

# 😐 Step 1: Ruff linting
log_section "Ruff: Harold's Code Quality Scanner"
if ruff check src/ tests/; then
    log_info "Ruff checks passed. Harold is cautiously pleased."
else
    log_error "Ruff found issues. Dark Harold expected this."
    exit_code=1
fi

# 😐 Step 2: MyPy type checking
log_section "MyPy: Harold's Type Safety Paranoia"
if mypy src/; then
    log_info "Type checks passed. Harold's types are sound."
else
    log_error "Type errors found. Harold sighs deeply."
    exit_code=1
fi

# 😐 Step 3: Pyright (alternative type checker)
log_section "Pyright: Second Opinion on Types"
if command -v pyright &> /dev/null; then
    if pyright src/; then
        log_info "Pyright agrees. Types are solid."
    else
        log_warn "Pyright disagrees with MyPy. Harold is confused but pragmatic."
        # Don't fail on Pyright errors, it's a second opinion
    fi
else
    log_warn "Pyright not installed. Skipping."
fi

# 😐 Step 4: Bandit security scanning
log_section "Bandit: Dark Harold's Security Audit"
if bandit -r src/ -c pyproject.toml --quiet; then
    log_info "No security issues found. Harold is suspicious but accepting."
else
    log_error "Security issues detected. Dark Harold's paranoia validated."
    exit_code=1
fi

# 😐 Step 5: Vulture dead code detection
log_section "Vulture: Finding the Bodies (Dead Code)"
if command -v vulture &> /dev/null; then
    if vulture src/ --min-confidence 80; then
        log_info "No dead code found. Everything serves a purpose."
    else
        log_warn "Dead code detected. Harold marks it for cleanup."
        # Don't fail on dead code, just warn
    fi
else
    log_warn "Vulture not installed. Skipping dead code detection."
fi

# 😐 Step 6: Radon complexity metrics
log_section "Radon: Measuring Harold's Pain (Complexity)"
if command -v radon &> /dev/null; then
    log_info "Cyclomatic Complexity:"
    radon cc src/ --average --show-complexity || true
    echo ""
    log_info "Maintainability Index:"
    radon mi src/ --show || true
else
    log_warn "Radon not installed. Skipping complexity analysis."
fi

# 😐 Step 7: Interrogate docstring coverage
log_section "Interrogate: Docstring Coverage Check"
if command -v interrogate &> /dev/null; then
    if interrogate -vv src/ --fail-under=70; then
        log_info "Docstring coverage adequate. Harold documents reluctantly."
    else
        log_warn "Docstring coverage below 70%. Internet Historian Harold disapproves."
        # Don't fail on docstring coverage, just warn
    fi
else
    log_warn "Interrogate not installed. Skipping docstring check."
fi

# Final summary
echo ""
log_section "Linting Summary"
if [ $exit_code -eq 0 ]; then
    log_info "All critical checks passed! 😐"
    log_info "Harold ships with cautious confidence."
else
    log_error "Some checks failed. Fix them before committing."
    log_error "Dark Harold demands perfection (or at least working code)."
fi

exit $exit_code
