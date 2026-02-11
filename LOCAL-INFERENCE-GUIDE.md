# 😐 Local Inference Quick Start

**Purpose**: Get Harold's local brain running for privacy-first development  
**Updated**: February 10, 2026  
**Recommended**: **qwen2.5-coder-1.5b** (best balance of quality and Harold persona adherence)

> 📊 **Model Evaluation Completed**: See [MODEL-EVALUATION.md](MODEL-EVALUATION.md) for detailed analysis

---

## Models Available

| Model | Size | Use Case | Context | Speed | Harold Persona |
|-------|------|----------|---------|-------|----------------|
| **qwen2.5-coder-0.5b** | 0.4GB | Simple refactoring, formatting | 32K | ⚡⚡⚡ Very Fast | ⚠️ Weak |
| ⭐ **qwen2.5-coder-1.5b** | 1.1GB | **Default: all tasks** | 32K | ⚡⚡ Fast | ✅ **Strong** |
| **qwen2.5-coder-3b** | 2.2GB | Complex implementation | 32K | ⚡ Good | ✅ Strong |
| **qwen2.5-coder-7b** | 4.9GB | Architecture, security review | 32K | 🐌 Slower | ✅ Strong |

All models: Q4_K_M quantization, instruct-tuned, Python 3.13+ compatible

**Why 1.5b?** Evaluation showed perfect 5/5 quality score including Harold emoji (😐) integration,  
2x faster than 7b, only 2GB RAM footprint. See full analysis in MODEL-EVALUATION.md.

---

## Quick Start

### 1. Download Models

```bash
# Download recommended model (1.5b) - ⭐ Best for development
./scripts/download-models.sh 1.5b

# Download alternative models
./scripts/download-models.sh 0.5b  # Faster, less Harold awareness
./scripts/download-models.sh 3b    # More capable, slower
./scripts/download-models.sh 7b    # For complex architecture/security

# Download all models (Harold waits nervously for 8.6GB)
./scripts/download-models.sh all

# List available models
./scripts/download-models.sh --list
```

### 2. Start Inference Server

#### Auto-detect (Recommended)
```bash
./scripts/llm-start.sh
# Auto-detects: GPU → vLLM, CPU → llama.cpp
```

#### GPU (NVIDIA/AMD/Intel)
```bash
./scripts/llm-start-gpu.sh
# Uses vLLM for fast inference
# Requires: CUDA/ROCm/Level Zero
```

#### CPU (Fallback)
```bash
./scripts/llm-start-cpu.sh
# Uses llama.cpp for CPU inference
# Slower but universal
```

### 3. Test Endpoint

```bash
# Check server health
curl http://localhost:8080/v1/models

# Expected response:
{
  "object": "list",
  "data": [
    {
      "id": "qwen2.5-coder-7b-instruct",
      "object": "model",
      "owned_by": "local"
    }
  ]
}
```

### 4. Configure tinyclaw

```bash
# Copy example config
cp tinyclaw-config.example.json5 ~/.config/tinyclaw/config.json5

# Edit if needed (defaults are good)
# Local-first is already configured!
```

---

## Model Selection Strategy

### By Task Complexity

**Simple** (format, lint, typos):
```yaml
model: qwen2.5-coder-0.5b-instruct
provider: llamacpp  # Fast, lightweight
```

**Moderate** (refactor, tests, docs):
```yaml
model: qwen2.5-coder-3b-instruct
provider: llamacpp  # Good balance
```

**Complex** (architecture, implementation):
```yaml
model: qwen2.5-coder-7b-instruct
provider: vllm  # GPU if available, else llamacpp
```

**Security/Crypto** (ALWAYS):
```yaml
model: claude-opus-4-6
provider: anthropic  # No compromise on security
```

### By Hardware

**High-end GPU** (NVIDIA RTX 4090, A100, etc.):
- Use: `qwen2.5-coder-7b-instruct` with vLLM
- Fast inference, maximum capability
- harold-implementer: "Ship code at GPU speed 🚀"

**Mid-range GPU** (NVIDIA RTX 3060, etc.):
- Use: `qwen2.5-coder-3b-instruct` with vLLM
- Good balance of speed and capability
- harold-planner: "Pragmatic choice for most work"

**CPU Only** (No GPU):
- Use: `qwen2.5-coder-1.5b-instruct` with llama.cpp
- Slower but functional
- harold-implementer: "Harold codes on a potato if necessary"

**Low Resources** (Old laptop):
- Use: `qwen2.5-coder-0.5b-instruct` with llama.cpp
- Basic tasks only
- Fallback to cloud for complex work

---

## Performance Tuning

### vLLM (GPU)

#### Environment Variables
```bash
# Use GPU 0
export CUDA_VISIBLE_DEVICES=0

# Tensor parallelism (multi-GPU)
export VLLM_TENSOR_PARALLEL_SIZE=2

# Batch size (higher = faster but more VRAM)
export VLLM_MAX_NUM_BATCHED_TOKENS=2048
```

#### Start with custom settings
```bash
vllm serve models/llama-cpp/qwen2.5-coder-7b-instruct-q4_k_m.gguf \
  --host 127.0.0.1 \
  --port 8000 \
  --max-model-len 32768 \
  --gpu-memory-utilization 0.9
```

### llama.cpp (CPU)

#### Environment Variables
```bash
# Number of threads (set to CPU cores - 1)
export LLAMA_CPP_N_THREADS=8

# Batch size (higher = faster but more RAM)
export LLAMA_CPP_N_BATCH=512
```

#### Start with custom settings
```bash
python -m llama_cpp.server \
  --model models/llama-cpp/qwen2.5-coder-3b-instruct-q4_k_m.gguf \
  --host 127.0.0.1 \
  --port 8080 \
  --n_ctx 32768 \
  --n_threads 8
```

---

## Troubleshooting

### Model server won't start

**Symptom**: `Connection refused` or port already in use

**Solutions**:
```bash
# Check if port is in use
lsof -i :8080  # llama.cpp default
lsof -i :8000  # vLLM default

# Kill existing server
pkill -f "llama_cpp.server"
pkill -f "vllm"

# Use different port
python -m llama_cpp.server --port 8081 ...
```

### Out of memory (GPU)

**Symptom**: `CUDA out of memory` or `RuntimeError: memory`

**Solutions**:
1. Use smaller model (7b → 3b → 1.5b)
2. Reduce context window: `--max-model-len 16384`
3. Reduce GPU utilization: `--gpu-memory-utilization 0.7`
4. Enable CPU offload (vLLM): `--device cpu`

### Out of memory (CPU/RAM)

**Symptom**: System hangs, swap thrashing

**Solutions**:
1. Use smaller model
2. Reduce threads: `--n_threads 4`
3. Reduce batch size: `--n_batch 256`
4. Close other applications

### Slow inference

**Symptom**: Takes forever to generate code

**Expected Behavior**:
- **GPU (vLLM)**: 20-50 tokens/sec
- **CPU (llama.cpp)**: 2-10 tokens/sec

**Solutions**:
1. Use GPU if available (vLLM)
2. Use smaller model (faster but less capable)
3. Reduce context length (less to process)
4. Fallback to cloud for complex tasks

### tinyclaw won't connect

**Symptom**: `Connection refused` or timeout

**Checks**:
```bash
# Is server running?
curl http://localhost:8080/v1/models

# Check tinyclaw config
cat ~/.config/tinyclaw/config.json5 | grep baseUrl

# Verify URL matches server
# llamacpp: http://127.0.0.1:8080/v1
# vllm: http://127.0.0.1:8000/v1
```

---

## Harold's Pro Tips

### Tip 1: Keep models running
```bash
# Start in background with screen/tmux
screen -S llm
./scripts/llm-start.sh
# Ctrl+A D to detach
```

### Tip 2: Monitor GPU usage
```bash
# NVIDIA
watch -n1 nvidia-smi

# AMD
watch -n1 rocm-smi

# Intel
watch -n1 xpu-smi
```

### Tip 3: Switch models on-the-fly
```bash
# Stop current server
pkill -f "llama_cpp.server"

# Start with different model
python -m llama_cpp.server \
  --model models/llama-cpp/qwen2.5-coder-3b-instruct-q4_k_m.gguf \
  ...
```

### Tip 4: Test model quality
```bash
# Simple prompt test
curl http://localhost:8080/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5-coder-7b-instruct",
    "prompt": "Write a Python function to check if a number is prime:",
    "max_tokens": 200,
    "temperature": 0.7
  }'
```

---

## Cost Comparison

### Local Inference (Harold's Privacy Mode)

| Model | Cost per 1M tokens | Notes |
|-------|-------------------|-------|
| **All local models** | $0.00 | Only electricity |

**Electricity cost**: ~$0.001 per hour (GPU) / ~$0.0001 per hour (CPU)  
**Privacy**: ✅ Complete (nothing leaves your machine)

### Cloud Fallback (Emergency Mode)

| Model | Cost per 1M tokens | Notes |
|-------|-------------------|-------|
| **Haiku** | $0.25 | Simple tasks |
| **Sonnet** | $3.00 | Moderate complexity |
| **Opus 4.6** | $15.00 | Security reviews ONLY |

**Privacy**: ⚠️ Code sent to Anthropic

### Harold's Strategy

- **90% local**: Use local models for most work
- **10% cloud**: Fall back to cloud for:
  - Security reviews (harold-security demands Opus)
  - Extremely complex architecture decisions
  - When local models fail repeatedly

**Monthly cost target**: <$50 (mostly Opus for security)

---

## Next Steps

1. **Start inference server**: `./scripts/llm-start.sh`
2. **Configure tinyclaw**: Already done! (local-first by default)
3. **Start coding**: Harold's brain is ready to ship code 😐
4. **Monitor usage**: Track local vs. cloud model usage
5. **Tune as needed**: Adjust model selection based on task performance

---

## Harold's Final Wisdom

*"Local inference is slower but private. Cloud inference is fast but leaky. Harold chooses privacy for 90% of work, speed for the critical 10%."* 😐

*"Dark Harold reminds you: Every cloud API call is a potential training data leak. Keep crypto and security work local."* 🌑

*"Start with the 3b model. It's the sweet spot of speed and capability. Upgrade to 7b when you need it."* — harold-implementer

**😐 Harold's brain is local. Harold's code stays private. Harold ships with confidence.**
