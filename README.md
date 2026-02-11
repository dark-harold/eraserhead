# 😐 EraserHead: Digital Privacy Through Origin Obfuscation

*Pragmatically erasing digital footprints while smiling through the pain*

**EraserHead** is a Python platform for systematically erasing your internet presence and providing truly anonymized network access through the **Anemochory Protocol** — multi-layer origin obfuscation that goes beyond mere VPNs.

🌱 **Anemochory**: Like seeds dispersed by wind, your packets travel untraceable paths through the network, their origin obscured by encryption layers and pseudo-random routing.

**Status**: Planning Phase (Week 4 — Forward Secrecy & Replay Protection Complete)  
**License**: MIT  
**Python**: >=3.14 required

---

## Core Capabilities

### 🌱 Anemochory Protocol
Multi-layer network anonymization through:
- **Nested encryption**: ChaCha20-Poly1305 per routing hop
- **Pseudo-random routing**: Non-deterministic paths prevent timing attacks
- **Origin obfuscation**: 3-7 hop routing with forward secrecy
- **Replay protection**: Timestamp validation + per-session nonce tracking

### 🧹 Scrubbing Engine *(Planned)*
Automated digital footprint erasure:
- Social media account deletion workflows
- Data broker removal requests (GDPR/CCPA)
- Platform API integration for content purging

### 🤖 Multi-Agent Architecture
Six specialized AI agents orchestrated by **tinyclaw**:
- **harold-planner**: System design & threat modeling
- **harold-implementer**: Pragmatic code delivery
- **harold-security**: Paranoid security audits
- **harold-researcher**: Library evaluation & protocol research
- **harold-tester**: Comprehensive test generation
- **harold-documenter**: Narrative documentation

All agents share unified context via local SQLite memory (hybrid BM25 + vector search).

---

## Quick Start

### Prerequisites

- Python >=3.14
- uv (package manager)
- Node.js >=22 (for tinyclaw)
- gitleaks (secret scanning)
- *Optional*: CUDA GPU for faster local inference

### Installation

```bash
# Clone repository
cd /path/to/eraserhead

# Create virtual environment
uv venv && source .venv/bin/activate

# Install dependencies
uv sync
uv pip install 'llama-cpp-python[server]' psutil

# Install tinyclaw globally
npm install -g @mrcloudchase/tinyclaw

# Configure tinyclaw
cp tinyclaw-config.example.json5 ~/.config/tinyclaw/config.json5
# Edit config: set memory backend to "builtin"

# Download local models (Qwen2.5-Coder-7B recommended)
./scripts/download-models.sh 7b

# Start local inference
./scripts/llm-start.sh

# Sync specifications to memory
./scripts/sync-memory.sh

# Verify setup
./scripts/model-health.sh
```

### Development Workflow

```bash
# Run quality gates before committing
./scripts/pre-commit.sh

# Run tests with coverage
./scripts/test.sh

# Publish anonymously via container
./scripts/publish-gh.sh
```

😐 All development happens locally. No CI/CD. Harold trusts no cloud.

---

## Architecture

```
┌─────────────────────────────────────────┐
│ User Applications                        │
│ • Mobile (React Native/Flutter)         │
│ • Web (FastAPI backend)                 │
└────────────┬────────────────────────────┘
             │
┌────────────▼────────────────────────────┐
│ Anemochory Protocol Layer               │
│ • Multi-layer encryption                │
│ • Pseudo-random routing                 │
│ • Origin obfuscation (3-7 hops)         │
│ • Forward secrecy + replay protection   │
└────────────┬────────────────────────────┘
             │
┌────────────▼────────────────────────────┐
│ Scrubbing Engine                         │
│ • Social media deletion                 │
│ • Data broker removal                   │
│ • GDPR/CCPA automation                  │
└────────────┬────────────────────────────┘
             │
┌────────────▼────────────────────────────┐
│ Multi-Agent System (tinyclaw)           │
│ • Local models (llama.cpp/vLLM)         │
│ • Cloud models (Opus/Sonnet/grok)       │
│ • Shared memory (SQLite + FTS5 + vec)   │
└─────────────────────────────────────────┘
```

---

## Security Modules (Completed)

### ✅ Forward Secrecy (`crypto_forward_secrecy.py`)
- **Algorithm**: X25519 ECDH + HKDF-SHA256
- **Properties**: Ephemeral keys, session binding, timestamp binding
- **Coverage**: 94% (15 tests)
- **Status**: Production-ready

### ✅ Replay Protection (`crypto_replay.py`)
- **Mechanism**: 60-second time window + per-session nonce tracking
- **Memory**: ~4MB for 100k nonces (LRU eviction)
- **Coverage**: 100% (24 tests)
- **Status**: Production-ready

**Remaining** (Week 4-5):
- Key rotation (automatic re-keying)
- Master key storage (OS keychain integration)

---

## Documentation

All detailed documentation has been moved out of the root README for cleanliness:

- **[AGENTS.md](AGENTS.md)** - Multi-agent architecture, model routing, tinyclaw integration
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Development workflow, quality gates, local-first philosophy
- **[CONSTITUTION.md](CONSTITUTION.md)** - Guiding principles, security policies, governance
- **[docs/memes/harold/emoji-reference.md](docs/memes/harold/emoji-reference.md)** - Official Harold emoji lexicon

**Specifications**:
- [specs/001-anemochory-protocol/](specs/001-anemochory-protocol/) - Network anonymization protocol
- [specs/002-scrubbing-engine/](specs/002-scrubbing-engine/) - Digital footprint erasure
- [specs/003-agent-architecture/](specs/003-agent-architecture/) - Multi-agent system design

---

## Scripts

All quality control runs locally:

```bash
./scripts/security-scan.sh    # gitleaks, bandit, safety
./scripts/test.sh              # pytest with >80% coverage
./scripts/format.sh            # ruff format + lint
./scripts/pre-commit.sh        # all gates (blocks bad commits)
./scripts/model-health.sh      # verify local inference
./scripts/sync-memory.sh       # index specs into tinyclaw
./scripts/download-models.sh   # download GGUF models
./scripts/llm-start.sh         # auto-detect CPU/GPU and start
./scripts/publish-gh.sh        # anonymized git push (Podman)
```

---

## Project Status

```
Phase 0: Infrastructure ✅
├── uv-managed virtual environment
├── Local model inference (llama.cpp)
├── tinyclaw memory system
├── Quality gates (gitleaks, bandit, ruff, mypy)
└── Anonymized publishing (Podman container)

Phase 1: Anemochory Protocol 🚧
├── Forward secrecy ✅ (94% coverage)
├── Replay protection ✅ (100% coverage)
├── Key rotation ⏳ (Week 4-5)
├── Master key storage ⏳ (Week 4)
├── Packet format 📝 (spec complete, implementation pending)
└── Multi-hop routing ⏳ (Week 5-6)

Phase 2: Scrubbing Engine ⏳
└── Library research in progress (harold-researcher)

Phase 3: User Applications ⏳
└── Design phase pending
```

😐 Progress is steady. Harold smiles nervously at the roadmap.

---

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Development workflow (local-first)
- Quality gates and testing
- Code style and Harold's voice
- Agent usage patterns
- Anonymized publishing

**Philosophy**:
1. 😐 Smile Locally (no cloud dependencies)
2. ✅ Ship Pragmatically (working code > perfect plans)
3. 📺 Document Cynically (assume future disasters)
4. 🌑 Test Paranoidly (everything breaks eventually)

---

## Acknowledgments

- **Hide the Pain Harold** (András Arató) - For teaching us to smile through complexity
- **Internet Historian** - For showing us how to narrate technical disasters with style
- **Effective Developers Everywhere** - For shipping code despite the pain

---

## Contact

**Issues**: Use GitHub issues for bug reports and feature requests  
**Security**: See [SECURITY.md](SECURITY.md) for vulnerability disclosure  
**Philosophy**: Read [CONSTITUTION.md](CONSTITUTION.md) for Harold's principles

---

*"I've made a career out of hiding pain. Now I'm hiding packet origins."* — Harold, probably

😐 May your digital footprint fade like Harold's stock photography career never did.
