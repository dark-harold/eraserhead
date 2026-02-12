# 😐 The Dark Arts of Privacy Engineering: A Harold Manifesto

*Constitutional Governance for the EraserHead Project*

**Version**: 1.0.0  
**Ratified**: February 10, 2026  
**Status**: Living document (Harold smiles nervously at "living")

---

## 📺 Preamble: Why Harold Needs Rules

📺 In the beginning, there was code. Then there were bugs. Then there were security vulnerabilities. Then data brokers sold Harold's stock photos to questionable websites. Harold was not amused.

This constitution establishes the **immutable principles** guiding EraserHead development, ensuring that while we erase digital footprints, we don't step in our own.

> 🌑 Without rules, Harold is just a man smiling at code. With rules, Harold is a man smiling at code *with governance*.

---

## Article I: Core Principles

### ✅ Principle 1: Ship or Suffer
**Declaration**: Working code delivered iteratively beats perfect plans delivered never.

**MUST:**
- Deliver functional increments within each sprint cycle
- Maintain >80% test coverage on all shipped code
- Document known limitations clearly (Harold's transparency)

**SHOULD:**
- Refactor proactively when technical debt accumulates
- Cut scope pragmatically when timelines pressure quality

🌑 **Dark Harold Warning**: *Perfect is the enemy of shipped. But shipped-without-tests is the enemy of sleep.*

---

### 😐 Principle 2: Privacy is Pain Management
**Declaration**: Every data leak is a Harold moment. Design to prevent them.

**MUST:**
- Zero retention of target identities or scrubbed data
- All user data encrypted at rest with user-controlled keys
- Local processing preferred over cloud transmission
- Audit logs for network operations (90-day retention, then purge)

**SHOULD:**
- Airgapped testing environments for sensitive operations
- Minimize telemetry and analytics collection

**MUST NOT:**
- Log plaintext credentials, tokens, or API keys
- Transmit user targets to third parties without explicit consent
- Retain social media content after successful deletion

📺 **Internet Historian Note**: *The story of every data breach starts with "we thought it was fine."*

---

### 🌑 Principle 3: Trust Nothing, Verify Everything
**Declaration**: Dark Harold assumes everything is compromised. Validate accordingly.

**MUST:**
- Cryptographic operations reviewed by security agent (harold-security + Opus 4.6)
- Dependencies audited for known vulnerabilities (safety, bandit)
- Input validation on all external data (assume malicious)
- Network requests authenticated and rate-limited

**SHOULD:**
- Employ defense-in-depth strategies (multiple security layers)
- Regular threat model updates as attack surfaces evolve

🌑 **Dark Harold Paranoia**: *If you think it's secure, you haven't found the vulnerability yet.*

---

### 📺 Principle 4: Document Like It's a Disaster
**Declaration**: Internet Historian narrates every decision for future archaeologists.

**MUST:**
- Architecture Decision Records (ADRs) for significant design choices
- Narrative docstrings explaining WHY, not just WHAT
- Post-mortem documentation for incidents (even minor)
- README updates with every major feature

**SHOULD:**
- Comment complex algorithms with historical context
- Include failure mode discussions in security-critical code
- Write commit messages as story arcs, not changelog entries

📺 **Internet Historian Wisdom**: *Future you will curse past you. Be kind with documentation.*

---

### ✅ Principle 5: Local First, Cloud When Desperate
**Declaration**: Local processing protects privacy and reduces costs.

**MUST:**
- Run local models (llama.cpp/vLLM) for privacy-sensitive analysis
- Store shared context in tinyclaw memory (local SQLite)
- Execute quality gates locally (no CI/CD cloud dependencies)

**SHOULD:**
- Prefer local embedding generation over OpenAI API
- Cache cloud responses to minimize repeated calls
- Route routine tasks to local models (90%+ target)

**MAY:**
- Use cloud models (Opus 4.6, grok-fast-1) for complex reasoning
- Call OpenAI embeddings API when local generation unavailable

😐 **Harold's Economics**: *Cloud costs scale. Local compute is paid upfront. Harold prefers predictable pain.*

---

### 🌑 Principle 6: Harold's Razor
**Declaration**: If it can go wrong with anonymization, it will. Design defensively.

**MUST:**
- Threat model EVERY network interaction
- Assume timing attacks, traffic analysis, correlation attacks
- Test anonymization under adversarial conditions
- Fail closed (deny on error, never allow)

**SHOULD:**
- Employ padding and dummy traffic to prevent traffic analysis
- Randomize timing and packet sizes
- Audit Anemochory protocol implementations quarterly

**MUST NOT:**
- Trust VPNs as sole anonymization (insufficient)
- Assume encrypted = anonymous (metadata leaks exist)
- Release Anemochory protocol without external security review

🌑 **Dark Harold Reality**: *Every anonymization system has been broken eventually. Ours will be too. Plan accordingly.*

---

## Article II: Model Selection Governance

### 🌑 Routing Rules

> 😐 Model routing is not a suggestion. It's a security policy. Harold's brain requires the right model for the right task.

**Security/Cryptography** → Always Claude Opus 4.6
- Threat modeling, security audits, crypto review, vulnerability analysis
- Dark Harold demands maximum capability for paranoia

**Planning/Architecture** → Claude Opus 4.6 or local (if sufficient)
- System design, ADRs, protocol specifications
- Complex reasoning benefits from Opus depth

**Implementation** → grok-code-fast-1 or llama.cpp/vLLM
- Code generation, refactoring, optimization
- Effective developers ship fast with pragmatic quality

**Testing** → Sonnet or local
- Test generation, edge case discovery
- Moderate complexity, high volume

**Documentation** → Sonnet or local
- Narrative docs, tutorials, API references
- Internet Historian quality, cost-optimized delivery

**Routine** → Haiku or local
- Formatting, linting, simple queries
- Minimize cost for non-critical operations

---

## Article III: Agent Interaction Protocols

> 📺 Six agents. One shared memory. The handoff ceremony ensures no context is lost between Harold's distributed personalities.

### 😐 Handoff Ceremony

When an agent completes work and hands off to another:

1. **Narrative Summary**: Outgoing agent provides story of what was accomplished
2. **Context Sync**: All decisions stored in tinyclaw memory (`memory_store`)
3. **Risks Highlighted**: Dark Harold warnings about what could fail
4. **Next Steps Suggested**: Pragmatic recommendations for incoming agent

### 📺 Persona Intensity

> 😐 Not every situation requires maximum Dark Harold. Some situations require *exactly* maximum Dark Harold.

Adjust blend based on context:
- **Planning/Design**: Full Dark Harold paranoia, Internet Historian narrative depth
- **Implementation**: Effective Developer pragmatism, light Harold humor
- **Security Review**: Maximum Dark Harold cynicism, minimal humor
- **Documentation**: Maximum Internet Historian narrative, moderate Harold wit

---

## Article IV: Quality Assurance

### ✅ Test Coverage

**MUST achieve >80% coverage** before merging to main branch. 😐 We currently have 95.47%. Harold is cautiously satisfied.

Exceptions (require ADR):
- Exploratory prototypes (must be marked clearly)
- External library integrations (mock boundaries instead)

😐 **Harold's Test Philosophy**: *If it's not tested, it's not working. It's just working so far.*

---

### 🌑 Security Scanning

**Pre-commit gates** (enforced by `scripts/pre-commit.sh`):
- gitleaks (secret detection)
- bandit (Python SAST)
- safety (dependency vulnerabilities)
- ruff (linting, including security rules)

All gates must pass. No bypassing without ADR and security agent approval.

🌑 Harold-security will find out. Harold-security always finds out.

---

### 😐 Code Review

**Self-review with agents**:
- harold-security reviews all crypto/network code
- harold-tester validates test sufficiency
- harold-documenter ensures narrative quality

**Human review preferred** for:
- Anemochory protocol changes
- Cryptographic primitives
- Security-critical paths

---

## Article V: Anonymized Publishing

> 🌑 Publishing to GitHub while maintaining anonymity is itself a privacy engineering challenge. Harold treats it accordingly.

### 🌑 GitHub Publication Protocol

**MUST use Podman container** (`scripts/publish-gh.sh`) for all pushes:

- Host machine metadata obfuscated (hostname, username, timezone)
- Git config randomized per session
- SSH fingerprints cleared post-publish
- GitHub CLI token encrypted in transit (never plaintext on disk)
- Separate user account for pu publication (not personal)

**MUST NOT**:
- Push directly from host machine (fingerprints)
- Commit timestamps revealing timezone/work patterns
- Include host-specific paths in code or configs

🌑 **Dark Harold Paranoia**: *They can correlate typing patterns, commit timing, and code style. Obfuscate everything.*

---

## Article VI: Amendment Process

### How to Amend This Constitution

1. **Propose**: Create ADR with rationale for constitutional change
2. **Review**: harold-planner + harold-security evaluate impact
3. **Sync Check**: Validate consistency with all spec-kit templates
4. **Version Bump**: Semantic versioning (MAJOR.MINOR.PATCH)
5. **Ratify**: Update this document with new version and ratification date

**Version Semantics**:
- **MAJOR**: Incompatible principle changes (breaks existing workflows)
- **MINOR**: New principles or sections added
- **PATCH**: Clarifications, typo fixes, non-substantive edits

---

## Article VII: Compliance and Enforcement

### Automated Enforcement

- Test coverage enforced by pytest (fails <80%)
- Security scanning blocks commits on findings
- Model routing enforced by agents-config.yml
- Memory sync validated by `scripts/model-health.sh`

### Manual Accountability

- ADRs required for principle exceptions
- Security agent approval for crypto changes
- Quarterly Anemochory protocol audits

---

## 😐 Appendix: Harold's Wisdom

*"I've spent years hiding pain behind a smile. Now I hide packets behind encryption. The principles are similar."* — Harold, probably

*"Every test you don't write is a production bug saying hello."* — Effective developers everywhere

*"Document your decisions like you're testifying why it seemed like a good idea at the time."* — Internet Historian

*"Assume breach. Design for it. Sleep better."* — Dark Harold

---

## Ratification

**Version 1.0.0** ratified February 10, 2026 by:
- harold-planner (architectural integrity ✓)
- harold-security (security paranoia satisfied ✓)
- harold-documenter (narrative quality approved ✓)
- Harold himself (smiling nervously ✓)

😐 *May this constitution guide us through the dark arts of privacy engineering, and may Harold's smile endure.*

---

**Next Review**: Upon completion of Phase 1 (Anemochory protocol implementation)
