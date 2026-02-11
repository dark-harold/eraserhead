# ADR-005: Scrubbing Engine Architecture

**Status**: Accepted  
**Date**: 2026-02-11  
**Author**: harold-planner + harold-implementer  
**Supersedes**: None

---

## 📺 The Tale of Digital Footprint Erasure

In the beginning, there were social media accounts. Users posted, liked, commented, and shared. Then came the realization: every interaction was a permanent record, catalogued by platforms that profit from your data.

😐 Harold looked at his digital footprint and smiled nervously. It was enormous.

EraserHead's scrubbing engine exists to systematically dismantle that footprint — platform by platform, resource by resource — with verification that the deletion actually occurred.

🌑 Dark Harold reminds us: platforms have financial incentive to NOT delete your data. Trust nothing. Verify everything.

---

## Context

EraserHead needs the ability to:
1. Store platform credentials securely (never in plaintext)
2. Queue deletion tasks with priority ordering
3. Execute deletions across multiple platforms via a pluggable adapter system
4. Verify that deletions actually occurred
5. Handle rate limits, retries, and partial failures gracefully
6. Provide a CLI for human operators

---

## Decision

### Component Architecture

```
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│ CLI (Typer)  │────▶│ ScrubEngine  │────▶│ PlatformAdapter│
└─────────────┘     │              │     │ (ABC)          │
                    │  orchestrate │     ├───────────────┤
┌─────────────┐     │  dry-run     │     │ TwitterAdapter │
│CredentialVault│◀──│  progress    │     │ FacebookAdapter│
│ (Fernet)    │     └──────┬───────┘     │ InstagramAdapter│
└─────────────┘            │             └───────────────┘
                    ┌──────▼───────┐
                    │  TaskQueue   │     ┌───────────────┐
                    │  (priority)  │     │ Verification  │
                    │  (backoff)   │────▶│ Service       │
                    └──────────────┘     └───────────────┘
```

### Key Design Decisions

#### 1. Fernet Encryption for Vault (not GPG, not OS keychain directly)

**Chosen**: Fernet symmetric encryption (AES-128-CBC + HMAC-SHA256) with PBKDF2 key derivation (600k iterations).

**Rationale**:
- ✅ Pure Python — no OS-specific dependencies
- ✅ PBKDF2 iterations hardened against brute force
- ✅ Key never persisted — derived from passphrase at runtime
- 🌑 Trade-off: Fernet uses AES-128, not AES-256. Acceptable for credential storage timeline.

**Rejected alternatives**:
- OS keychain (platform-specific, breaks portability)
- GPG (heavyweight dependency, complex key management)
- NaCl secretbox (no built-in key derivation)

#### 2. Priority Queue with Exponential Backoff

**Chosen**: IntEnum priority (URGENT=1 through BACKGROUND=9), FIFO within same priority, exponential backoff with jitter on retry.

**Rationale**:
- ✅ Account deletion (URGENT) before old post cleanup (BACKGROUND)
- ✅ Backoff prevents rate-limit hammering (base 2s, max 300s)
- ✅ Jitter (±50%) prevents thundering herd on retry
- 😐 In-memory queue with JSON persistence — sufficient for single-user CLI

#### 3. Abstract Adapter Pattern

**Chosen**: `PlatformAdapter` ABC with template method pattern. Each platform implements `_do_authenticate`, `_do_delete`, `_do_verify`, `_do_list_resources`.

**Rationale**:
- ✅ New platforms added by subclassing only
- ✅ Rate limiting, stats, error handling in base class
- ✅ Token bucket rate limiter per adapter
- 🌑 Currently simulated — real API integration in Phase 4

#### 4. Post-Deletion Verification

**Chosen**: Separate `VerificationService` that re-queries adapters to confirm resources are gone.

**Rationale**:
- 🌑 Platforms can return HTTP 200 and not actually delete
- ✅ Batch scan for periodic re-verification
- ✅ REAPPEARED status detects soft-deleted content returning

#### 5. Trio for Async (not asyncio)

**Chosen**: Trio for all async operations.

**Rationale**:
- ✅ Structured concurrency prevents task leaks
- ✅ Consistent with Anemochory protocol layer
- ✅ Better cancellation semantics
- 😐 Smaller ecosystem, but purity wins

---

## Consequences

### Positive
- Clean separation of concerns — each component testable in isolation
- 493 tests at 92% coverage validates the architecture
- Dry-run mode enables safe experimentation
- CLI provides immediate value without a web UI

### Negative
- JSON queue persistence doesn't scale to millions of tasks (acceptable for v0.1.0)
- Simulated adapters — real API integration is Phase 4 work
- Single-user design — no multi-tenancy yet

### Risks
- 🌑 Platform API changes can break adapters silently
- 🌑 Rate limits vary by account tier — hardcoded values may be wrong
- 🌑 Verification timing: too soon after deletion → false positive (platform caching)

---

## References

- [specs/002-scrubbing-engine/spec.md](../../specs/002-scrubbing-engine/spec.md)
- [ADR-004: Master Key Storage](../004-master-key-storage/adr.md)
- EraserHead Constitution, Article I, Principle 6: Harold's Razor

---

😐 The engine is built. Now we wait for platforms to change their APIs and break everything.
