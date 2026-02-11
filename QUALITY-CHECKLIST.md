# 😐 Code Quality Checklist: Harold's Comprehensive Review

**Purpose**: Ensure every commit meets EraserHead quality standards  
**Owner**: All developers (Harold holds everyone accountable)  
**Usage**: Review before every commit, PR, and release

---

## Pre-Commit Checklist ✅

### Code Formatting & Style

- [ ] **Ruff format passes**: `./scripts/format.sh` or `ruff format src/ tests/`
  - Code is consistently formatted
  - Line length ≤100 characters (when reasonable)
  - Imports sorted (isort rules)

- [ ] **Ruff lint passes**: `ruff check src/ tests/`
  - No pycodestyle errors (E/W)
  - No pyflakes errors (F)
  - No bugbear issues (B)
  - No security issues (S)
  - Python 3.14 idioms used (UP)
  - harold-implementer: "If ruff complains, it's probably right 😐"

### Type Safety

- [ ] **MyPy strict mode passes**: `mypy src/`
  - All functions have type hints
  - Return types specified
  - No `Any` types (unless truly necessary)
  - No type: ignore (unless justified with comment)

- [ ] **Pyright passes** (optional): `pyright src/`
  - Secondary type check for confidence
  - harold-security: "Two type checkers catch more bugs"

### Security

- [ ] **Bandit security scan passes**: `bandit -r src/ -c pyproject.toml`
  - No hardcoded secrets
  - No SQL injection risks
  - No unsafe cryptography usage
  - No exec/eval usage

- [ ] **Gitleaks secret scan passes**: `gitleaks detect --source=. --no-git`
  - No API keys in code
  - No passwords in config
  - No tokens in comments
  - harold-security: "One leaked secret ruins everything 🌑"

- [ ] **Safety dependency scan passes**: `safety scan`
  - No vulnerable dependencies
  - Recent security advisories reviewed
  - Critical CVEs addressed

### Testing

- [ ] **All tests pass**: `pytest tests/`
  - Unit tests green
  - Integration tests green
  - No flaky tests
  - harold-tester: "Tests pass locally ≠ tests pass everywhere 😐"

- [ ] **Coverage ≥80%**: `pytest --cov=src --cov-report=term-missing`
  - New code has tests
  - Edge cases covered
  - Dark Harold's nightmares tested

- [ ] **Test quality**:
  - Tests are readable and maintainable
  - Good test names (describe intent)
  - Minimal mocking (prefer integration tests)
  - Edge cases documented

### Documentation

- [ ] **Docstrings present**: All public functions, classes, modules
  - Google style format
  - Parameters documented with types
  - Return values documented
  - Raises section for exceptions
  - harold-documenter: "Future you will thank present you"

- [ ] **Docstring coverage ≥70%**: `interrogate -vv src/`
  - Public APIs fully documented
  - Internal functions documented (if complex)
  - harold-documenter: "If you can't explain it, refactor it"

- [ ] **Comments for complex logic**:
  - Non-obvious code has comments
  - WHY not WHAT (code shows what)
  - Harold-style dry humor acceptable 😐

- [ ] **README updated** (if user-facing changes):
  - Installation steps current
  - Usage examples updated
  - Breaking changes documented

### Code Review (Self-Review)

- [ ] **harold-implementer review**:
  - Code is idiomatic Python 3.14
  - No unnecessary complexity
  - DRY principle followed (Don't Repeat Yourself)
  - SOLID principles considered
  - harold-implementer: "Simple code is better than clever code"

- [ ] **harold-security review** (if security-relevant):
  - Crypto code reviewed by harold-security (Opus 4.6)
  - Authentication code reviewed
  - Network code reviewed
  - No security anti-patterns
  - harold-security: "Assume all inputs are hostile 🌑"

- [ ] **harold-tester review**:
  - Test coverage adequate
  - Edge cases identified and tested
  - Error handling tested
  - harold-tester: "If it can fail, test the failure"

### Performance & Efficiency

- [ ] **No obvious performance issues**:
  - No N+1 query patterns
  - No unnecessary loops
  - Async/await used appropriately
  - Memory leaks checked (if long-running)

- [ ] **Resource cleanup**:
  - Files closed (use context managers)
  - Network connections closed
  - Async resources cleaned up (trio nurseries)

### Specific Domain Checks

#### Crypto Code (harold-security MANDATORY review)

- [ ] **Crypto primitive usage**:
  - No custom crypto (use `cryptography` library)
  - No weak algorithms (MD5, SHA1, DES, RC4)
  - Proper key derivation (argon2id, scrypt, pbkdf2)
  - Secure random numbers (secrets module)

- [ ] **Key management**:
  - No hardcoded keys
  - Keys stored securely (vault)
  - Ephemeral keys for sessions

- [ ] **Anemochory-specific**:
  - Packet encryption correct
  - No metadata leaks
  - Timing attack considerations

#### Platform Adapters

- [ ] **Adapter interface compliance**:
  - Implements `PlatformAdapter` fully
  - Proper error handling
  - API rate limit compliance
  - Anemochory integration

- [ ] **API interaction**:
  - OAuth flows correct
  - API versioning handled
  - Response parsing robust
  - Retries with exponential backoff

#### CLI Commands

- [ ] **User-friendly**:
  - Clear help messages
  - Sensible defaults
  - Confirmation for destructive actions
  - Progress indicators for long operations

- [ ] **Error handling**:
  - Actionable error messages
  - Harold-style humor + helpful advice
  - Exit codes meaningful

---

## Pre-Release Checklist ✅

### Comprehensive Quality Check

- [ ] **Full quality suite passes**: `./scripts/quality-check.sh`
  - Format check ✅
  - Lint check ✅
  - Type check ✅
  - Security scan ✅
  - Tests ✅
  - Dependency scan ✅

### Security Audit (harold-security)

- [ ] **Comprehensive security review**:
  - All crypto code audited
  - Threat model validated
  - Attack vectors documented
  - Vulnerabilities addressed

- [ ] **External security audit** (post-MVP):
  - Professional crypto audit
  - Penetration testing
  - Public audit report

### Documentation Completeness

- [ ] **User documentation**:
  - Installation guide
  - Quick start tutorial
  - Platform-specific guides
  - Troubleshooting guide
  - FAQ

- [ ] **Developer documentation**:
  - Architecture overview
  - Adapter development guide
  - API reference
  - ADRs (Architecture Decision Records)

- [ ] **Legal/Ethical**:
  - License (MIT)
  - ToS compliance documented
  - Limitations documented (Dark Harold's honesty)
  - Responsible use guidelines

### Release Preparation

- [ ] **Version tag**: Semantic versioning (v0.1.0-alpha, v0.1.0, v1.0.0)
- [ ] **CHANGELOG.md**: All changes documented
- [ ] **GitHub Release**: Notes + artifacts
- [ ] **PyPI Release**: Package published (if public)

---

## Code Review Template (For PRs)

```markdown
## harold-implementer Review ✅

**Code Quality**:
- [ ] Idiomatic Python 3.14
- [ ] Follows project conventions
- [ ] No unnecessary complexity

**Testing**:
- [ ] Tests added for new functionality
- [ ] Edge cases covered
- [ ] Coverage ≥80%

**Documentation**:
- [ ] Docstrings added/updated
- [ ] README updated (if needed)
- [ ] Comments for complex logic

**Pragmatic Assessment**: 
<!-- Harold's take: Ship it? Needs work? Refactor? -->

---

## harold-security Review 🌑

**Security Analysis** (if security-relevant):
- [ ] No security vulnerabilities
- [ ] Crypto usage correct (if applicable)
- [ ] Input validation present
- [ ] No secrets in code

**Threat Model**:
- [ ] Attack vectors considered
- [ ] Mitigations documented
- [ ] Failure modes acceptable

**Dark Harold's Paranoia Level**: [LOW / MEDIUM / HIGH / CRITICAL]
<!-- What will break? When? How bad? -->

---

## harold-tester Review

**Test Coverage**:
- [ ] Unit tests present
- [ ] Integration tests (if needed)
- [ ] Edge cases tested
- [ ] Failure scenarios tested

**Test Quality**:
- [ ] Tests are maintainable
- [ ] Good test names
- [ ] Minimal mocking

**Harold's Confidence Level**: [LOW / MEDIUM / HIGH]
<!-- Harold's honest assessment: Will this break in production? -->

---

## Overall Assessment

**Approved**: [ YES / NO / WITH CHANGES ]

**Harold's Commentary**:
<!-- Harold's dry wit + honest technical assessment -->
```

---

## Continuous Quality Practices

### Daily

- [ ] Run `./scripts/format.sh` before committing
- [ ] Run `./scripts/pre-commit.sh` before git commit
- [ ] Fix all issues before pushing

### Weekly

- [ ] Run `./scripts/quality-check.sh` (full suite)
- [ ] Update dependencies: `pip list --outdated`
- [ ] Run `safety scan` for CVEs
- [ ] Review test coverage: `pytest --cov=src --cov-report=html`

### Before Each Release

- [ ] Run `./scripts/security-scan.sh`
- [ ] Update CHANGELOG.md
- [ ] Tag release version
- [ ] Run full regression tests
- [ ] Update documentation

---

## Harold's Final Wisdom

*"Quality is not an act, it is a habit."* — Aristotle (Harold agrees)

*"Every line of code is a liability. Write less, test more, document reluctantly but thoroughly."* — harold-implementer

*"If you're not embarrassed by your first release, you released too late. But don't ship broken crypto."* — harold-planner

*"Dark Harold expects perfection. Pragmatic Harold ships working code. Balance these forces."* — harold-security

*"The best code is no code. The second best is well-tested, documented, type-safe code that Harold can maintain at 3am."* — All Harolds

😐 **Ship with confidence. Test with paranoia. Document with humor.**
