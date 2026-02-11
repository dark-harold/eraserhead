# 😐 EraserHead: Digital Privacy Through Origin Obfuscation

*Pragmatically erasing digital footprints while smiling through the pain*

**EraserHead** is a Python platform for systematically erasing your internet presence and providing truly anonymized network access through the **Anemochory Protocol** — multi-layer origin obfuscation that goes beyond mere VPNs.

🌱 **Anemochory**: Like seeds dispersed by wind, your packets travel untraceable paths through the network, their origin obscured by encryption layers and pseudo-random routing.

**Status**: Alpha (v0.1.0-alpha) — Anemochory Protocol + Scrubbing Engine Complete  
**License**: MIT  
**Python**: >=3.13 required

---

## Core Capabilities

### 🌱 Anemochory Protocol (`src/anemochory/`)
Multi-layer network anonymization:
- **Nested onion encryption**: ChaCha20-Poly1305 per routing hop (3-7 hops)
- **Pseudo-random routing**: Weighted path selection with diversity constraints
- **Origin obfuscation**: Constant-size packets, timing jitter (5-50ms)
- **Forward secrecy**: X25519 ECDH + HKDF-SHA256 ephemeral keys
- **Replay protection**: 60-second window + per-session nonce tracking (100k LRU)
- **Key rotation**: Automatic re-keying every 10k packets or 1 hour
- **Master key storage**: PBKDF2-derived, OS keychain integration

### 🧹 Scrubbing Engine (`src/eraserhead/`)
Automated digital footprint erasure:
- **Credential vault**: Fernet-encrypted storage with PBKDF2 key derivation
- **Task queue**: Priority-ordered with exponential backoff + jitter retry
- **Platform adapters**: Pluggable adapters for Twitter, Facebook, Instagram
- **Verification service**: Post-deletion confirmation with re-scan capability
- **CLI**: Typer-powered command-line interface for all operations
- **Dry-run mode**: Preview deletions without executing

### 🤖 Multi-Agent Architecture
Six specialized AI agents orchestrated by **tinyclaw**:
- **harold-planner**: System design & threat modeling
- **harold-implementer**: Pragmatic code delivery
- **harold-security**: Paranoid security audits (always Claude Opus 4.6)
- **harold-researcher**: Library evaluation & protocol research
- **harold-tester**: Comprehensive test generation
- **harold-documenter**: Narrative documentation

All agents share unified context via local SQLite memory (hybrid BM25 + vector search).

---

## Quick Start

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
# Run tests with coverage (>80% required)
./scripts/test.sh

# Run quality gates
./scripts/pre-commit.sh

# Run individual checks
./scripts/security-scan.sh    # gitleaks + bandit
./scripts/format.sh            # ruff format + lint
```

😐 All development happens locally. No CI/CD. Harold trusts no cloud.

---

## Architecture

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

## Project Structure

```
src/
├── anemochory/           # Network anonymization protocol
│   ├── client.py         # High-level send API with retries
│   ├── crypto.py         # ChaCha20-Poly1305 encryption engine
│   ├── models.py         # NodeInfo, NodePool, capabilities
│   ├── node.py           # Packet processing, forwarding, exit handling
│   ├── packet.py         # Onion packet construction/decryption
│   ├── routing.py        # Path selection, diversity constraints
│   ├── session.py        # Secure session with key exchange
│   └── transport.py      # Trio TCP framing and server
│
├── eraserhead/           # Digital footprint scrubbing engine
│   ├── adapters/         # Platform-specific adapters
│   │   ├── __init__.py   # PlatformAdapter ABC, rate limiting
│   │   └── platforms.py  # Twitter, Facebook, Instagram adapters
│   ├── cli.py            # Typer CLI interface
│   ├── engine.py         # ScrubEngine orchestration
│   ├── models.py         # Tasks, results, credentials, enums
│   ├── queue.py          # Priority queue with backoff
│   ├── vault.py          # Encrypted credential storage
│   └── verification.py   # Post-deletion verification
```

---

## Quality Metrics

| Metric | Value |
|--------|-------|
| Tests | 493 |
| Coverage | 92% |
| Bandit (med/high) | 0 issues |
| MyPy (eraserhead) | Clean |
| Python | 3.13+ |

---

## Documentation

- **[AGENTS.md](AGENTS.md)** - Multi-agent architecture, model routing, tinyclaw
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Development workflow, quality gates
- **[CONSTITUTION.md](CONSTITUTION.md)** - Guiding principles, security policies
- **[DEVELOPMENT-PLAN.md](DEVELOPMENT-PLAN.md)** - Phase-by-phase roadmap

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
