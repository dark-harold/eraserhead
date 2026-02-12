# 😐 EraserHead: Digital Privacy Through Origin Obfuscation

*Pragmatically erasing digital footprints while smiling through the pain*

**EraserHead** is a Python platform for systematically erasing your internet presence and providing truly anonymized network access through the **Anemochory Protocol** — multi-layer origin obfuscation that goes beyond mere VPNs.

🌱 **Anemochory**: Like seeds dispersed by wind, your packets travel untraceable paths through the network, their origin obscured by encryption layers and pseudo-random routing.

**Status**: Production (v1.0.0) — Anemochory Protocol + Scrubbing Engine + Erasure Provider System  
**License**: MIT  
**Python**: >=3.13 required

---

## 😐 Core Capabilities

### 🌱 Anemochory Protocol (`src/anemochory/`)

> 📺 Like seeds dispersed by wind, packets travel paths that cannot be reconstructed. The destination knows the content. Nobody knows the origin.

Multi-layer network anonymization:
- **Nested onion encryption**: ChaCha20-Poly1305 per routing hop (3-7 hops)
- **Pseudo-random routing**: Weighted path selection with diversity constraints
- **Origin obfuscation**: Constant-size packets, timing jitter (5-50ms)
- **Forward secrecy**: X25519 ECDH + HKDF-SHA256 ephemeral keys
- **Replay protection**: 60-second window + per-session nonce tracking (100k LRU)
- **Key rotation**: Automatic re-keying every 10k packets or 1 hour
- **Master key storage**: PBKDF2-derived, OS keychain integration

### 🧹 Scrubbing Engine (`src/eraserhead/`)

> 😐 Every platform has a "delete" button. None of them work the way you think they do.

Automated digital footprint erasure:
- **Credential vault**: Fernet-encrypted storage with PBKDF2 key derivation (600k iterations)
- **Task queue**: Priority-ordered with exponential backoff + jitter retry
- **Platform adapters**: Pluggable adapters for Twitter, Facebook, Instagram, LinkedIn, Google
- **Verification service**: Post-deletion confirmation with re-scan capability
- **Erasure provider system**: Compliance-aware providers (GDPR, CCPA) with orchestration
- **Erasure modes**: Confirmation, containment, and target validation workflows
- **CLI**: Typer-powered command-line interface for all operations
- **Dry-run mode**: Preview deletions without executing

### 🤖 Multi-Agent Architecture

> 📺 Harold's brain is distributed. This is both efficient and makes debugging conversations awkward.

Six specialized AI agents orchestrated by **tinyclaw**:
- **harold-planner**: System design & threat modeling
- **harold-implementer**: Pragmatic code delivery
- **harold-security**: Paranoid security audits (always Claude Opus 4.6)
- **harold-researcher**: Library evaluation & protocol research
- **harold-tester**: Comprehensive test generation
- **harold-documenter**: Narrative documentation

All agents share unified context via local SQLite memory (hybrid BM25 + vector search).

---

## ✅ Quick Start

### Prerequisites

- Python >=3.13
- uv (package manager)
- *Optional*: Node.js >=22 (for tinyclaw agent system)
- *Optional*: CUDA GPU for faster local inference

### Installation

```bash
# Clone repository
git clone https://github.com/dark-harold/eraserhead.git
cd eraserhead

# Create virtual environment and install
uv venv && source .venv/bin/activate
uv sync
```

### CLI Usage

```bash
# Store platform credentials (encrypted)
eraserhead vault store twitter harold --token "your-token" -p

# List stored credentials
eraserhead vault list -p

# Scrub posts (dry run)
eraserhead scrub twitter --type post --ids "tweet-1,tweet-2" --dry-run -p

# Scrub posts (live deletion)
eraserhead scrub twitter --type post --ids "tweet-1,tweet-2" -p

# Check queue status
eraserhead status

# Show version
eraserhead version
```

### Development Workflow

```bash
# Run full quality gate (format, lint, mypy, bandit, tests, safety)
./scripts/quality-check.sh

# Run tests with coverage (>80% required)
.venv/bin/pytest

# Run individual checks
.venv/bin/ruff check src/ tests/    # Lint
.venv/bin/ruff format src/ tests/   # Format
.venv/bin/bandit -r src/ -ll        # Security scan
```

😐 All development happens locally. No CI/CD. Harold trusts no cloud.

---

## 📺 Architecture

> 📺 The tale of EraserHead's architecture: a CLI that talks to an engine that talks to adapters that talk to platforms that wish you'd stop deleting things.

```
┌─────────────────────────────────────────┐
│ CLI (eraserhead)                         │
│ • vault store/list/remove               │
│ • scrub (dry-run, live, multi-platform) │
│ • status, version                       │
└────────────┬────────────────────────────┘
             │
┌────────────▼────────────────────────────┐
│ Scrubbing Engine                         │
│ • CredentialVault (Fernet encrypted)    │
│ • TaskQueue (priority + backoff)        │
│ • ScrubEngine (orchestration)           │
│ • PlatformAdapters (Twitter/FB/IG)      │
│ • VerificationService (post-delete)     │
└────────────┬────────────────────────────┘
             │
┌────────────▼────────────────────────────┐
│ Anemochory Protocol Layer               │
│ • AnemochoryClient (send API)           │
│ • PathSelector (weighted routing)       │
│ • AnemochoryNode (packet processing)    │
│ • ChaCha20Engine (layer encryption)     │
│ • NodeServer (trio TCP)                 │
│ • Forward secrecy + replay protection   │
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

## 😐 Project Structure

```
src/
├── anemochory/                # Network anonymization protocol
│   ├── client.py              # High-level send API with retries
│   ├── crypto.py              # ChaCha20-Poly1305 encryption engine
│   ├── crypto_forward_secrecy.py  # X25519 ECDH + HKDF key exchange
│   ├── crypto_key_rotation.py # Automatic session re-keying
│   ├── crypto_key_storage.py  # Master key derivation + OS keychain
│   ├── crypto_memory.py       # Secure memory wiping (ctypes)
│   ├── crypto_replay.py       # Nonce replay protection
│   ├── models.py              # NodeInfo, NodePool, capabilities
│   ├── node.py                # Packet processing, forwarding, exit
│   ├── packet.py              # Onion packet construction/decryption
│   ├── routing.py             # Path selection, diversity constraints
│   ├── session.py             # Secure session with key exchange
│   └── transport.py           # Trio TCP framing and server
│
├── eraserhead/                # Digital footprint scrubbing engine
│   ├── adapters/              # Platform-specific adapters
│   │   ├── __init__.py        # PlatformAdapter ABC, rate limiting
│   │   └── platforms.py       # Twitter, FB, IG, LinkedIn, Google
│   ├── cli.py                 # Typer CLI interface
│   ├── engine.py              # ScrubEngine orchestration
│   ├── models.py              # Tasks, results, credentials, enums
│   ├── modes/                 # Erasure workflow modes
│   │   ├── base.py            # Base mode with lifecycle
│   │   ├── confirmation.py    # User confirmation workflows
│   │   ├── containment.py     # Data containment mode
│   │   └── target_validation.py  # Target validation checks
│   ├── providers/             # Erasure provider system
│   │   ├── base.py            # Provider ABC
│   │   ├── compliance.py      # GDPR/CCPA compliance checks
│   │   ├── orchestrator.py    # Multi-provider orchestration
│   │   ├── registry.py        # Provider discovery + registration
│   │   └── search/            # Search provider integration
│   ├── queue.py               # Priority queue with backoff
│   ├── vault.py               # Encrypted credential storage
│   └── verification.py        # Post-deletion verification
```

---

## ✅ Quality Metrics

> 😐 Harold doesn't ship without green gates. Harold has been hurt before.

| Metric | Value |
|--------|-------|
| Tests | 947 |
| Coverage | 95%+ |
| Bandit (med/high) | 0 issues |
| Ruff (lint + format) | 0 errors |
| Python | 3.13+ |

---

## 🌑 Security

> 🌑 Dark Harold reviewed every security module. Dark Harold approved with caveats. Dark Harold always has caveats.

EraserHead is designed with defense-in-depth:

- **Key material**: Secure memory wiping via `explicit_bzero()` / `RtlSecureZeroMemory()` with Python fallback
- **Vault encryption**: AES-128-CBC + HMAC-SHA256 (Fernet) with PBKDF2 (600k iterations)
- **Network layer**: ChaCha20-Poly1305 AEAD, X25519 ECDH, HKDF-SHA256 key derivation
- **Replay protection**: 60-second nonce window with 100k LRU cache per session
- **Forward secrecy**: Ephemeral keypairs with automatic key rotation (10k packets / 1 hour)
- **No assert in production paths**: Runtime exceptions replace assertions in security-critical code
- **No secrets in code**: Enforced by gitleaks + bandit scanning

---

## 📚 Documentation

- **[docs/user-guide.md](docs/user-guide.md)** - Getting started, CLI usage, troubleshooting
- **[docs/api-reference.md](docs/api-reference.md)** - Full API reference for all modules
- **[docs/adapter-development.md](docs/adapter-development.md)** - Building custom platform adapters
- **[AGENTS.md](AGENTS.md)** - Multi-agent architecture, model routing, tinyclaw
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Development workflow, quality gates
- **[CONSTITUTION.md](CONSTITUTION.md)** - Guiding principles, security policies
- **[DEVELOPMENT-PLAN.md](DEVELOPMENT-PLAN.md)** - Phase-by-phase roadmap

- **[docs/memes/harold/](docs/memes/harold/)** - Harold emoji, meme gallery, sourcing guide

**Specifications**:
- [specs/001-anemochory-protocol/](specs/001-anemochory-protocol/) - Network anonymization
- [specs/002-scrubbing-engine/](specs/002-scrubbing-engine/) - Digital footprint erasure
- [specs/003-agent-architecture/](specs/003-agent-architecture/) - Multi-agent system

---

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) for development workflow details.

**Philosophy**:
1. 😐 Smile Locally (no cloud dependencies)
2. ✅ Ship Pragmatically (working code > perfect plans)
3. 📺 Document Cynically (assume future disasters)
4. 🌑 Test Paranoidly (everything breaks eventually)

---

*"I've made a career out of hiding pain. Now I'm hiding packet origins."* — Harold, probably

😐 May your digital footprint fade like Harold's stock photography career never did.
