#!/usr/bin/env bash
# 😐 Start vLLM inference server (GPU accelerated)
# Harold's brain runs faster with silicon assistance

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

# 😐 Check if podman is installed
if ! command -v podman &> /dev/null; then
    log_error "Podman not found. Harold demands container isolation."
    echo "Install with: sudo apt install podman"
    exit 1
fi

# 😐 Check if podman-compose is available
if ! command -v podman-compose &> /dev/null; then
    log_warn "podman-compose not found. Using podman directly."
    USE_COMPOSE=false
else
    USE_COMPOSE=true
fi

# 😐 Model for vLLM (same as CPU but full precision)
MODEL_NAME="Qwen/Qwen2.5-Coder-7B-Instruct"
MODEL_TAG="qwen2.5-coder-7b"

log_info "Starting vLLM server (GPU mode)"
log_info "Model: $MODEL_NAME"
log_info "Endpoint: http://127.0.0.1:8000/v1"
echo ""
log_warn "Dark Harold notes: This requires NVIDIA GPU with CUDA support."
log_warn "GPU memory: ~8GB minimum for 7B model"
echo ""

cd "$PROJECT_ROOT"

if [ "$USE_COMPOSE" = true ]; then
    log_info "Using podman-compose..."
    
    # Set model in environment
    export VLLM_MODEL="$MODEL_NAME"
    
    podman-compose up -d harold-brain-vllm
    
    log_info "Container starting. Harold's GPU brain initializing..."
    log_info "Check status: podman-compose logs -f harold-brain-vllm"
else
    log_info "Using podman directly..."
    
    # Check if container already running
    if podman ps --filter "name=harold-brain-vllm" --format "{{.Names}}" | grep -q "harold-brain-vllm"; then
        log_warn "Container already running"
        read -p "😐 Restart? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            podman stop harold-brain-vllm
            podman rm harold-brain-vllm
        else
            log_info "Harold reuses running container"
            exit 0
        fi
    fi
    
    # Run vLLM container
    podman run -d \
        --name harold-brain-vllm \
        --device nvidia.com/gpu=all \
        --security-opt=label=disable \
        --ipc=host \
        -p 8000:8000 \
        -e HF_TOKEN="${HF_TOKEN:-}" \
        -v "$PROJECT_ROOT/models:/models:ro" \
        vllm/vllm-openai:latest \
        --model "$MODEL_NAME" \
        --host 0.0.0.0 \
        --port 8000 \
        --gpu-memory-utilization 0.9 \
        --max-model-len 8192 \
        --served-model-name "$MODEL_TAG"
    
    log_info "Container started: harold-brain-vllm"
    log_info "Check logs: podman logs -f harold-brain-vllm"
fi

echo ""
log_info "=================================================="
log_info "Waiting for model to load..."
sleep 5

# 😐 Test endpoint
if curl -s http://127.0.0.1:8000/v1/models > /dev/null 2>&1; then
    log_info "✓ vLLM server responding"
    log_info "Harold's GPU brain is operational"
else
    log_warn "Server not responding yet (model may still be loading)"
    log_info "Monitor logs for progress"
fi

echo ""
log_info "Test with: curl http://127.0.0.1:8000/v1/models"
log_info "Stop with: podman stop harold-brain-vllm"
