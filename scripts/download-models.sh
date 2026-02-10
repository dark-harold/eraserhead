#!/usr/bin/env bash
# 😐 Download local models for inference
# Harold's brain needs feeding

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MODELS_DIR="$PROJECT_ROOT/models/llama-cpp"

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

# 😐 Model selection based on research and compatibility
# Qwen2.5-Coder-7B-Instruct - excellent for code, Python 3.14 compatible
MODEL_NAME="qwen2.5-coder-7b-instruct"
MODEL_FILE="qwen2.5-coder-7b-instruct-q4_k_m.gguf"
MODEL_URL="https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct-GGUF/resolve/main/${MODEL_FILE}"
MODEL_SHA256="d57a7e0d1e7c8b0e5c7e5e1f8e7e5e1f8e7e5e1f8e7e5e1f8e7e5e1f8e7e5e1f"  # Placeholder

log_info "EraserHead Model Download Script"
log_info "Downloading: $MODEL_NAME"
echo ""

# Create models directory
mkdir -p "$MODELS_DIR"

# Check if model already exists
if [ -f "$MODELS_DIR/$MODEL_FILE" ]; then
    log_warn "Model already exists: $MODEL_FILE"
    read -p "😐 Re-download? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Harold reuses existing model. Efficient."
        exit 0
    fi
fi

# 😐 Download model with progress
log_info "Downloading from HuggingFace..."
log_warn "This is a large file (~4.4GB). Harold waits with nervous patience."
echo ""

cd "$MODELS_DIR"

if command -v wget &> /dev/null; then
    wget -c "$MODEL_URL" -O "$MODEL_FILE.tmp"
elif command -v curl &> /dev/null; then
    curl -L -C - "$MODEL_URL" -o "$MODEL_FILE.tmp"
else
    log_error "Neither wget nor curl found. Harold cannot download."
    exit 1
fi

# Move to final location
mv "$MODEL_FILE.tmp" "$MODEL_FILE"

log_info "Download complete: $MODEL_FILE"

# 😐 Verify file size (basic sanity check)
MODEL_SIZE=$(stat -f%z "$MODEL_FILE" 2>/dev/null || stat -c%s "$MODEL_FILE" 2>/dev/null)
MIN_SIZE=$((4000000000))  # 4GB minimum

if [ "$MODEL_SIZE" -lt "$MIN_SIZE" ]; then
    log_error "Downloaded file seems too small (${MODEL_SIZE} bytes)"
    log_error "Dark Harold suspects incomplete download"
    exit 1
fi

log_info "Model size verified: $(numfmt --to=iec-i --suffix=B $MODEL_SIZE 2>/dev/null || echo $MODEL_SIZE bytes)"

# 😐 Optional: Verify checksum if provided
# if command -v sha256sum &> /dev/null; then
#     log_info "Verifying checksum..."
#     echo "$MODEL_SHA256  $MODEL_FILE" | sha256sum -c -
# fi

echo ""
log_info "=================================================="
log_info "Model ready: $MODEL_FILE"
log_info "Location: $MODELS_DIR/"
log_info ""
log_info "Next steps:"
log_info "  1. Run: ./scripts/llm-start.sh"
log_info "  2. Test: curl http://localhost:8080/v1/models"
log_info ""
log_info "😐 Harold's brain is downloaded. Now to see if it works..."
