#!/usr/bin/env bash
# 😐 Model Evaluation Script
# Testing local models for development tasks

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
RESULTS_DIR="$PROJECT_ROOT/model-evaluation-results"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}😐${NC} $1"
}

log_metric() {
    echo -e "${BLUE}  📊${NC} $1"
}

# Test task: Implement a simple validation function with Harold persona
TEST_PROMPT='You are implementing a Python function for the EraserHead project with Harold persona (😐 for normal code, 🌑 for security concerns).

Task: Implement a function `validate_layer_count(layers: int, min_layers: int = 3, max_layers: int = 7) -> bool` that:
1. Returns True if layers is between min_layers and max_layers (inclusive)
2. Raises ValueError with message if layers is invalid
3. Has Google-style docstring with Harold comments
4. Includes type hints

Write only the implementation code, no tests.'

mkdir -p "$RESULTS_DIR"

evaluate_model() {
    local model_size=$1
    local model_file=$2
    local result_file="$RESULTS_DIR/${model_size}-evaluation.json"
    
    log_info "Evaluating $model_size model..."
    
    # Start server in background
    log_info "Starting llama-server..."
    local server_pid
    llama-server \
        -m "$PROJECT_ROOT/models/llama-cpp/$model_file" \
        -c 4096 \
        -n 512 \
        --port 8080 \
        --threads $(nproc) \
        > "$RESULTS_DIR/${model_size}-server.log" 2>&1 &
    server_pid=$!
    
    # Wait for server to be ready
    log_info "Waiting for server to initialize..."
    sleep 5
    for i in {1..30}; do
        if curl -s http://localhost:8080/health > /dev/null 2>&1; then
            log_info "Server ready!"
            break
        fi
        sleep 1
    done
    
    # Capture baseline metrics
    local start_time=$(date +%s)
    local start_mem=$(free -m | awk '/^Mem:/{print $3}')
    
    # Send test request
    log_info "Sending test prompt..."
    local response
    response=$(curl -s http://localhost:8080/v1/chat/completions \
        -H "Content-Type: application/json" \
        -d "{
            \"model\": \"qwen2.5-coder\",
            \"messages\": [{\"role\": \"user\", \"content\": $(echo "$TEST_PROMPT" | jq -Rs .)}],
            \"temperature\": 0.1,
            \"max_tokens\": 512
        }")
    
    # Capture end metrics
    local end_time=$(date +%s)
    local end_mem=$(free -m | awk '/^Mem:/{print $3}')
    local duration=$((end_time - start_time))
    local mem_used=$((end_mem - start_mem))
    
    # Parse response
    local generated_text=$(echo "$response" | jq -r '.choices[0].message.content // empty')
    local prompt_tokens=$(echo "$response" | jq -r '.usage.prompt_tokens // 0')
    local completion_tokens=$(echo "$response" | jq -r '.usage.completion_tokens // 0')
    
    # Save full response
    echo "$response" > "$RESULTS_DIR/${model_size}-response.json"
    echo "$generated_text" > "$RESULTS_DIR/${model_size}-generated.py"
    
    # Calculate metrics
    local tokens_per_sec=0
    if [ $duration -gt 0 ]; then
        tokens_per_sec=$(echo "scale=2; $completion_tokens / $duration" | bc)
    fi
    
    # Check quality indicators
    local has_docstring=0
    local has_type_hints=0
    local has_harold_emoji=0
    local has_raises=0
    
    if echo "$generated_text" | grep -q '"""'; then has_docstring=1; fi
    if echo "$generated_text" | grep -q '-> bool'; then has_type_hints=1; fi
    if echo "$generated_text" | grep -qE '😐|🌑'; then has_harold_emoji=1; fi
    if echo "$generated_text" | grep -qi 'raise.*ValueError'; then has_raises=1; fi
    
    local quality_score=$((has_docstring + has_type_hints + has_harold_emoji + has_raises))
    
    # Display metrics
    log_metric "Duration: ${duration}s"
    log_metric "Memory used: ${mem_used}MB"
    log_metric "Prompt tokens: $prompt_tokens"
    log_metric "Completion tokens: $completion_tokens"
    log_metric "Tokens/sec: $tokens_per_sec"
    log_metric "Quality score: $quality_score/4"
    
    # Create summary JSON
    cat > "$result_file" <<EOF
{
  "model_size": "$model_size",
  "model_file": "$model_file",
  "timestamp": "$(date -Iseconds)",
  "performance": {
    "duration_seconds": $duration,
    "memory_used_mb": $mem_used,
    "prompt_tokens": $prompt_tokens,
    "completion_tokens": $completion_tokens,
    "tokens_per_second": $tokens_per_sec
  },
  "quality": {
    "has_docstring": $has_docstring,
    "has_type_hints": $has_type_hints,
    "has_harold_emoji": $has_harold_emoji,
    "has_raises": $has_raises,
    "score": $quality_score
  },
  "generated_code_length": ${#generated_text}
}
EOF
    
    # Stop server
    log_info "Stopping server..."
    kill $server_pid 2>/dev/null || true
    sleep 2
    
    log_info "$model_size evaluation complete!"
    echo ""
}

# Main evaluation
log_info "🧪 Model Evaluation: 0.5b vs 1.5b"
log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check for llama-server
if ! command -v llama-server &> /dev/null; then
    echo "❌ llama-server not found. Please install llama.cpp"
    exit 1
fi

# Evaluate 0.5b
evaluate_model "0.5b" "qwen2.5-coder-0.5b-instruct-q4_k_m.gguf"

# Evaluate 1.5b
evaluate_model "1.5b" "qwen2.5-coder-1.5b-instruct-q4_k_m.gguf"

# Generate comparison report
log_info "📊 Generating comparison report..."

cat > "$RESULTS_DIR/comparison.md" <<'EOF'
# 😐 Local Model Evaluation Results

**Task**: Implement `validate_layer_count()` function with Harold persona

## Test Prompt
```
Implement a function `validate_layer_count(layers: int, min_layers: int = 3, max_layers: int = 7) -> bool` that:
1. Returns True if layers is between min_layers and max_layers (inclusive)
2. Raises ValueError with message if layers is invalid
3. Has Google-style docstring with Harold comments
4. Includes type hints
```

## Results

EOF

# Add performance comparison
cat >> "$RESULTS_DIR/comparison.md" <<EOF
### Performance Comparison

| Metric | 0.5b | 1.5b | Winner |
|--------|------|------|--------|
EOF

# Parse and compare JSON results
if [ -f "$RESULTS_DIR/0.5b-evaluation.json" ] && [ -f "$RESULTS_DIR/1.5b-evaluation.json" ]; then
    dur_05b=$(jq -r '.performance.duration_seconds' "$RESULTS_DIR/0.5b-evaluation.json")
    dur_15b=$(jq -r '.performance.duration_seconds' "$RESULTS_DIR/1.5b-evaluation.json")
    
    mem_05b=$(jq -r '.performance.memory_used_mb' "$RESULTS_DIR/0.5b-evaluation.json")
    mem_15b=$(jq -r '.performance.memory_used_mb' "$RESULTS_DIR/1.5b-evaluation.json")
    
    tps_05b=$(jq -r '.performance.tokens_per_second' "$RESULTS_DIR/0.5b-evaluation.json")
    tps_15b=$(jq -r '.performance.tokens_per_second' "$RESULTS_DIR/1.5b-evaluation.json")
    
    qual_05b=$(jq -r '.quality.score' "$RESULTS_DIR/0.5b-evaluation.json")
    qual_15b=$(jq -r '.quality.score' "$RESULTS_DIR/1.5b-evaluation.json")
    
    # Determine winners
    dur_winner="0.5b"
    [ "$dur_15b" -lt "$dur_05b" ] 2>/dev/null && dur_winner="1.5b" || true
    
    mem_winner="0.5b"
    [ "$mem_15b" -lt "$mem_05b" ] 2>/dev/null && mem_winner="1.5b" || true
    
    tps_winner="0.5b"
    [ $(echo "$tps_15b > $tps_05b" | bc -l) -eq 1 ] 2>/dev/null && tps_winner="1.5b" || true
    
    qual_winner="0.5b"
    [ "$qual_15b" -gt "$qual_05b" ] 2>/dev/null && qual_winner="1.5b" || true
    
    cat >> "$RESULTS_DIR/comparison.md" <<EOFTABLE
| Duration (seconds) | ${dur_05b}s | ${dur_15b}s | ✅ ${dur_winner} |
| Memory Used (MB) | ${mem_05b}MB | ${mem_15b}MB | ✅ ${mem_winner} |
| Tokens/Second | ${tps_05b} | ${tps_15b} | ✅ ${tps_winner} |
| Quality Score | ${qual_05b}/4 | ${qual_15b}/4 | ✅ ${qual_winner} |

### Quality Breakdown

| Feature | 0.5b | 1.5b |
|---------|------|------|
| Docstring | $(jq -r '.quality.has_docstring' "$RESULTS_DIR/0.5b-evaluation.json") | $(jq -r '.quality.has_docstring' "$RESULTS_DIR/1.5b-evaluation.json") |
| Type Hints | $(jq -r '.quality.has_type_hints' "$RESULTS_DIR/0.5b-evaluation.json") | $(jq -r '.quality.has_type_hints' "$RESULTS_DIR/1.5b-evaluation.json") |
| Harold Emoji | $(jq -r '.quality.has_harold_emoji' "$RESULTS_DIR/0.5b-evaluation.json") | $(jq -r '.quality.has_harold_emoji' "$RESULTS_DIR/1.5b-evaluation.json") |
| Raises ValueError | $(jq -r '.quality.has_raises' "$RESULTS_DIR/0.5b-evaluation.json") | $(jq -r '.quality.has_raises' "$RESULTS_DIR/1.5b-evaluation.json") |

### Generated Code

#### 0.5b Model Output
\`\`\`python
$(cat "$RESULTS_DIR/0.5b-generated.py")
\`\`\`

#### 1.5b Model Output
\`\`\`python
$(cat "$RESULTS_DIR/1.5b-generated.py")
\`\`\`

EOFTABLE
fi

cat >> "$RESULTS_DIR/comparison.md" <<'EOF'

## Recommendation

Based on the evaluation:

EOF

log_info "✅ Evaluation complete!"
log_info "Results saved to: $RESULTS_DIR/"
log_info ""
log_info "View comparison report: cat $RESULTS_DIR/comparison.md"
