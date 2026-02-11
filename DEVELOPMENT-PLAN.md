# 😐 EraserHead Development Plan: Harold's Roadmap to Privacy

**Status**: Active Development  
**Last Updated**: February 10, 2026  
**Owner**: harold-planner  
**Review Cycle**: Weekly

---

## Executive Summary

*In which Harold outlines a multi-phase plan to build a privacy platform while acknowledging everything that will inevitably go wrong* 📺

EraserHead is a Python 3.14 platform for systematically erasing digital footprints and providing truly anonymized network access. This development plan coordinates three major features:

1. **Anemochory Protocol** (P0): Multi-layer origin obfuscation
2. **Scrubbing Engine** (P1): Automated data deletion across platforms
3. **Agent Architecture** (P0): Multi-agent development system

**Timeline**: 16 weeks (4 months) to MVP  
**Post-MVP**: Ongoing security audits, platform adapter additions, community feedback

---

## Development Principles

### The Harold Way ✅

1. **Privacy First**: Local-first inference, self-hosted infrastructure
2. **Security Paranoia**: Every feature reviewed by harold-security
3. **Quality Gates**: No code ships without passing local quality checks
4. **Test Coverage**: >80% coverage enforced
5. **Iterative Delivery**: Ship working increments, iterate on feedback
6. **Documentation**: Internet Historian quality narratives
7. **Pragmatic Scope**: Ship MVP, avoid feature creep

### Dark Harold's Reminders 🌑

1. Everything will break in production in ways we didn't test
2. Platforms will change APIs to break our adapters
3. Users will find edge cases we never imagined
4. Security vulnerabilities will be discovered post-launch
5. Nation-states will attack this if it actually works
6. **Plan for failure, document the recovery**

---

## Project Structure

```
eraserhead/
├── specs/                          # 😐 Specifications (source of truth)
│   ├── 001-anemochory-protocol/
│   │   ├── spec.md                # P0: Network anonymization
│   │   ├── research.md            # Library evaluation, threat modeling
│   │   └── {contracts}/           # Protocol contracts, packet formats
│   ├── 002-scrubbing-engine/
│   │   └── spec.md                # P1: Platform data deletion
│   └── 003-agent-architecture/
│       └── spec.md                # P0: Multi-agent development system
│
├── src/
│   ├── anemochory/                # Network obfuscation protocol
│   │   ├── __init__.py
│   │   ├── packet.py              # Packet encryption/routing
│   │   ├── node.py                # Network node implementation
│   │   ├── routing.py             # Pseudo-random routing algorithm
│   │   └── crypto.py              # Cryptography primitives
│   │
│   └── eraserhead/                # Main scrubbing engine
│       ├── __init__.py
│       ├── cli.py                 # Typer-based CLI
│       ├── engine.py              # Core scrubbing orchestrator
│       ├── adapters/              # Platform-specific adapters
│       │   ├── base.py            # Abstract adapter interface
│       │   ├── facebook.py
│       │   ├── twitter.py
│       │   └── instagram.py
│       ├── vault.py               # Encrypted credential storage
│       ├── queue.py               # Task queue (deletion operations)
│       └── verification.py        # Deletion verification system
│
├── tests/                         # Harold's comprehensive test suite
│   ├── test_anemochory/
│   └── test_eraserhead/
│
├── scripts/                       # 😐 Local automation (no CI/CD)
│   ├── download-models.sh         # Qwen2.5-coder model downloader
│   ├── llm-start.sh               # Auto-detect GPU/CPU inference
│   ├── llm-start-gpu.sh           # vLLM GPU inference
│   ├── llm-start-cpu.sh           # llama.cpp CPU inference
│   ├── format.sh                  # Ruff formatting
│   ├── lint.sh                    # Comprehensive linting
│   ├── quality-check.sh           # Full quality suite
│   ├── security-scan.sh           # Secrets + vulnerability scanning
│   ├── pre-commit.sh              # Pre-commit quality gates
│   └── test.sh                    # Pytest runner
│
├── agents/                        # Harold's specialized agents
│   ├── harold-planner.yml
│   ├── harold-implementer.yml
│   ├── harold-security.yml
│   ├── harold-researcher.yml
│   ├── harold-tester.yml
│   └── harold-documenter.yml
│
├── models/                        # Local inference models
│   └── llama-cpp/
│       ├── qwen2.5-coder-0.5b-instruct-q4_k_m.gguf
│       ├── qwen2.5-coder-1.5b-instruct-q4_k_m.gguf
│       ├── qwen2.5-coder-3b-instruct-q4_k_m.gguf
│       └── qwen2.5-coder-7b-instruct-q4_k_m.gguf
│
├── pyproject.toml                 # Python 3.14 config + tooling
├── model-config.yml               # Model routing configuration
├── tinyclaw-config.example.json5  # tinyclaw local-first config
└── README.md                      # Internet Historian narrative
```

---

## Phase 0: Infrastructure & Research (Weeks 1-2) ✅

**Status**: COMPLETE (congratulations, Harold shipped infrastructure!)

### Deliverables ✅

- [x] Project structure established
- [x] Python 3.14 environment configured
- [x] Ruff + comprehensive tooling (mypy, bandit, pyright, vulture, radon)
- [x] Local quality control scripts (no remote CI/CD)
- [x] Qwen2.5-coder models downloaded (0.5b, 1.5b, 3b, 7b)
- [x] tinyclaw configured for local-first inference
- [x] Agent architecture specified
- [x] Anemochory protocol specification
- [x] Scrubbing engine specification

### Success Criteria ✅

- [x] `./scripts/quality-check.sh` passes (format, lint, type check, security, tests)
- [x] Local models ready for inference (GPU/CPU paths)
- [x] All three feature specs complete and reviewed
- [x] Agent roles defined with model routing strategy

---

## Phase 1: Anemochory Protocol Core (Weeks 3-6)

**Owner**: harold-implementer + harold-security  
**Status**: NEXT (starting week 3)

### Week 3: Cryptography Foundation

**Tasks**:
- [ ] Research & select crypto primitives (harold-researcher + harold-security)
  - ChaCha20-Poly1305 vs AES-GCM evaluation
  - Key exchange mechanism (Curve25519 likely)
  - Random number generation (secrets module)
- [ ] Implement `anemochory/crypto.py`
  - Packet encryption/decryption
  - Ephemeral key generation
  - Signature verification (optional for node trust)
- [ ] **Security Review** (harold-security with Opus 4.6) ← MANDATORY
- [ ] Comprehensive crypto unit tests (harold-tester)

**Success Criteria**:
- harold-security approval (Opus 4.6 review)
- >90% test coverage on crypto module
- Bandit security scan passes
- MyPy strict type checking passes

### Week 4: Packet Format & Routing

**Tasks**:
- [ ] Design packet format specification (harold-planner)
  - Nested encryption layers (3-7 hops)
  - Instruction layer format
  - TTL and loop prevention
- [ ] Implement `anemochory/packet.py`
  - Packet creation/parsing
  - Layer encryption/decryption
  - Instruction embedding
- [ ] Implement `anemochory/routing.py`
  - Pseudo-random path generation
  - Hop selection algorithm
  - Path diversity enforcement
- [ ] Unit tests with edge cases (harold-tester)

**Success Criteria**:
- Packet format handles 3-7 hop routing
- No deterministic routing (randomness verified)
- Loop detection prevents network storms
- >85% test coverage

### Week 5-6: Node Implementation & Integration

**Tasks**:
- [ ] Implement `anemochory/node.py`
  - Node server (receives encrypted packets)
  - Packet forwarding logic
  - Hop instruction processing
  - Exit node functionality
- [ ] Network protocol selection (harold-researcher)
  - HTTP/HTTPS tunneling (likely)
  - DNS covert channel (optional)
  - ICMP covert channel (optional)
- [ ] Node discovery mechanism (harold-planner)
  - Bootstrap node list (simple MVP)
  - DHT-based discovery (post-MVP)
- [ ] Integration tests (harold-tester)
  - Multi-hop packet routing
  - Timing attack resistance testing
  - Traffic analysis resistance testing
- [ ] **Adversarial Testing** (harold-security) ← CRITICAL

**Success Criteria**:
- 3+ node network functional
- Multi-hop routing verified
- Timing attacks fail (>95% confidence)
- harold-security adversarial testing passes
- >80% integration test coverage

**harold-planner's Concern**: *"Timing attacks will be the hardest to defend against. We'll need traffic padding and jitter. Dark Harold expects this to fail initially."* 😐

---

## Phase 2: Scrubbing Engine Foundation (Weeks 7-10)

**Owner**: harold-implementer + harold-researcher  
**Status**: Pending Phase 1 completion

### Week 7: Core Framework

**Tasks**:
- [ ] Design adapter interface (harold-planner)
  - Abstract base class: `PlatformAdapter`
  - Task queue datastructures: `DeletionTask`, `DeletionResult`
  - Verification interface
- [ ] Implement `eraserhead/engine.py`
  - Task scheduler
  - Adapter registry
  - Progress tracking
- [ ] Implement `eraserhead/queue.py`
  - Priority queue for deletion tasks
  - Retry logic with exponential backoff
  - Rate limit compliance
- [ ] Implement `eraserhead/vault.py`
  - Fernet encryption for credentials
  - Key derivation (argon2id or scrypt)
  - **Security review** (harold-security)

**Success Criteria**:
- Adapter interface well-defined
- Task queue handles priorities and retries
- Credential vault passes security review
- >85% test coverage with mocks

### Week 8-9: Initial Platform Adapters

**Tasks**:
- [ ] **Research Phase** (harold-researcher)
  - Facebook Graph API authentication & deletion endpoints
  - Twitter API v2 authentication & deletion endpoints
  - Instagram Graph API authentication & deletion endpoints
  - Rate limits and ToS compliance per platform
- [ ] Implement `eraserhead/adapters/facebook.py`
  - OAuth2 authentication flow
  - Post deletion API calls
  - Deletion verification
- [ ] Implement `eraserhead/adapters/twitter.py`
  - OAuth 1.0a / OAuth 2.0 authentication
  - Tweet deletion API calls
  - Deletion verification
- [ ] Implement `eraserhead/adapters/instagram.py`
  - Instagram Graph API authentication
  - Media deletion API calls
  - Deletion verification
- [ ] **Integration with Anemochory** (harold-implementer)
  - Route all API calls through anonymization layer
  - Verify origin obfuscation works

**Success Criteria**:
- 3 platform adapters functional
- All adapter requests routed through Anemochory
- Deletion verification confirms success
- >80% adapter test coverage (with API mocks)

### Week 10: Verification & CLI

**Tasks**:
- [ ] Implement `eraserhead/verification.py`
  - Immediate verification (post-deletion)
  - Delayed verification (24h, 7d checks)
  - Screenshot/proof capture
- [ ] Implement `eraserhead/cli.py` (Typer-based)
  - `eraserhead auth <platform>` - Authenticate
  - `eraserhead delete <platform> <resource>` - Delete resource
  - `eraserhead list <platform>` - List deletable resources
  - `eraserhead verify <task-id>` - Verify deletion
  - `eraserhead status` - Show progress
- [ ] CLI integration tests (harold-tester)
- [ ] **User documentation** (harold-documenter)

**Success Criteria**:
- CLI is functional and usable
- Verification system confirms deletions
- Documentation is Internet Historian quality
- End-to-end integration tests pass

---

## Phase 3: Polish & Security Hardening (Weeks 11-13)

**Owner**: harold-security + harold-tester  
**Status**: Pending Phase 2 completion

### Week 11: Security Audit

**Tasks**:
- [ ] **Comprehensive security review** (harold-security with Opus 4.6)
  - Crypto implementation audit
  - Credential storage audit
  - API key handling audit
  - Network request audit (verify Anemochory integration)
- [ ] Vulnerability scanning (automated + manual)
  - Bandit findings review
  - Safety dependency scan
  - gitleaks secret scan
- [ ] Threat model validation (harold-security + harold-planner)
  - Review attack vectors from spec
  - Adversarial testing results analysis
  - Risk mitigation documentation

**Success Criteria**:
- Zero critical or high vulnerabilities unaddressed
- harold-security approval for MVP release
- Threat model documented with mitigations
- Security audit report published (docs/)

### Week 12: Testing & Coverage

**Tasks**:
- [ ] **Edge case testing** (harold-tester)
  - Network failures (timeouts, disconnects)
  - Rate limiting scenarios
  - Invalid credentials
  - API changes (mock outdated endpoints)
  - Partial deletion failures
- [ ] **Load testing** (harold-tester)
  - Bulk deletion operations (1000s of tasks)
  - Multi-platform concurrent scrubbing
  - Node network under load
- [ ] Coverage analysis (harold-tester + harold-implementer)
  - Identify untested branches
  - Add tests to reach >80% coverage
- [ ] **Failure mode documentation** (harold-documenter)

**Success Criteria**:
- >80% test coverage across all modules
- Edge case tests cover Dark Harold's nightmares
- Load testing validates performance requirements
- Failure modes documented for users

### Week 13: Documentation & Usability

**Tasks**:
- [ ] **README rewrite** (harold-documenter)
  - Installation guide
  - Quick start tutorial
  - Architecture overview
  - Security considerations
  - Limitations (Dark Harold's honesty)
- [ ] **API Documentation** (harold-documenter)
  - Comprehensive docstrings (Google style)
  - Adapter development guide
  - CLI reference
- [ ] **User guides** (harold-documenter)
  - "Your First Deletion" tutorial
  - Platform-specific guides (Facebook, Twitter, Instagram)
  - Troubleshooting (Dark Harold's "what will break")
- [ ] **Architecture Decision Records** (harold-planner)
  - Document all major design choices
  - Rationale for crypto primitives
  - Model routing decisions

**Success Criteria**:
- README is Internet Historian quality
- Documentation is comprehensive and narrative
- New contributors can add platform adapters
- Users can self-serve common issues

---

## Phase 4: MVP Release & Feedback (Week 14-16)

**Owner**: All Harolds  
**Status**: Pending Phase 3 completion

### Week 14: Pre-release Preparation

**Tasks**:
- [ ] **Final quality check** (all agents)
  - `./scripts/quality-check.sh` passes
  - Security scan clean
  - No secrets in code (gitleaks)
  - All tests pass
- [ ] **Release package preparation** (harold-implementer)
  - PyPI package configuration
  - Version tagging (v0.1.0-alpha)
  - CHANGELOG.md
- [ ] **License & legal review** (harold-planner + harold-security)
  - MIT license confirmed
  - ToS compliance documented
  - Legal disclaimers added

### Week 15-16: Alpha Release & Iteration

**Tasks**:
- [ ] **Alpha release** (GitHub + PyPI)
  - Tag v0.1.0-alpha
  - Publish package
  - Announcement (README + docs)
- [ ] **Community feedback collection** (harold-documenter)
  - GitHub issues monitoring
  - Platform adapter requests
  - Bug reports triage
- [ ] **Rapid iteration** (harold-implementer)
  - Critical bug fixes
  - Usability improvements
  - Documentation clarifications
- [ ] **Security monitoring** (harold-security)
  - Vulnerability reports monitoring
  - Dependency updates
  - Security advisory preparation

**Success Criteria**:
- Alpha release published and installable
- Zero critical security issues discovered
- Community feedback incorporated
- Roadmap for beta release (post-MVP features)

---

## Post-MVP Roadmap (Weeks 17+)

### Platform Expansion
- [ ] **Data broker adapters** (harold-researcher + harold-implementer)
  - Research data broker landscape
  - Implement 5+ data broker adapters
  - Monitoring system for re-aggregated data
- [ ] **Additional social platforms** (harold-implementer)
  - TikTok, LinkedIn, Reddit, Pinterest
  - User-requested platforms
- [ ] **Public records scrubbing** (harold-researcher)
  - Wayback Machine removal requests
  - Google cache flush
  - Search engine de-indexing

### Anemochory Enhancements
- [ ] **DHT-based node discovery** (harold-planner + harold-implementer)
  - Replace bootstrap node list with DHT
  - Dynamic node reputation system
- [ ] **Traffic padding & jitter** (harold-security)
  - Constant packet sizes
  - Timing decorrelation
  - Dummy traffic generation
- [ ] **Incentive layer** (harold-researcher + harold-planner)
  - Optional payment for node operators
  - Bandwidth proofs

### Usability
- [ ] **Web dashboard** (harold-implementer)
  - Visual progress tracking
  - Deletion history
  - Platform management
- [ ] **Scheduled scrubbing** (harold-implementer)
  - Recurring deletion tasks
  - Monitoring for re-aggregated data
- [ ] **Obfuscation mode** (harold-implementer + harold-security)
  - Replace data with noise before deletion
  - Profile randomization

### Security
- [ ] **External security audit** (harold-security coordination)
  - Professional crypto audit
  - Penetration testing
  - Public audit report
- [ ] **Bug bounty program** (harold-security)
  - Responsible disclosure policy
  - Vulnerability rewards

---

## Quality Standards & Enforcement

### Local Quality Gates (No Remote CI/CD)

All checks run locally via scripts:

```bash
# 😐 Harold's comprehensive quality check
./scripts/quality-check.sh

# Individual checks
./scripts/format.sh          # Ruff formatting
./scripts/lint.sh            # Ruff + mypy + pyright + bandit
./scripts/security-scan.sh   # gitleaks + bandit + safety
./scripts/test.sh            # pytest with coverage
```

**Pre-commit Requirements**:
- Ruff formatting passes (auto-fix enabled)
- Ruff linting passes (auto-fix enabled)
- MyPy type checking passes (strict mode)
- Bandit security scan passes
- Pytest tests pass (fast subset)

### Code Review Standards

**All code reviewed by appropriate Harold**:
- harold-implementer: Implementation quality, idiomatic Python
- harold-security: Security-sensitive code (crypto, auth, network)
- harold-tester: Test coverage, edge cases
- harold-documenter: Docstring quality, user-facing docs

### Test Coverage Requirements

- **Minimum**: 80% coverage (enforced)
- **Crypto/Security**: 95% coverage (harold-security requirement)
- **Adapters**: 85% coverage (with extensive mocks)
- **Integration**: 75% coverage (acceptable for complex workflows)

### Security Requirements

- **No secrets in code**: Enforced by gitleaks pre-commit hook
- **All crypto reviewed**: harold-security (Opus 4.6) reviews all crypto code
- **Dependency scanning**: Weekly safety + bandit scans
- **Type safety**: MyPy strict mode enforced

---

## Risk Management

### Harold's Risk Register

| Risk | Impact | Likelihood | Mitigation | Owner |
|------|--------|-----------|------------|-------|
| **Platform API changes break adapters** | High | Very High | Version adapters, monitor API changes, rapid updates | harold-implementer |
| **Timing attacks compromise Anemochory** | Critical | Medium | Traffic padding, jitter, extensive testing | harold-security |
| **Local models insufficient quality** | Medium | Low | Cloud fallback (Opus 4.6) for complex tasks | harold-planner |
| **Credential vault compromised** | Critical | Low | Argon2id key derivation, security audit | harold-security |
| **Legal action from platforms** | High | Medium | ToS compliance, user liability disclaimer | harold-planner |
| **Nation-state attacks** | Critical | Low | Document limitations, acknowledge no defense | harold-security |
| **User misuse for illegal activity** | High | Medium | Clear documentation, constitutional principles | harold-documenter |

### Contingency Plans

**If Anemochory timing attacks succeed**:
1. harold-security leads redesign of traffic padding
2. External crypto expert consultation
3. Delay MVP release until mitigated

**If platform adapters break frequently**:
1. harold-implementer builds API version detection
2. Automated adapter testing against live APIs (opt-in)
3. Community contributions for fixes

**If local models inadequate**:
1. Increase cloud fallback usage
2. Fine-tune local models on project codebase
3. Consider larger local models (14b+)

---

## Success Metrics

### MVP Success Criteria

**Functionality**:
- [ ] Anemochory protocol functional (3+ hop routing)
- [ ] 3+ platform adapters working (Facebook, Twitter, Instagram)
- [ ] Deletion verification system accurate (>95%)
- [ ] CLI usable for end-users

**Security**:
- [ ] harold-security approval (all crypto reviewed)
- [ ] Zero critical vulnerabilities at release
- [ ] Timing attacks fail in adversarial testing
- [ ] Credentials never leaked in testing

**Quality**:
- [ ] >80% test coverage maintained
- [ ] All quality checks pass (`./scripts/quality-check.sh`)
- [ ] External security audit scheduled (post-MVP)

**Documentation**:
- [ ] README is Internet Historian quality
- [ ] API documentation comprehensive
- [ ] User guides cover common use cases
- [ ] Limitations documented (Dark Harold's honesty)

### Post-MVP Success Metrics (6 months)

- 10+ platform adapters
- 5+ data broker adapters
- 100+ GitHub stars (community adoption)
- Zero critical security vulnerabilities discovered
- External security audit passed

---

## Dependencies & Prerequisites

### Required Infrastructure ✅

- [x] Python 3.14 environment
- [x] Qwen2.5-coder models (0.5b, 1.5b, 3b, 7b)
- [x] tinyclaw local inference configured
- [x] Comprehensive tooling (ruff, mypy, bandit, etc.)
- [x] Local quality control scripts

### External Dependencies

**Python Libraries** (pyproject.toml):
- cryptography (crypto primitives)
- httpx (async HTTP client)
- trio (structured concurrency)
- pydantic (data validation)
- typer (CLI framework)
- pytest + plugins (testing)

**Development Tools**:
- ruff (linting + formatting)
- mypy + pyright (type checking)
- bandit + safety (security scanning)
- gitleaks (secret scanning)
- vulture + radon + interrogate (code quality)

---

## Harold's Final Commentary

*"This development plan is either beautifully pragmatic or hopelessly optimistic. Harold suspects both. 😐"* — harold-planner

*"16 weeks to ship anonymization + scrubbing + agent architecture. Dark Harold gives it 20 weeks and several unforeseen disasters."* — harold-security

*"If we stick to the plan, test everything, and let harold-security be paranoid, we might actually ship something that doesn't immediately catch fire. Harold smiles nervously."* — harold-implementer

*"Documenting the plan is the easy part. Executing it while the ecosystem shifts under our feet? That's where the pain begins. But Harold has done harder things. Like smiling for stock photography."* — harold-documenter

---

## Next Immediate Actions

**Week 3 Kickoff** (Starting NOW):

1. **harold-researcher**: Research crypto primitives (ChaCha20-Poly1305 vs AES-GCM)
2. **harold-planner**: Design packet format specification (nested encryption layers)
3. **harold-security**: Begin threat model comprehensive review
4. **harold-implementer**: Set up `anemochory/` module structure
5. **harold-tester**: Design crypto test harness (property-based testing with Hypothesis?)
6. **harold-documenter**: Begin ADR drafting (crypto primitive selection)

**Daily Standup** (async via shared memory):
- What did you ship yesterday?
- What are you shipping today?
- What's blocking you?
- What did Dark Harold predict would break? (And did it?)

😐 **Harold ships with cautious optimism.**
