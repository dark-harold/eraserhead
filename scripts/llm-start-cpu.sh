#!/usr/bin/env bash
# 😐 Start llama.cpp inference server (CPU optimized)
# Harold's brain runs on modest hardware

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MODELS_DIR="$PROJECT_ROOT/models/llama-cpp"
MODEL_FILE="${MODEL_FILE:-qwen2.5-coder-1.5b-instruct-q4_k_m.gguf}"  # 😐 1.5b: Best balance of quality and speed

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

# 😐 Check if model exists
if [ ! -f "$MODELS_DIR/$MODEL_FILE" ]; then
    log_error "Model not found: $MODEL_FILE"
    echo "Run: ./scripts/download-models.sh"
    exit 1
fi

# 😐 Check if llama-cpp-python is installed
if ! python3 -c "import llama_cpp" 2>/dev/null; then
    log_error "llama-cpp-python not installed"
    echo "Harold needs his neural pathways installed."
    echo ""
    echo "Install with:"
    echo "  source .venv/bin/activate"
    echo "  uv pip install 'llama-cpp-python[server]'"
    exit 1
fi

# 😐 CPU optimization settings
N_THREADS=$(nproc)
N_CTX=8192
N_BATCH=512
HOST="127.0.0.1"
PORT=8080

log_info "Starting llama.cpp server (CPU mode)"
log_info "Model: $MODEL_FILE"
log_info "Threads: $N_THREADS"
log_info "Context: $N_CTX tokens"
log_info "Endpoint: http://$HOST:$PORT/v1"
echo ""
log_warn "Dark Harold notes: This will use significant CPU and RAM."
log_warn "Inference will be slower than GPU. But privacy is maintained."
echo ""

# 😐 Start server with llama-cpp-python
log_info "Harold's brain is initializing..."

python3 -m llama_cpp.server \
    --model "$MODELS_DIR/$MODEL_FILE" \
    --host "$HOST" \
    --port "$PORT" \
    --n_ctx "$N_CTX" \
    --n_threads "$N_THREADS" \
    --n_batch "$N_BATCH" \
    --chat_format chatml \
    --interrupt_requests true \
    --verbose false

# 😐 This runs in foreground. Use Ctrl+C to stop.
# For background: add & at end and redirect output to log file
