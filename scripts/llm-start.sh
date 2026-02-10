#!/usr/bin/env bash
# 😐 Smart LLM starter - detects hardware and routes appropriately
# Harold adapts to available resources

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}😐${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}😐${NC} $1"
}

echo "😐 Harold's Hardware Detection"
echo "=================================================="
echo ""

# 😐 Check for NVIDIA GPU
if command -v nvidia-smi &> /dev/null; then
    if nvidia-smi &> /dev/null; then
        GPU_AVAILABLE=true
        GPU_INFO=$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits | head -n1)
        log_info "GPU detected: $GPU_INFO"
    else
        GPU_AVAILABLE=false
        log_warn "nvidia-smi found but no GPU detected"
    fi
else
    GPU_AVAILABLE=false
    log_info "No NVIDIA GPU detected (nvidia-smi not found)"
fi

echo ""

# 😐 Check available RAM
if command -v free &> /dev/null; then
    TOTAL_RAM=$(free -g | awk '/^Mem:/{print $2}')
    log_info "System RAM: ${TOTAL_RAM}GB"
    
    if [ "$TOTAL_RAM" -lt 16 ]; then
        log_warn "RAM below recommended 16GB. Harold may struggle."
    fi
fi

# 😐 Check CPU threads
if command -v nproc &> /dev/null; then
    N_THREADS=$(nproc)
    log_info "CPU threads: $N_THREADS"
fi

echo ""
echo "=================================================="
echo ""

# 😐 Route to appropriate backend
if [ "$GPU_AVAILABLE" = true ]; then
    log_info "Routing to GPU path (vLLM)"
    log_info "Harold's brain runs on silicon acceleration"
    echo ""
    exec "$SCRIPT_DIR/llm-start-gpu.sh"
else
    log_info "Routing to CPU path (llama.cpp)"
    log_info "Harold's brain runs on modest hardware"
    log_warn "Performance will be slower. But privacy is maintained locally."
    echo ""
    exec "$SCRIPT_DIR/llm-start-cpu.sh"
fi
