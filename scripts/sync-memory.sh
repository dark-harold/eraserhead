#!/usr/bin/env bash
# 😐 Sync spec-kit artifacts into tinyclaw memory
# Harold remembers everything. Unfortunately.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
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

# 😐 Check if tinyclaw is available
if ! command -v tinyclaw &> /dev/null; then
    log_error "tinyclaw not found. Harold's memory system unavailable."
    echo "Install with: npm install -g @mrcloudchase/tinyclaw"
    exit 1
fi

log_info "Syncing artifacts to tinyclaw memory..."
echo ""

# 😐 Files to sync into memory
SYNC_FILES=(
    ".specify/memory/constitution.md"
    "TINYCLAW.md"
    "README.md"
    "specs/001-anemochory-protocol/spec.md"
    "specs/001-anemochory-protocol/research.md"
)

SYNCED=0
FAILED=0

cd "$PROJECT_ROOT"

for file in "${SYNC_FILES[@]}"; do
    if [ -f "$file" ]; then
        log_info "Syncing: $file"
        
        # 😐 Use tinyclaw CLI to store file in memory
        # This chunks the file and stores with embeddings
        if tinyclaw memory store --file "$file" --source "$file" 2>/dev/null; then
            ((SYNCED++))
        else
            log_warn "Failed to sync: $file"
            ((FAILED++))
        fi
    else
        log_warn "File not found: $file"
        ((FAILED++))
    fi
done

echo ""
echo "=================================================="
log_info "Sync complete"
log_info "  Synced: $SYNCED files"
if [ $FAILED -gt 0 ]; then
    log_warn "  Failed: $FAILED files"
fi

echo ""
log_info "Memory location: ~/.config/tinyclaw/memory/memory.db"
log_info "Test search: tinyclaw memory search 'anemochory protocol'"
echo ""
log_info "😐 Harold's memory is updated. He never forgets."
log_warn "🌑 Dark Harold reminder: Every memory is a liability in the wrong hands."
