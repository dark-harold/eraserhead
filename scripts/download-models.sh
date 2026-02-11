#!/usr/bin/env bash
# 😐 Download Qwen2.3-coder models for local inference
# Harold's privacy-first brain requires feeding

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MODELS_DIR="$PROJECT_ROOT/models/llama-cpp"

# Colors for Harold's emotional state
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

log_detail() {
    echo -e "${BLUE}  ├─${NC} $1"
}

# 😐 Qwen2.3-Coder model definitions
# All models: 32K context, instruct-tuned, Python 3.14 compatible
declare -A MODELS=(
    ["0.5b"]="Qwen/Qwen2.5-Coder-0.5B-Instruct-GGUF:qwen2.5-coder-0.5b-instruct-q4_k_m.gguf:0.4:Simple refactoring, formatting"
    ["1.5b"]="Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF:qwen2.5-coder-1.5b-instruct-q4_k_m.gguf:1.1:Testing, docs, moderate code"
    ["3b"]="Qwen/Qwen2.5-Coder-3B-Instruct-GGUF:qwen2.5-coder-3b-instruct-q4_k_m.gguf:2.2:Implementation, refactoring"
    ["7b"]="Qwen/Qwen2.5-Coder-7B-Instruct-GGUF:qwen2.5-coder-7b-instruct-q4_k_m.gguf:4.9:Complex arch, security analysis"
)

show_usage() {
    cat << EOF
${GREEN}😐 EraserHead Model Download Script${NC}

Usage: $0 [OPTIONS] [MODEL_SIZE]

MODEL_SIZE: 0.5b, 1.5b, 3b, 7b, or 'all' (default: 7b)

Options:
  -h, --help     Show this help message
  -f, --force    Re-download even if file exists
  -l, --list     List available models and exit

Examples:
  $0              # Download 7b model (recommended)
  $0 3b           # Download 3b model
  $0 all          # Download all models (Harold waits nervously)
  $0 -f 7b        # Force re-download 7b

${YELLOW}Dark Harold's Reminder:${NC} Larger models = better quality, slower inference
EOF
    exit 0
}

list_models() {
    log_info "Available Qwen2.3-Coder Models"
    echo ""
    printf "%-8s %-8s %-50s\n" "SIZE" "DISK" "USE CASE"
    printf "%-8s %-8s %-50s\n" "----" "----" "--------"
    for size in 0.5b 1.5b 3b 7b; do
        IFS=':' read -r repo file disk_gb use_case <<< "${MODELS[$size]}"
        printf "%-8s %-8s %-50s\n" "$size" "${disk_gb}GB" "$use_case"
    done
    echo ""
    log_detail "All models: Q4_K_M quantization, 32K context window"
    log_detail "HuggingFace repo: Qwen/Qwen2.5-Coder-*-Instruct-GGUF"
    exit 0
}

download_model() {
    local size=$1
    local force_download=$2
    
    if [[ ! -v MODELS[$size] ]]; then
        log_error "Unknown model size: $size (valid: 0.5b, 1.5b, 3b, 7b)"
        return 1
    fi
    
    IFS=':' read -r repo file disk_gb use_case <<< "${MODELS[$size]}"
    local url="https://huggingface.co/${repo}/resolve/main/${file}"
    local output_path="$MODELS_DIR/$file"
    
    log_info "Model: Qwen2.3-Coder-${size} (${disk_gb}GB)"
    log_detail "Use case: $use_case"
    log_detail "Quantization: Q4_K_M"
    log_detail "Context: 32K tokens"
    echo ""
    
    # Check if model exists
    if [ -f "$output_path" ] && [ "$force_download" = false ]; then
        log_warn "Model already exists: $file"
        read -p "😐 Re-download? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Harold reuses existing model. Pragmatic."
            return 0
        fi
    fi
    
    # Create models directory
    mkdir -p "$MODELS_DIR"
    
    # Download with progress
    log_info "Downloading from HuggingFace..."
    log_warn "File size: ~${disk_gb}GB. Harold waits with nervous optimism."
    echo ""
    
    cd "$MODELS_DIR"
    
    local temp_file="${file}.tmp"
    local download_success=false
    
    # Try wget first (better progress), fallback to curl
    if command -v wget &> /dev/null; then
        if wget -c "$url" -O "$temp_file"; then
            download_success=true
        fi
    elif command -v curl &> /dev/null; then
        if curl -L -C - --progress-bar "$url" -o "$temp_file"; then
            download_success=true
        fi
    else
        log_error "Neither wget nor curl found. Harold cannot download."
        return 1
    fi
    
    if [ "$download_success" = false ]; then
        log_error "Download failed. Dark Harold suspected this."
        rm -f "$temp_file"
        return 1
    fi
    
    # Move to final location
    mv "$temp_file" "$file"
    
    # Verify file size (basic sanity check)
    local expected_bytes=$(echo "$disk_gb * 1000000000" | bc 2>/dev/null || echo "1000000000")
    local actual_bytes=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null)
    local min_bytes=$(echo "$expected_bytes * 0.8" | bc 2>/dev/null || echo "800000000")
    
    if [ "$actual_bytes" -lt "$min_bytes" ]; then
        log_error "Downloaded file seems too small (${actual_bytes} bytes)"
        log_error "Expected: ~${expected_bytes} bytes"
        log_error "Dark Harold suspects incomplete download or corrupted file"
        return 1
    fi
    
    # Display human-readable size
    local size_human=""
    if command -v numfmt &> /dev/null; then
        size_human=$(numfmt --to=iec-i --suffix=B "$actual_bytes")
    else
        size_human="${actual_bytes} bytes"
    fi
    
    log_info "Download complete: $file ($size_human)"
    echo ""
    
    return 0
}

main() {
    local force_download=false
    local model_size="7b"
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                ;;
            -l|--list)
                list_models
                ;;
            -f|--force)
                force_download=true
                shift
                ;;
            0.5b|1.5b|3b|7b|all)
                model_size=$1
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                ;;
        esac
    done
    
    log_info "EraserHead Model Download Script"
    echo ""
    
    # Download models
    if [ "$model_size" = "all" ]; then
        log_warn "Downloading ALL models. Total: ~8.6GB. Harold's patience will be tested."
        echo ""
        for size in 0.5b 1.5b 3b 7b; do
            download_model "$size" "$force_download"
            echo ""
        done
    else
        download_model "$model_size" "$force_download"
    fi
    
    # Summary
    log_info "=================================================="
    log_info "Models ready in: $MODELS_DIR/"
    echo ""
    log_info "Next steps:"
    log_detail "For GPU inference (NVIDIA): ./scripts/llm-start-gpu.sh"
    log_detail "For CPU inference: ./scripts/llm-start-cpu.sh"
    log_detail "Auto-detect: ./scripts/llm-start.sh"
    log_detail "Test endpoint: curl http://localhost:8080/v1/models"
    echo ""
    log_info "Harold's brain is now local, private, and ready to ship code 😐"
}

main "$@"
