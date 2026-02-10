#!/usr/bin/env bash
# 😐 Model health check script
# Verifying Harold's brain functionality

set -euo pipefail

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

echo "😐 Harold's Brain Health Check"
echo "=================================================="
echo ""

EXIT_CODE=0

# 😐 Check 1: Local inference server (CPU path)
echo "Checking local inference server (port 8080)..."
if curl -s http://127.0.0.1:8080/v1/models > /dev/null 2>&1; then
    MODELS=$(curl -s http://127.0.0.1:8080/v1/models | python3 -c "import sys, json; print(json.load(sys.stdin)['data'][0]['id'])" 2>/dev/null || echo "unknown")
    log_info "✓ llama.cpp server responding"
    log_info "  Model: $MODELS"
else
    log_warn "✗ llama.cpp server not responding (port 8080)"
    log_info "  Start with: ./scripts/llm-start-cpu.sh"
fi

echo ""

# 😐 Check 2: GPU inference server (vLLM path)
echo "Checking GPU inference server (port 8000)..."
if curl -s http://127.0.0.1:8000/v1/models > /dev/null 2>&1; then
    MODELS=$(curl -s http://127.0.0.1:8000/v1/models | python3 -c "import sys, json; print(json.load(sys.stdin)['data'][0]['id'])" 2>/dev/null || echo "unknown")
    log_info "✓ vLLM server responding"
    log_info "  Model: $MODELS"
else
    log_warn "✗ vLLM server not responding (port 8000)"
    log_info "  Start with: ./scripts/llm-start-gpu.sh"
fi

echo ""

# 😐 Check 3: tinyclaw installation
echo "Checking tinyclaw installation..."
if command -v tinyclaw &> /dev/null; then
    TINYCLAW_VERSION=$(tinyclaw --version 2>/dev/null || echo "unknown")
    log_info "✓ tinyclaw installed"
    log_info "  Version: $TINYCLAW_VERSION"
else
    log_error "✗ tinyclaw not installed"
    echo "  Install: npm install -g @mrcloudchase/tinyclaw"
    EXIT_CODE=1
fi

echo ""

# 😐 Check 4: tinyclaw memory database
echo "Checking tinyclaw memory..."
MEMORY_DB="$HOME/.config/tinyclaw/memory/memory.db"
if [ -f "$MEMORY_DB" ]; then
    DB_SIZE=$(stat -f%z "$MEMORY_DB" 2>/dev/null || stat -c%s "$MEMORY_DB" 2>/dev/null)
    DB_SIZE_MB=$((DB_SIZE / 1024 / 1024))
    log_info "✓ Memory database exists"
    log_info "  Location: $MEMORY_DB"
    log_info "  Size: ${DB_SIZE_MB}MB"
    
    # Test memory search
    if command -v tinyclaw &> /dev/null; then
        MEMORY_COUNT=$(tinyclaw memory search "test" 2>/dev/null | grep -c "content" || echo "0")
        log_info "  Indexed: $MEMORY_COUNT+ chunks"
    fi
else
    log_warn "✗ Memory database not found"
    log_info "  Initialize with: tinyclaw memory store --file README.md"
fi

echo ""

# 😐 Check 5: Model files
echo "Checking downloaded models..."
MODEL_DIR="$(dirname "$0")/../models/llama-cpp"
if [ -d "$MODEL_DIR" ] && [ "$(ls -A "$MODEL_DIR" 2>/dev/null)" ]; then
    MODEL_COUNT=$(find "$MODEL_DIR" -name "*.gguf" | wc -l)
    log_info "✓ Models directory exists"
    log_info "  GGUF files: $MODEL_COUNT"
    
    for model in "$MODEL_DIR"/*.gguf; do
        if [ -f "$model" ]; then
            MODEL_NAME=$(basename "$model")
            MODEL_SIZE=$(stat -f%z "$model" 2>/dev/null || stat -c%s "$model" 2>/dev/null)
            MODEL_SIZE_GB=$((MODEL_SIZE / 1024 / 1024 / 1024))
            log_info "  - $MODEL_NAME (${MODEL_SIZE_GB}GB)"
        fi
    done
else
    log_warn "✗ No models downloaded"
    log_info "  Download with: ./scripts/download-models.sh"
    EXIT_CODE=1
fi

echo ""
echo "=================================================="

if [ $EXIT_CODE -eq 0 ]; then
    log_info "Health check complete. Harold's brain is functioning."
    log_info "😐 All systems operational (with mild concern)"
else
    log_warn "Health check found issues. Harold needs attention."
    log_warn "😐 Fix issues and rerun health check"
fi

exit $EXIT_CODE
