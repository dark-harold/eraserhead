# 😐 Changelog

All notable changes to EraserHead will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] — 2026-02-11

📺 *Harold reaches production. The smile is... almost genuine.*

### Added
- **Adversarial security test suite**: 27 tests covering nonce replay, key exchange attacks, key rotation exploitation, padding oracle probing, ciphertext tampering, session lifecycle abuse, and replay protection edge cases
- **Platform fallback path tests**: 8 additional tests for secure memory wiping cross-platform behavior

### Changed
- **HKDF salt parameter**: `derive_layer_key()` now accepts an explicit `salt` parameter for stronger key isolation (backward compatible with deterministic default)
- **Constant-time error messages**: `unpad_packet()` returns constant error message to prevent padding oracle attacks
- **Version bump**: 0.1.0a1 → 1.0.0 (Production/Stable)

### Fixed
- Resolved TODO in `crypto_key_storage.py`: clarified session key independence from master key rotation
- Resolved TODO in `crypto_key_rotation.py`: confirmed secure wipe implementation already present
- Cleaned up 90+ lint issues via ruff auto-fix (unused imports, formatting)
- Standardized ruff configuration with comprehensive per-file-ignores

### Security
- **HKDF salt binding** (SECURITY-REVIEW Issue #9): Layer keys now bound to unique salt material
- **Padding oracle mitigation** (SECURITY-REVIEW Issue #10): Error messages no longer leak internal state
- **Timing jitter** (Issue #7): Verified already implemented in node.py (5-50ms random delays)
- Zero critical/high bandit findings
- 901 tests, 94% coverage, all security review issues resolved

### Quality
- **901 tests** passing (up from 874)
- **94.02% code coverage** (80% minimum enforced)
- **Ruff lint**: Zero warnings (214 → 0)
- **Ruff format**: All files formatted
- **Bandit**: Zero actionable findings
- **All security review issues**: RESOLVED

---

## [0.1.0-alpha] — 2026-02-11

📺 *The inaugural release. Harold's first public smile.*

### Added

#### 🌱 Anemochory Protocol (`src/anemochory/`)
- **Onion packet construction**: Build and decrypt multi-layer encrypted packets (3-7 hops)
- **ChaCha20-Poly1305 encryption engine**: Per-layer authenticated encryption with constant-size packets (1024 bytes)
- **Pseudo-random routing**: Weighted path selection with geographic diversity constraints
- **Node processing**: AnemochoryNode with packet forwarding, exit handling, timing jitter (5-50ms)
- **Trio TCP transport**: Frame-based packet protocol with NodeServer and PacketSender
- **AnemochoryClient**: High-level send API with retry logic and path selection
- **Forward secrecy**: X25519 ECDH + HKDF-SHA256 ephemeral key exchange
- **Replay protection**: 60-second time window + per-session 100k nonce tracking (LRU eviction)
- **Key rotation**: Automatic re-keying every 10k packets or 1 hour
- **Master key storage**: PBKDF2-derived keys with AES-GCM encryption (ADR-004)
- **Secure sessions**: SecureSession manager integrating all cryptographic components

#### 🧹 Scrubbing Engine (`src/eraserhead/`)
- **Data models**: Platform, ResourceType, TaskPriority, TaskStatus, DeletionTask, DeletionResult, PlatformCredentials
- **Credential vault**: Fernet-encrypted storage with PBKDF2 key derivation (600k iterations)
- **Task queue**: Priority-ordered (URGENT → BACKGROUND) with exponential backoff + jitter retry
- **Platform adapters**: Abstract PlatformAdapter with token-bucket rate limiting; Twitter, Facebook, Instagram adapters (simulated)
- **Scrub engine**: Orchestrates queue + adapters with dry-run mode, verification, and progress tracking
- **Verification service**: Post-deletion confirmation with batch scan and re-appearance detection
- **CLI**: Typer-powered interface — `vault store/list/remove`, `scrub`, `status`, `version`

#### 🤖 Infrastructure
- **Multi-agent architecture**: Six Harold personas (planner, implementer, security, researcher, tester, documenter)
- **Local model inference**: llama.cpp + vLLM support with Qwen2.5-Coder models
- **Quality pipeline**: ruff, mypy (strict), bandit, gitleaks, pytest with 80% coverage gate
- **Anonymized publishing**: Podman container for git operations (no identity leakage)
- **ADRs**: Architecture decisions documented (ADR-003 through ADR-005)

### Quality
- **493 tests** passing
- **92% code coverage** (80% minimum enforced)
- **0 medium/high** bandit security issues
- **MyPy clean** on eraserhead (strict mode)

### 🌑 Known Limitations
- Platform adapters are simulated — real API integration planned for v0.2.0
- Transport layer at 50% coverage (network integration tests deferred)
- Single-user design — no multi-tenancy
- JSON queue persistence doesn't scale beyond ~100k tasks

---

😐 Harold ships the alpha. Sleep quality: unchanged.
