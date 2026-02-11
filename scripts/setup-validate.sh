#!/bin/bash
# 😐 EraserHead Setup Validation Script
# Validates tinyclaw integration and development environment

set -e

PROJECT_ROOT="/home/kang/Documents/projects/radkit/eraserhead"
TINYCLAW_CONFIG="$HOME/.config/tinyclaw/config.json5"
TINYCLAW_MEMORY="$HOME/.config/tinyclaw/memory/memory.db"

echo "😐 EraserHead + tinyclaw Setup Validation"
echo "=========================================="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

success_count=0
warning_count=0
error_count=0

check_success() {
    echo -e "${GREEN}✓${NC} $1"
    ((success_count++))
}

check_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((warning_count++))
}

check_error() {
    echo -e "${RED}✗${NC} $1"
    ((error_count++))
}

# 1. Check Node.js and npm
echo "📦 Checking Node.js..."
if command -v node >/dev/null 2>&1; then
    NODE_VERSION=$(node --version)
    check_success "Node.js installed: $NODE_VERSION"
else
    check_error "Node.js not installed"
fi

if command -v npm >/dev/null 2>&1; then
    NPM_VERSION=$(npm --version)
    check_success "npm installed: $NPM_VERSION"
else
    check_error "npm not installed"
fi

# 2. Check tinyclaw installation
echo ""
echo "🔧 Checking tinyclaw..."
if command -v tinyclaw >/dev/null 2>&1; then
    TINYCLAW_VERSION=$(tinyclaw --version 2>/dev/null || echo "unknown")
    check_success "tinyclaw installed: $TINYCLAW_VERSION"
else
    check_error "tinyclaw not installed (run: npm install -g @mrcloudchase/tinyclaw)"
fi

# 3. Check tinyclaw configuration
echo ""
echo "⚙️  Checking configuration..."
if [ -f "$TINYCLAW_CONFIG" ]; then
    check_success "tinyclaw config exists: $TINYCLAW_CONFIG"
    
    # Check if it's valid JSON5
    if command -v node >/dev/null 2>&1; then
        if node -e "require('$TINYCLAW_CONFIG')" 2>/dev/null; then
            check_success "Config file is valid"
        else
            check_warning "Config file may have syntax issues"
        fi
    fi
else
    check_error "tinyclaw config missing (expected at: $TINYCLAW_CONFIG)"
fi

# 4. Check memory database
echo ""
echo "🧠 Checking memory system..."
if [ -f "$TINYCLAW_MEMORY" ]; then
    MEMORY_SIZE=$(du -h "$TINYCLAW_MEMORY" | cut -f1)
    check_success "Memory database exists: $MEMORY_SIZE"
else
    check_warning "Memory database not initialized (run: ./scripts/sync-memory.sh)"
fi

# 5. Check API keys
echo ""
echo "🔑 Checking API keys..."
if [ -n "$ANTHROPIC_API_KEY" ]; then
    check_success "ANTHROPIC_API_KEY set (for Opus 4.6 security reviews)"
else
    check_warning "ANTHROPIC_API_KEY not set (needed for harold-security)"
fi

# 6. Check local models
echo ""
echo "🤖 Checking local models..."
MODEL_DIR="$PROJECT_ROOT/models/llama-cpp"
if [ -d "$MODEL_DIR" ]; then
    MODEL_COUNT=$(ls -1 "$MODEL_DIR"/*.gguf 2>/dev/null | wc -l)
    if [ "$MODEL_COUNT" -gt 0 ]; then
        check_success "Found $MODEL_COUNT model(s) in $MODEL_DIR"
        ls -lh "$MODEL_DIR"/*.gguf | awk '{print "  - " $9 " (" $5 ")"}'
    else
        check_warning "No models found in $MODEL_DIR"
    fi
else
    check_error "Model directory missing: $MODEL_DIR"
fi

# 7. Check inference server
echo ""
echo "🚀 Checking inference server..."
if curl -s http://localhost:8080/health >/dev/null 2>&1; then
    check_success "llama.cpp server responsive (port 8080)"
elif curl -s http://localhost:8000/health >/dev/null 2>&1; then
    check_success "vLLM server responsive (port 8000)"
else
    check_warning "No inference server running (start with: llm-start)"
fi

# 8. Check bash aliases
echo ""
echo "🔗 Checking bash aliases..."
if declare -f tc >/dev/null 2>&1 || alias tc >/dev/null 2>&1; then
    check_success "Aliases loaded (tc command available)"
else
    check_warning "Aliases not loaded (source ~/.bash_aliases or the project .bash_aliases_eraserhead)"
fi

# 9. Check system resources
echo ""
echo "💾 Checking system resources..."
TOTAL_RAM=$(free -h | awk '/^Mem:/ {print $2}')
AVAIL_RAM=$(free -h | awk '/^Mem:/ {print $7}')
CPU_CORES=$(nproc)
LOAD_AVG=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | tr -d ',')

check_success "Total RAM: $TOTAL_RAM"
check_success "Available RAM: $AVAIL_RAM"
check_success "CPU cores: $CPU_CORES"
echo "  Load average: $LOAD_AVG"

# Calculate available RAM in GB (rough)
AVAIL_RAM_NUM=$(free -g | awk '/^Mem:/ {print $7}')
if [ "$AVAIL_RAM_NUM" -lt 2 ]; then
    check_warning "Low available RAM (<2GB) - may struggle with larger models"
else
    check_success "Sufficient RAM for 1.5b model"
fi

# 10. Test tinyclaw memory search
echo ""
echo "🔍 Testing memory search..."
if command -v tinyclaw >/dev/null 2>&1 && [ -f "$TINYCLAW_MEMORY" ]; then
    if timeout 10s tinyclaw memory search "test" >/dev/null 2>&1; then
        check_success "Memory search functional"
    else
        check_warning "Memory search timed out or failed"
    fi
else
    check_warning "Cannot test memory search (tinyclaw or database missing)"
fi

# 11. Check quality scripts
echo ""
echo "🛡️  Checking quality scripts..."
SCRIPTS=("format.sh" "lint.sh" "test.sh" "security-scan.sh" "quality-check.sh" "pre-commit.sh")
for script in "${SCRIPTS[@]}"; do
    if [ -x "$PROJECT_ROOT/scripts/$script" ]; then
        check_success "scripts/$script is executable"
    else
        check_warning "scripts/$script not executable (run: chmod +x scripts/$script)"
    fi
done

# Summary
echo ""
echo "=========================================="
echo "📊 Validation Summary"
echo "=========================================="
echo -e "${GREEN}✓ Success: $success_count${NC}"
echo -e "${YELLOW}⚠ Warnings: $warning_count${NC}"
echo -e "${RED}✗ Errors: $error_count${NC}"
echo ""

if [ $error_count -eq 0 ] && [ $warning_count -eq 0 ]; then
    echo "🎉 Perfect! All checks passed. Harold is ready to ship code. 😐"
    exit 0
elif [ $error_count -eq 0 ]; then
    echo "😐 Setup is functional with some warnings. Can proceed with caution."
    echo ""
    echo "🌑 Dark Harold's note: Warnings mean potential issues."
    echo "   Fix them before relying on affected features."
    exit 0
else
    echo "😐 Setup has errors. Fix them before proceeding:"
    echo ""
    if ! command -v tinyclaw >/dev/null 2>&1; then
        echo "  1. Install tinyclaw: npm install -g @mrcloudchase/tinyclaw"
    fi
    if [ ! -f "$TINYCLAW_CONFIG" ]; then
        echo "  2. Copy config: cp tinyclaw-config.example.json5 ~/.config/tinyclaw/config.json5"
    fi
    if [ ! -f "$TINYCLAW_MEMORY" ]; then
        echo "  3. Initialize memory: ./scripts/sync-memory.sh"
    fi
    echo ""
    exit 1
fi
