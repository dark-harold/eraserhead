# 😐 tinyclaw Integration Setup Guide for EraserHead

> **Status**: Prepared for installation  
> **Priority**: Recommended for multi-agent workflow automation  
> **Alternative**: Direct implementation without tinyclaw (see below)

## Overview

tinyclaw provides multi-agent coordination, shared memory (RAG), and intelligent model routing for EraserHead development. It enables the 6 specialized Harold agents to work together efficiently while maintaining local-first privacy.

**Key Benefits**:
- **Shared Memory**: SQLite + FTS5 + sqlite-vec RAG system
- **Model Routing**: Auto-select best model (CPU → GPU → Cloud fallback)
- **Agent Coordination**: Route tasks to specialized agents
- **Cost Optimization**: 90% local, <$50/month cloud

---

## 🚀 Installation

### Prerequisites

```bash
# Check if Node.js is installed
node --version  # Need >= 18.0.0, recommend >= 22.12.0
npm --version   # Need >= 8.0.0

# If not installed (Ubuntu/Debian)
sudo apt update && sudo apt install -y nodejs npm

# Or use nvm for latest version
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
source ~/.bashrc
nvm install 22
nvm use 22
```

### Install tinyclaw Globally

```bash
# Install from npm
npm install -g @mrcloudchase/tinyclaw

# Verify installation
tinyclaw --version
which tinyclaw
```

---

## ⚙️ Configuration

### 1. Create Config Directory

```bash
mkdir -p ~/.config/tinyclaw/memory
```

### 2. Copy Configuration for 1.5b Model

We have a customized config optimized for CPU inference with 1.5b model:

```bash
# Copy from project directory
cp /home/kang/Documents/projects/radkit/eraserhead/tinyclaw-config-1.5b.json5 \
   ~/.config/tinyclaw/config.json5

# Or use the standard config as a base
cp /home/kang/Documents/projects/radkit/eraserhead/tinyclaw-config.example.json5 \
   ~/.config/tinyclaw/config.json5
```

**Configuration Highlights** (1.5b optimized):
- Primary model: `qwen2.5-coder-1.5b-instruct` via llama.cpp (CPU)
- Fallbacks: 3b (local) → Sonnet (cloud) → Opus (security only)
- harold-security: **ALWAYS** uses Opus 4.6 (no compromise)
- Local-first: 90% target, privacy-preserving

###3. Set API Key (for Cloud Fallback)

```bash
# Add to ~/.bashrc or ~/.bash_profile
echo 'export ANTHROPIC_API_KEY="your-key-here"' >> ~/.bashrc
source ~/.bashrc

# Verify
echo $ANTHROPIC_API_KEY
```

**🌑 Dark Harold's Note**: The API key is required for harold-security crypto reviews (Opus 4.6). Without it, security reviews will fail. This is intentional.

---

## 🧠 Memory Initialization

### 1. Start Local Inference Server

```bash
cd /home/kang/Documents/projects/radkit/eraserhead

# Auto-detect GPU/CPU
./scripts/llm-start.sh

# Or force CPU (for 1.5b model)
./scripts/llm-start-cpu.sh
```

### 2. Sync Project Specs to Memory

```bash
# From project directory
./scripts/sync-memory.sh

# Manually check what will be synced
cat specs/001-anemochory-protocol/spec.md
cat .specify/memory/constitution.md
```

This indexes:
- Constitution (.specify/memory/constitution.md)
- All spec files (specs/**/spec.md)
- Project README and development plan
- Agent configurations

### 3. Verify Memory Database

```bash
# Check database exists
ls -lh ~/.config/tinyclaw/memory/memory.db

# Test search
tinyclaw memory search "anemochory protocol"
tinyclaw memory search "harold persona"
tinyclaw memory search "security principles"
```

---

## 🔗 Bash Aliases Setup

### Add Aliases to Shell

```bash
# Check if ~/.bash_aliases exists and is sourced
grep -q ".bash_aliases" ~/.bashrc || echo '
# Source bash aliases if file exists
if [ -f ~/.bash_aliases ]; then
    . ~/.bash_aliases
fi' >> ~/.bashrc

# Create aliases file if it doesn't exist
touch ~/.bash_aliases

# Append EraserHead aliases
cat /home/kang/Documents/projects/radkit/eraserhead/.bash_aliases_eraserhead >> ~/.bash_aliases

# OR source directly from project
echo '
# EraserHead aliases
source /home/kang/Documents/projects/radkit/eraserhead/.bash_aliases_eraserhead' >> ~/.bashrc

# Reload shell
source ~/.bashrc
```

### Verify Aliases Loaded

```bash
alias | grep eh
alias | grep tc
alias | grep harold

# Test an alias
eh  # Should CD to project directory
```

**Available Aliases**:
- Project: `eh` (cd to project)
- tinyclaw: `tc`, `tcs` (search), `tcstore`
- Agents: `harold-plan`, `harold-code`, `harold-secure`, `harold-test`, `harold-doc`, `harold-research`
- Quality: `ehtest`, `ehlint`, `ehfmt`, `ehsec`, `ehqc`, `ehpc`
- Models: `llm-start`, `llm-health`
- Memory: `ehsync`
- Workflows: `ehcheck`, `ehship`
- Monitoring: `ehram`, `ehcpu`, `ehres`

---

## ✅ Validation

### Run Setup Validation Script

```bash
cd /home/kang/Documents/projects/radkit/eraserhead
./scripts/setup-validate.sh
```

**Expected Output** (after full setup):
```
😐 EraserHead + tinyclaw Setup Validation
==========================================

📦 Checking Node.js...
✓ Node.js installed: v22.12.0
✓ npm installed: 10.5.0

🔧 Checking tinyclaw...
✓ tinyclaw installed: x.x.x

⚙️  Checking configuration...
✓ tinyclaw config exists: /home/kang/.config/tinyclaw/config.json5
✓ Config file is valid

🧠 Checking memory system...
✓ Memory database exists: 128K

🔑 Checking API keys...
✓ ANTHROPIC_API_KEY set (for Opus 4.6 security reviews)

🤖 Checking local models...
✓ Found 3 model(s) in models/llama-cpp

🚀 Checking inference server...
✓ llama.cpp server responsive (port 8080)

🔗 Checking bash aliases...
✓ Aliases loaded (tc command available)

💾 Checking system resources...
✓ Total RAM: 14Gi
✓ Available RAM: 8.3Gi
✓ CPU cores: 8
✓ Sufficient RAM for 1.5b model

🔍 Testing memory search...
✓ Memory search functional

🛡️  Checking quality scripts...
✓ scripts/format.sh is executable
✓ scripts/lint.sh is executable
✓ scripts/test.sh is executable
✓ scripts/security-scan.sh is executable
✓ scripts/quality-check.sh is executable
✓ scripts/pre-commit.sh is executable

==========================================
📊 Validation Summary
==========================================
✓ Success: 22
⚠ Warnings: 0
✗ Errors: 0

🎉 Perfect! All checks passed. Harold is ready to ship code. 😐
```

---

## 🛠️ Usage Workflows

### Interactive Agent Sessions

```bash
# General Harold conversation
harold

# Specific agent
harold-plan  # Planning with harold-planner
harold-code  # Implementation with harold-implementer
harold-secure  # Security review (Opus 4.6)
harold-test  # Test generation
harold-doc  # Documentation
harold-research  # Research & library evaluation
```

### Memory-Assisted Development

```bash
# Search before implementing
tcs "packet encryption requirements"
tcs "ChaCha20-Poly1305 usage"
tcs "Dark Harold security principles"

# Context-aware prompts
harold-code  # Automatically has access to memory context
```

### TDD Workflow with tinyclaw

```bash
# 1. Research crypto libraries
harold-research  # "Evaluate ChaCha20-Poly1305 vs AES-GCM for Python 3.14"

# 2. Plan module structure
harold-plan  # "Design crypto.py interface for Anemochory protocol"

# 3. Implement (scoped for 1.5b model)
harold-code  # "Implement encrypt() function using ChaCha20, return bytes"

# 4. Run tests immediately
ehtest -k crypto

# 5. Security review (switches to Opus 4.6)
harold-secure  # "Review crypto.py for timing attacks and key management"

# 6. Document
harold-doc  # "Write docstring for encrypt() with usage examples"

# 7. Quality gates
ehpc  # Pre-commit checks

# 8. Sync new specs/ADRs
ehsync
```

### Agent Handoff Pattern

```bash
# Week 3 Task: Crypto primitive selection
# ----------------------------------------

# Step 1: Research
harold-research  # Query: "Evaluate Python crypto libraries..."
# Creates: specs/001-anemochory-protocol/research.md

# Step 2: Security review research
harold-secure  # Query: "Review crypto research findings..."
# Validates: Library choices, identifies risks

# Step 3: Planning
harold-plan  # Query: "Design packet format with approved crypto..."
# Creates: specs/001-anemochory-protocol/ADR-001-crypto-selection.md

# Step 4: Implementation
harold-code  # Query: "Implement crypto.py interface per ADR-001..."
# Creates: src/anemochory/crypto.py

# Step 5: Testing
harold-test  # Query: "Generate property-based tests for crypto..."
# Creates: tests/anemochory/test_crypto.py

# Step 6: Security review code
harold-secure  # Query: "Review crypto.py implementation..."
# Validates: Implementation correctness, signs off

# Step 7: Documentation
harold-doc  # Query: "Document crypto module API..."
# Updates: docs/anemochory-api-reference.md

# Step 8: Memory sync
ehsync  # Indexes new ADR and docs into memory
```

---

## 🎯 Task Sizing for 1.5b Model

The 1.5b model works best with **tightly scoped, well-defined tasks**:

### ✅ Good Task Sizes (1.5b Handles Well)

- **Single function implementation**: "Implement `generate_key()` that returns 32 bytes using secrets.token_bytes()"
- **Test generation**: "Generate pytest tests for `encrypt()` function covering happy path and error cases"
- **Documentation**: "Write Google-style docstring for `decrypt()` function with parameters and examples"
- **Simple refactoring**: "Rename `key` parameter to `encryption_key` throughout crypto.py"
- **Bug fixing**: "Fix off-by-one error in packet padding at line 42"

### ❌ Too Complex for 1.5b (Use Cloud Fallback)

- **Architecture design**: "Design the entire routing algorithm for Anemochory protocol" → Use harold-plan (may fallback to Sonnet)
- **Multi-file refactors**: "Refactor entire networking layer across 5 modules" → Break into smaller tasks
- **Security reviews**: "Audit crypto implementation for timing attacks" → Use harold-secure (ALWAYS Opus 4.6)
- **Complex debugging**: "Investigate race condition across async network stack" → Use 3b or cloud

### 📏 Task Sizing Rules

1. **One function or class per prompt** — Clear boundaries
2. **Include expected interface** — Type hints, parameter descriptions
3. **State success criteria** — What does "done" look like?
4. **Reference existing patterns** — "Similar to existing `decode()` function"

5. **Provide test requirements** — "Include tests for empty input and max size"

---

## 🚫 Alternative: Direct Implementation Without tinyclaw

If tinyclaw installation fails or you prefer direct implementation:

### Option 1: Direct Local LLM (llama.cpp)

```bash
# Start server
./scripts/llm-start-cpu.sh

# Use curl directly
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5-coder-1.5b-instruct",
    "messages": [{"role": "user", "content": "Implement Python function to generate 32-byte key"}],
    "temperature": 0.7
  }'
```

### Option 2: Use GitHub Copilot (in VS Code)

GitHub Copilot (this agent) has access to:
- Project constitution and specs
- Harold persona guidelines
- Model routing rules
- Quality standards

Simply ask for implementation and it will follow EraserHead standards:

```
User: "Implement src/anemochory/crypto.py with encrypt() and decrypt() functions"
Copilot: [Generates code with Harold comments, type hints, Google docstrings]
```

### Option 3: Manual Implementation (Traditional)

Follow [DEVELOPMENT-PLAN.md](DEVELOPMENT-PLAN.md) week-by-week:
1. Read specs in `specs/`
2. Implement modules in `src/`
3. Write tests in `tests/`
4. Run quality checks: `./scripts/quality-check.sh`
5. Document in `docs/`

All development practices still apply:
- >80% test coverage
- Harold persona in comments
- Security reviews for crypto (manual or via Copilot)
- Quality gates before commit

---

## 🔧 Troubleshooting

### tinyclaw Not Found After Install

```bash
# Check npm global path
npm config get prefix

# If not in PATH, add to ~/.bashrc
echo 'export PATH="$(npm config get prefix)/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Memory Search Returns No Results

```bash
# Re-sync memory
cd /home/kang/Documents/projects/radkit/eraserhead
./scripts/sync-memory.sh

# Check database size
ls -lh ~/.config/tinyclaw/memory/memory.db

# If still empty, check tinyclaw logs
tinyclaw --debug memory search "test"
```

### Inference Server Not Responding

```bash
# Check if running
curl http://localhost:8080/health
curl http://localhost:8000/health  # vLLM alternative

# Restart server
pkill -f llama-server  # or vllm
./scripts/llm-start-cpu.sh

# Check logs
journalctl --user -u llama-cpp  # if using systemd
```

### API Key Not Working for Opus

```bash
# Verify key is set
echo $ANTHROPIC_API_KEY

# Test API key directly
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"claude-opus-4","max_tokens":10,"messages":[{"role":"user","content":"test"}]}'
```

### Aliases Not Loading

```bash
# Check if ~/.bashrc sources ~/.bash_aliases
grep ".bash_aliases" ~/.bashrc

# If not, add it
echo '
if [ -f ~/.bash_aliases ]; then
    . ~/.bash_aliases
fi' >> ~/.bashrc

# Reload
source ~/.bashrc

# Test
alias | grep eh
```

---

## 💰 Cost Optimization

### Target: <$50/Month

**Breakdown**:
- **90% of tasks**: Local (1.5b-3b models) — $0
- **8% of tasks**: Sonnet (complex planning) — ~$10-$20
- **2% of tasks**: Opus (security/crypto only) — ~$20-$30

**Cost Control Strategies**:
1. **Break tasks into 1.5b-sized chunks** — Avoid unnecessary cloud usage
2. **Use Sonnet for research, not Opus** — Opus only for harold-security
3. **Batch security reviews** — Review multiple modules together
4. **Cache successful prompts** — Reuse patterns that work
5. **Monitor usage** — Check Anthropic dashboard monthly

### Typical Month (Phase 1 Implementation)

- **Week 3**: $15 (crypto research + initial security review)
- **Week 4**: $20 (crypto implementation security audit)
- **Week 5**: $10 (packet/routing review)
- **Week 6**: $15 (final protocol audit)
- **Total**: ~$60 (over budget, but worth it for security)

🌑 **Dark Harold's Budget Rule**: "Never cheap out on security reviews. Budget overruns on Opus are acceptable. Vulnerabilities are not."

---

## 📚 Additional Resources

- [TINYCLAW.md](TINYCLAW.md) — Bootstrap instructions
- [LOCAL-INFERENCE-GUIDE.md](LOCAL-INFERENCE-GUIDE.md) — Model selection guide
- [.specify/memory/constitution.md](.specify/memory/constitution.md) — Development principles
- [DEVELOPMENT-PLAN.md](DEVELOPMENT-PLAN.MD) — 16-week roadmap
- [agents/](agents/) — Agent YAML configurations

---

## ✅ Next Steps After Setup

Once validation passes:

```bash
# 1. Confirm setup
./scripts/setup-validate.sh

# 2. Test workflow
harold-research  # Test agent interaction

# 3. Begin Phase 1, Week 3
eh  # CD to project
harold-research  # "Evaluate ChaCha20-Poly1305 vs AES-GCM for Python 3.14"

# 4. Monitor resources
ehram  # Check memory usage during development
```

---

😐 **Harold's Setup Summary**: Installation is straightforward when Node.js cooperates. Memory system is powerful once populated. Agent coordination makes development feel like having a team. But Dark Harold reminds us: Every tool is a potential failure point. Test each component. Trust nothing. Ship anyway.

🌑 **Dark Harold's Final Warning**: tinyclaw stores all context in SQLite. Back up `~/.config/tinyclaw/memory/` regularly. When (not if) your disk fails, you'll want those ADRs and research notes. Don't learn this the hardway.
