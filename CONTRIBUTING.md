# 😐 Contributing to EraserHead: Smile Locally, Ship Pragmatically, Document Cynically

*Development workflow, quality gates, and Harold's local-first philosophy*

**Last Updated**: February 10, 2026  
**Approach**: Local development, no CI/CD cloud dependencies, Harold approves

---

## Philosophy: Do As Harold Does

1. **😐 Smile Locally**: All development on local branches, no cloud dependencies
2. **✅ Ship Pragmatically**: Working code over perfect plans. Harold ships.
3. **📺 Document Cynically**: Internet Historian style. Assume future disasters.
4. **🌑 Test Paranoidly**: Dark Harold expects everything to break. Prove him wrong (you can't).
5. **Commit Narratively**: Commit messages tell stories. Harold approves.

---

## Setup: Prerequisites

Harold demands proper tooling before you touch code.

### Required

- **Python >=3.14**: For type hints and `typing` improvements
- **uv**: Fast Python package manager (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- **Node.js >=22.12.0**: For tinyclaw memory system
- **Podman**: Container runtime for anonymized publishing
- **gitleaks**: Secret detection (`sudo apt install gitleaks` or download from GitHub releases)

### Optional but Recommended

- **CUDA-capable GPU**: For vLLM inference (otherwise llama.cpp uses CPU)
- **age**: File encryption for local secrets (`sudo apt install age`)
- **htop**: To watch Harold's brain consume resources in real-time

---

## Initial Setup

### 1. Clone and Environment

```bash
# 😐 Clone the repository
cd /home/kang/Documents/projects/radkit/eraserhead

# 😐 Create isolated Python environment with uv
uv venv
source .venv/bin/activate

# 😐 Install all dependencies (dev, security, quality)
uv sync

# 😐 Install llama-cpp-python with server support
uv pip install 'llama-cpp-python[server]' psutil
```

---

### 2. Install tinyclaw (Global)

```bash
# 😐 Install tinyclaw memory system
npm install -g @mrcloudchase/tinyclaw

# 😐 Configure tinyclaw
mkdir -p ~/.config/tinyclaw
cp tinyclaw-config.example.json5 ~/.config/tinyclaw/config.json5

# 😐 Edit config with your preferences
# Set memory backend to "builtin" (SQLite + FTS5 + sqlite-vec)
# Configure model providers (anthropic, openai, llamacpp, vllm)
```

**tinyclaw config highlights**:
```json5
{
  memory: {
    backend: "builtin",  // SQLite-based, no external dependencies
    path: "~/.config/tinyclaw/memory/memory.db",
    chunking: {
      size: 512,
      overlap: 64
    }
  },
  providers: {
    anthropic: { api_key: "..." },  // Optional, for cloud models
    llamacpp: { endpoint: "http://127.0.0.1:8080" },  // Local CPU inference
    vllm: { endpoint: "http://127.0.0.1:8081" }  // Local GPU inference (if available)
  }
}
```

---

### 3. Download Local Models

```bash
# 😐 Download Qwen2.5-Coder models (GGUF format for llama.cpp)
./scripts/download-models.sh 3b  # 3B model (~2GB)
./scripts/download-models.sh 7b  # 7B model (~4.4GB, recommended)

# Models stored in: models/llama-cpp/
```

**Model Selection**:
- **qwen2.5-coder-0.5b**: Fast, low memory (~588MB RAM), routine tasks
- **qwen2.5-coder-1.5b**: Balanced, moderate tasks (~1.8GB RAM)
- **qwen2.5-coder-3b**: Good quality, ~2GB RAM
-**qwen2.5-coder-7b**: Best quality, ~4.4GB RAM (selected for EraserHead)

😐 Harold runs 7B on CPU. It's warm. The laptop fan agrees.

---

### 4. Start Local Inference

```bash
# 😐 Auto-detect CPU/GPU and start appropriate server
./scripts/llm-start.sh

# Or manually:
# CPU (llama.cpp)
MODEL_FILE=qwen2.5-coder-7b-instruct-q4_k_m.gguf ./scripts/llm-start-cpu.sh

# GPU (vLLM, if CUDA available)
MODEL_FILE=qwen2.5-coder-7b-instruct-q4_k_m.gguf ./scripts/llm-start-gpu.sh

# 😐 Verify server health
./scripts/model-health.sh
```

**Expected output**:
```
✅ llama.cpp server: Healthy (http://127.0.0.1:8080)
Model: qwen2.5-coder-7b-instruct-q4_k_m.gguf
Status: ready
😐 Harold's brain is operational
```

---

### 5. Sync Specifications to Memory

```bash
# 😐 Index specs, constitution, and documentation into tinyclaw
./scripts/sync-memory.sh

# This indexes:
# - specs/001-anemochory-protocol/**
# - CONSTITUTION.md
# - AGENTS.md
# - Architecture Decision Records (ADRs)
```

🌑 All agents now share context. Harold's distributed brain is ready.

---

## Development Workflow

### The Harold Method

```bash
# 1. 📺 Specify what you're building
/speckit.specify "Implement key rotation for forward secrecy module"

# Output: specs/004-key-rotation/spec.md (narrative specification)

# 2. 😐 Plan the architecture
/harold-planner Review spec and create implementation plan

# Output: specs/004-key-rotation/plan.md (with threat model)

# 3. 🌑 Security review the design
/harold-security Review key rotation design for vulnerabilities

# Output: Security review report, threat model updates

# 4. ✅ Implement pragmatically
/harold-implementer Implement key rotation based on plan

# Output: Working code, likely with sarcastic comments

# 5. 😐 Test paranoidly
/harold-tester Generate comprehensive tests for key rotation

# Output: Test suite with >80% coverage

# 6. 📺 Document the tale
/harold-documenter Write ADR for key rotation decision

# Output: docs/decisions/ADR-004-key-rotation.md (narrative style)

# 7. 😐 Run local quality gates
./scripts/pre-commit.sh

# 8. ✅ Ship it (anonymously)
./scripts/publish-gh.sh
```

---

## Quality Gates (Local Enforcement)

Harold trusts no cloud. All gates run locally.

### Pre-Commit Hook

**Auto-installed**: `.git/hooks/pre-commit` runs automatically on `git commit`

**What it does**:
1. **gitleaks**: Scans for secrets (API keys, tokens, passwords)
2. **bandit**: Python security SAST
3. **safety**: Dependency vulnerability scan
4. **ruff check**: Linting (including security rules)
5. **ruff format --check**: Code formatting validation
6. **mypy**: Static type checking (strict mode)

**Manual execution**:
```bash
./scripts/pre-commit.sh

# Or individual gates:
./scripts/security-scan.sh  # gitleaks + bandit + safety
./scripts/format.sh check   # ruff format --check
./scripts/lint.sh           # ruff check
```

---

### Test Coverage Gate

**Requirement**: >80% coverage on all modules

```bash
# 😐 Run full test suite with coverage
./scripts/test.sh

# Or specific modules:
pytest tests/anemochory/test_crypto_forward_secrecy.py \
  --cov=src/anemochory/crypto_forward_secrecy \
  --cov-report=term-missing

# Expected output:
# 39 passed in 0.58s
# Coverage: 94% (crypto_forward_secrecy), 100% (crypto_replay)
```

**Coverage fails <80%** → CI blocks merge (local enforcement via pytest settings)

🌑 If it's not tested, it's not working. It's just working *so far*.

---

### Security Scan Gate

```bash
# 😐 Full security audit
./scripts/security-scan.sh

# Components:
# 1. gitleaks: Secret detection (regex + entropy analysis)
# 2. bandit: Python code SAST (CWE database)
# 3. safety: Known CVE scan for dependencies
# 4. ruff: Security-focused linting rules
```

**Blocks commit if**:
- Secrets detected (hardcoded keys, tokens)
- High-severity bandit findings
- Known vulnerabilities in dependencies (CRITICAL/HIGH)

---

### Code Quality Gate

```bash
# 😐 Linting and formatting
./scripts/quality-check.sh

# Or separately:
ruff format src/ tests/  # Auto-format
ruff check src/ tests/   # Lint
mypy --strict src/       # Type check
```

**Standards**:
- **Line length**: 100 characters (ruff configured)
- **Type hints**: Required on all functions (mypy strict)
- **Docstrings**: Google style, narrative tone
- **Comments**: Harold's observations (e.g., `# 😐 This will scale fine`)

---

## Code Style: Harold's Voice

### Comment Style

**Good** (Harold approved):
```python
# 😐 This definitely won't cause problems at scale
def derive_session_master_key(shared_secret: bytes, session_id: bytes) -> bytes:
    """
    Derive session master key from shared secret using HKDF.
    
    😐 Binds key to session_id and timestamp for uniqueness.
    🌑 Different session IDs produce different keys from same shared secret.
    
    Args:
        shared_secret: Output from ECDH (32 bytes)
        session_id: Unique session identifier (32 bytes)
        
    Returns:
        32-byte master key for ChaCha20-Poly1305
        
    Raises:
        ForwardSecrecyError: If key derivation fails
    """
```

**Bad** (Harold disapproves):
```python
# derive key
def derive_key(secret, id):  # No types, no Harold
    return hkdf(secret, id)  # No context, no humor
```

---

### Docstring Style

**Format**: Google style with Harold persona

```python
def mark_nonce_seen(self, nonce: bytes, session_id: bytes) -> None:
    """
    Record nonce as seen to detect duplicates.
    
    😐 Call this after successfully decrypting packet.
    🌑 If nonce already seen, that's a replay attack!
    
    Args:
        nonce: Nonce from encryption (12 bytes for ChaCha20-Poly1305)
        session_id: Session identifier for isolation
        
    Raises:
        ReplayProtectionError: If memory limit exceeded (defensive)
        
    Example:
        >>> manager = ReplayProtectionManager()
        >>> nonce = secrets.token_bytes(12)
        >>> session_id = b"test_session_16b"
        >>> 
        >>> assert not manager.is_nonce_seen(nonce, session_id)
        >>> manager.mark_nonce_seen(nonce, session_id)
        >>> assert manager.is_nonce_seen(nonce, session_id)  # Replay detected!
    """
```

**Key elements**:
1. **One-line summary**: What it does
2. **Harold commentary**: Why/when to use, caveats
3. **Args/Returns/Raises**: Formal specification
4. **Example**: Executable doctest when possible

---

### Commit Message Style

**Format**: Narrative, Internet Historian style

**Good**:
```
✅ Implement forward secrecy module with X25519 ECDH

The crypto_forward_secrecy module provides ephemeral key exchange
using X25519 ECDH + HKDF-SHA256. Each session generates unique
keypairs that are never persisted.

😐 Security properties:
- Forward secrecy (past sessions safe if current key compromised)
- Session binding (different session IDs → different master keys)
- Timestamp binding (temporal isolation)

🌑 Known limitations:
- No automatic key rotation (addressed in next sprint)
- Session keys held in memory (side-channel attacks possible)

Test coverage: 94% (15 tests, 4 test classes)
Quality: ✅ ruff, ✅ mypy strict, ✅ bandit

Addresses: SECURITY-REVIEW-CRYPTO.md Critical Issue #1
```

**Bad**:
```
add forward secrecy
```

---

## Anonymized Publishing

### Problem: Git Metadata Leaks Identity

**Git reveals**:
- Hostname (via commit metadata)
- Username (via git config)
- Timezone (via commit timestamps)
- SSH fingerprints (via authentication)
- Working patterns (commit timing analysis)

🌑 Dark Harold: *They can correlate your typing cadence. Obfuscate everything.*

---

### Solution: Podman Container Publishing

```bash
# 😐 Publish via anonymized container
./scripts/publish-gh.sh

# What it does:
# 1. Spawns Alpine Linux container (Podman)
# 2. Prompts for GitHub CLI token (interactive, secure)
# 3. Obfuscates: hostname, timezone, git config
# 4. Randomizes commit author metadata
# 5. Pushes to repository under separate account
# 6. Cleans up: SSH keys, tokens, git history
# 7. Destroys container
```

**Container protections**:
- Hostname: Randomized per session
- Timezone: UTC (no local timezone leak)
- Git config: Generated, not imported from host
- SSH keys: Ephemeral, deleted post-push
- GitHub token: Encrypted in transit, never plaintext on disk

😐 Harold publishes anonymously. Like his stock photos—everywhere, but origin unknown.

---

## Agent Usage from CLI

### Invoke Agents Directly

```bash
# 📺 Planning
tinyclaw chat --agent harold-planner \
  --prompt "Design key rotation mechanism with automatic ratcheting" \
  --memory-search "forward secrecy session management"

# ✅ Implementation
tinyclaw chat --agent harold-implementer \
  --file src/anemochory/crypto_forward_secrecy.py \
  --prompt "Add key rotation method with 10k packet threshold"

# 🌑 Security Review
tinyclaw chat --agent harold-security \
  --file src/anemochory/crypto_forward_secrecy.py \
  --prompt "Audit for timing attacks and key material leakage"

# 😐 Testing
tinyclaw chat --agent harold-tester \
  --prompt "Generate edge case tests for key rotation logic"

# 📺 Documentation
tinyclaw chat --agent harold-documenter \
  --prompt "Write ADR for key rotation decision and threat model"
```

---

### Invoke via VS Code Copilot

**Slash commands** (configured in `.github/agents/`):

```
/harold-planner <task description>
/harold-implementer <implementation request>
/harold-security <security review request>
/harold-researcher <research question>
/harold-tester <testing request>
/harold-documenter <documentation request>
```

**Model routing** (automatic):
- harold-security: **Always Opus 4.6** (non-negotiable)
- harold-planner: Opus 4.6 / local tinyclaw
- harold-implementer: grok-code-fast-1 / llama.cpp
- Others: Sonnet / local

---

## Memory Management

### Sync Specs to tinyclaw

```bash
# 😐 Index all specifications and documentation
./scripts/sync-memory.sh

# Indexes:
# - specs/**/*.md (all protocol specs)
# - CONSTITUTION.md
# - AGENTS.md
# - docs/decisions/*.md (ADRs)
# - docs/architecture/*.md
```

**Automatic sync** when:
- New spec created (`/speckit.specify`)
- ADR written (`/harold-documenter`)
- Constitution amended (manual trigger required)

---

### Query Memory Directly

```bash
# 😐 Search shared context
tinyclaw memory search "forward secrecy key exchange ECDH"

# Returns:
# - Relevant chunks from indexed documents
# - Hybrid BM25 + cosine similarity ranking
# - Source file references

# 😐 Inspect memory stats
tinyclaw memory stats

# Output: chunk count, source files, index size
```

---

### Clear Memory (Nuclear Option)

```bash
# 🌑 Wipe all indexed context
tinyclaw memory clear

# Then re-sync:
./scripts/sync-memory.sh
```

**Warning**: All agents lose shared context until re-sync.  
😐 Use only when memory becomes corrupted or testing fresh indexing.

---

## Testing Philosophy

### Test Like Harold Tests

harold-tester embodies:
- **😐 Break things with a smile**: Creative failure scenarios
- **🌑 Assume adversarial inputs**: Malicious data, edge cases
- **✅ Pragmatic coverage**: >80% required, 100% impractical
- **📺 Document failures**: Tests narrate what could go wrong

**Example test narrative**:
```python
class TestReplayProtection:
    """😐 Breaking replay protection with a smile"""
    
    def test_duplicate_nonce_detected(self):
        """🌑 Detects replay attacks (the whole point)"""
        manager = ReplayProtectionManager()
        nonce = secrets.token_bytes(12)
        
        # First use: legitimate
        assert not manager.is_nonce_seen(nonce, session_id)
        manager.mark_nonce_seen(nonce, session_id)
        
        # Second use: REPLAY ATTACK! 🌑
        assert manager.is_nonce_seen(nonce, session_id)
        
    def test_far_future_packet_rejected(self):
        """🌑 Packets far in future rejected (attack or bad clock)"""
        # 10 seconds in future (beyond 5s tolerance)
        future_time = time.time() + 10
        metadata = PacketMetadata(
            timestamp=future_time, 
            sequence_number=1, 
            session_id=session_id
        )
        
        assert not manager.validate_packet_metadata(metadata)
        # 📺 If this fails, time travelers are using our protocol
```

---

### Coverage Requirements

**Global**: >80% on all shipped code (enforced by `pyproject.toml`)

**Critical paths**: >90% coverage required
- Cryptographic modules (`src/anemochory/crypto_*.py`)
- Network handling (`src/anemochory/packet.py`)
- Security-sensitive code (anything touching keys or user data)

**Exceptions** (require ADR):
- Exploratory prototypes (must be marked clearly with `# 😐 PROTOTYPE`)
- External library integrations (mock boundaries instead of testing library internals)

---

## Local Development Tips

### 1. Use Virtual Environment

```bash
# 😐 Always activate before working
source .venv/bin/activate

# 😐 Verify isolation
which python3  # Should point to .venv/bin/python3
```

**Why**: No system-wide package pollution. Harold demands hygiene.

---

### 2. Run Pre-Commit Before Committing

```bash
# 😐 Catch issues before git hook blocks you
./scripts/pre-commit.sh

# Fix issues:
ruff format src/ tests/          # Auto-format
ruff check --fix src/ tests/     # Auto-fix lints
# Then manually address security findings
```

---

### 3. Test Early, Test Often

```bash
# 😐 Run tests as you develop
pytest tests/anemochory/test_crypto_forward_secrecy.py -v

# 😐 Watch coverage increase
pytest --cov=src/anemochory/crypto_forward_secrecy \
  --cov-report=html \
  && open htmlcov/index.html
```

---

### 4. Sync Memory After Spec Changes

```bash
# 😐 Update agent context
./scripts/sync-memory.sh

# Verify sync:
tinyclaw memory search "your new feature"
```

---

### 5. Monitor Local Model Resource Usage

```bash
# 😐 Watch Harold's brain consume RAM
htop

# Or:
./scripts/model-health.sh

# Check logs:
tail -f /tmp/llama-server.log      # llama.cpp CPU
tail -f /tmp/vllm-server.log       # vLLM GPU (if running)
```

---

## Troubleshooting

### Issue: gitleaks Blocks Commit (False Positive)

**Solution**: Add exception to `.gitleaks.toml`:
```toml
[[rules]]
description = "Inline test fixtures are not secrets"
regex = '''test_secret_key'''
path = '''tests/'''
```

---

### Issue: Local Model Not Responding

```bash
# 😐 Check if server running
ps aux | grep llama

# Restart server
./scripts/llm-start.sh

# Check health
./scripts/model-health.sh
```

---

### Issue: tinyclaw Memory Search Returns Nothing

```bash
# 😐 Re-sync memory
./scripts/sync-memory.sh

# Verify files indexed:
tinyclaw memory stats
```

---

### Issue: Test Coverage Below 80%

```bash
# 😐 Find uncovered lines
pytest --cov=src/anemochory/crypto_forward_secrecy \
  --cov-report=term-missing

# Output shows missing line numbers:
# src/anemochory/crypto_forward_secrecy.py:54, 296, 300-301

# Add tests for those lines
```

---

## Advanced: Running Multiple Model Instances

```bash
# 😐 Run 0.5B and 1.5B models in parallel (resource permitting)
python -m llama_cpp.server \
  --model models/llama-cpp/qwen2.5-coder-0.5b-instruct-q4_k_m.gguf \
  --port 8080 --n_ctx 4096 --n_threads 2 &

python -m llama_cpp.server \
  --model models/llama-cpp/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf \
  --port 8082 --n_ctx 8192 --n_threads 4 &

# Configure tinyclaw to use both:
# providers.llamacpp_small.endpoint = "http://127.0.0.1:8080"
# providers.llamacpp_large.endpoint = "http://127.0.0.1:8082"
```

**Use case**: Route simple queries to 0.5B (fast), complex to 1.5B (better quality).

😐 Harold now has multiple brains. This is fine.

---

## Resources

**Internal Documentation**:
- [AGENTS.md](AGENTS.md) - Agent architecture and personas
- [CONSTITUTION.md](CONSTITUTION.md) - Guiding principles
- [docs/memes/harold/emoji-reference.md](docs/memes/harold/emoji-reference.md) - Harold emoji guide
- [specs/](specs/) - Protocol specifications and ADRs

**External Tools**:
- [uv documentation](https://docs.astral.sh/uv/)
- [tinyclaw GitHub](https://github.com/mrcloudchase/tinyclaw)
- [llama.cpp](https://github.com/ggerganov/llama.cpp)
- [gitleaks](https://github.com/gitleaks/gitleaks)

---

## Harold's Approval

*"I've made a career out of hiding pain while smiling confidently. Now my development workflow does the same."* — Harold (probably)

😐 Contribute locally. Ship pragmatically. Test paranoidly. Document cynically.  
🌑 Dark Harold watches your commits. Don't disappoint him.  
✅ Above all: working code > perfect plans.

---

*For agent details, see [AGENTS.md](AGENTS.md)*  
*For principles, see [CONSTITUTION.md](CONSTITUTION.md)*  
*For emoji usage, see [docs/memes/harold/emoji-reference.md](docs/memes/harold/emoji-reference.md)*
