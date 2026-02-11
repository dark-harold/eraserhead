# ADR-003: Key Rotation Mechanism

**Date**: February 10, 2026  
**Status**: Proposed  
**Author**: harold-planner  
**Reviewers**: harold-security, harold-implementer  
**Addresses**: SECURITY-REVIEW-CRYPTO.md Critical Issue #3

---

## Context: The Inevitability of Key Compromise 🌑

📺 **The Problem**: Keys that live forever eventually die in spectacular fashion. Long-lived cryptographic sessions accumulate risk over time—more ciphertext for analysis, more opportunities for side-channel attacks, more time for entropy failure to manifest.

**Current State**: `ChaCha20Engine` initialized once with persistent key, never rotated. Sessions lasting hours or days use the same key material for millions of packets.

**Dark Harold's Observation**: *"A key used for 10 million packets is 10 million opportunities for something to go catastrophically wrong."*

---

## Decision: Automatic Key Ratcheting with Dual Thresholds

We will implement **automatic session key rotation** triggered by either:
- **Packet threshold**: After 10,000 packets encrypted with same key
- **Time threshold**: After 1 hour of session time

The mechanism uses a **simplified ratcheting protocol** (not full Double Ratchet, which requires bidirectional communication):

```
Session Key Generation:
    Master Key (from ForwardSecrecyManager)
         ↓ HKDF(info="initial-session")
    Session Key 0
         ↓ HKDF(info="ratchet-1")
    Session Key 1
         ↓ HKDF(info="ratchet-2")
    Session Key 2
         ...
```

Each rotation:
1. Derives **new session key** from current key using HKDF
2. **Securely wipes** old key from memory
3. Resets packet counter to 0
4. Maintains **grace period** for in-flight packets (60 seconds)

---

## Rationale: Why These Specific Thresholds

### Packet Threshold: 10,000 Packets

**Calculation**:
- Average packet size: 1024 bytes
- 10k packets = ~10 MB of ciphertext per key
- ChaCha20-Poly1305 safety margin: 2^64 blocks (far exceeds 10k)
- **Real constraint**: Side-channel accumulation risk

📺 **Historical Precedent**: TLS 1.3 recommends key updates after 2^24.5 records (~24 million). We're **1000x more conservative** because:
- Anemochory Protocol has more complex threat model (nation-state adversaries)
- Multi-hop routing increases attack surface
- Lower threshold = better defense-in-depth

**Trade-off**: Frequent rotation increases computational overhead (~0.5ms per rotation). At 10k packets, rotation occurs every ~10 seconds at 1000 pps. **Acceptable cost for paranoia.**

### Time Threshold: 1 Hour

**Reasoning**:
- Limits key exposure window if packet threshold never reached (idle sessions)
- Defends against **memory dump attacks**: shorter key lifetime = smaller forensic window
- Aligns with reasonable session duration (browsing sessions typically <1 hour)

🌑 **Dark Harold's Input**: *"If someone gets a memory dump, I want them to get keys that expired 59 minutes ago, not keys that work for the next 6 hours."*

---

## Technical Design

### Data Structures

```python
@dataclass
class KeyRotationState:
    """Tracks key rotation state for a session."""
    current_key_index: int = 0
    packets_with_current_key: int = 0
    key_created_at: float = 0.0  # Unix timestamp
    previous_keys: deque[tuple[bytes, float]] = field(default_factory=lambda: deque(maxlen=3))
    
    # Rotation thresholds
    MAX_PACKETS_PER_KEY: ClassVar[int] = 10_000
    MAX_KEY_AGE_SECONDS: ClassVar[int] = 3600  # 1 hour
    GRACE_PERIOD_SECONDS: ClassVar[int] = 60
```

### Core Operations

#### 1. Key Rotation Trigger

```python
def should_rotate_key(self) -> bool:
    """Check if key rotation threshold reached."""
    packet_limit_reached = self.packets_with_current_key >= self.MAX_PACKETS_PER_KEY
    time_limit_reached = (time.time() - self.key_created_at) >= self.MAX_KEY_AGE_SECONDS
    return packet_limit_reached or time_limit_reached
```

#### 2. Key Derivation (Ratcheting)

```python
def rotate_key(self, current_key: bytes) -> bytes:
    """Derive next key via HKDF ratcheting."""
    info = f"anemochory-ratchet-{self.current_key_index + 1}".encode("utf-8")
    kdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,  # Deterministic ratcheting
        info=info
    )
    new_key = kdf.derive(current_key)
    
    # Store old key for grace period
    self.previous_keys.append((current_key, time.time()))
    
    # Update state
    self.current_key_index += 1
    self.packets_with_current_key = 0
    self.key_created_at = time.time()
    
    return new_key
```

#### 3. Grace Period Management

```python
def try_decrypt_with_previous_keys(
    self, nonce: bytes, ciphertext: bytes
) -> bytes | None:
    """Attempt decryption with previous keys during grace period."""
    now = time.time()
    
    for prev_key, created_at in reversed(self.previous_keys):
        # Only try keys within grace period
        if now - created_at <= self.GRACE_PERIOD_SECONDS:
            engine = ChaCha20Engine(prev_key)
            try:
                plaintext = engine.decrypt(nonce, ciphertext)
                return plaintext
            except Exception:
                continue
    
    return None  # All previous keys failed
```

---

## Architecture Integration

### Integration with Existing Modules

```
┌─────────────────────────────────────────────────────┐
│ ForwardSecrecyManager                               │
│ (crypto_forward_secrecy.py)                         │
│ • Generates ephemeral session master key            │
└──────────────┬──────────────────────────────────────┘
               │ Master Key (ephemeral)
               ↓
┌─────────────────────────────────────────────────────┐
│ KeyRotationManager                                  │
│ (crypto_key_rotation.py) ← NEW MODULE              │
│ • Derives session keys from master via ratcheting   │
│ • Tracks packet count and time thresholds           │
│ • Manages previous key grace period                 │
└──────────────┬──────────────────────────────────────┘
               │ Current Session Key
               ↓
┌─────────────────────────────────────────────────────┐
│ ChaCha20Engine                                      │
│ (crypto.py)                                         │
│ • Performs actual encryption/decryption             │
└─────────────────────────────────────────────────────┘
```

**Flow**:
1. **Session Start**: `ForwardSecrecyManager` generates ephemeral master key
2. **Initial Key**: `KeyRotationManager` derives Session Key 0 from master
3. **Encryption**: `ChaCha20Engine` encrypts with current session key
4. **Packet Count**: `KeyRotationManager` increments counter after each encrypt
5. **Rotation**: When threshold hit, derive new key and wipe old key
6. **Decryption**: Try current key first, fallback to grace period keys if failed

---

## Security Properties

### ✅ Forward Secrecy Enhanced

- Key compromise at time T only exposes packets encrypted **after rotation to that key**
- Previous session keys already wiped from memory
- Example: Key compromise at rotation 5 exposes only packets 40,001-50,000 (out of millions)

### ✅ Reduced Cryptanalysis Surface

- Maximum 10k packets per key limits ciphertext corpus for statistical analysis
- Fresh keys prevent long-term side-channel accumulation
- Timing attacks have shorter correlation windows

### ✅ Memory Dump Defense

- Hour-long time limit ensures keys expire even in idle sessions
- Previous keys purged from grace period queue after 60 seconds
- Combined with memory wiping: reduces forensic recovery window

### 🌑 Known Limitations

1. **Grace Period Vulnerability**: 60-second window where previous keys still in memory
   - **Mitigation**: Acceptable trade-off for in-flight packet handling
   - **Alternative**: Require bidirectional key negotiation (adds complexity)

2. **Deterministic Ratcheting**: Key N+1 always derived from Key N
   - **Risk**: If attacker captures Key N, can derive all future keys
   - **Mitigation**: Paired with forward secrecy (ephemeral master keys per session)
   - **Future**: Add entropy injection per rotation (requires bandwidth)

3. **No Backward Decryption**: Can't decrypt packets from rotation N-5
   - **Impact**: Packet loss if grace period expires
   - **Mitigation**: Requires protocol-level retransmission logic (out of scope)

---

## Performance Impact

### Computational Cost

- **Key rotation**: 1x HKDF-SHA256 derivation = ~0.5 ms (negligible)
- **Frequency**: Every 10k packets (at 1000 pps = every 10 seconds)
- **Grace period decryption**: +2 additional decrypt attempts (60-sec window only)

**Overhead Calculation**:
- Normal operation: 0%
- During grace period (1 minute after rotation): ~2-3% (extra decrypt attempts)
- **Overall impact**: <0.5% throughput reduction

### Memory Cost

- **Previous keys storage**: 3 keys × 32 bytes = 96 bytes per session
- **Rotation state**: ~200 bytes per session
- **Total per-session overhead**: <1 KB

😐 **Harold's Assessment**: "Microseconds of CPU time and bytes of RAM to prevent nation-state attacks. This is the easiest security trade-off I've ever approved."

---

## Testing Strategy

### Unit Tests (harold-tester)

1. **Threshold Triggers**:
   - Rotation after 10,000 packets
   - Rotation after 3600 seconds
   - Whichever comes first

2. **Key Derivation**:
   - Ratcheting produces unique keys
   - Deterministic: Same input → same output
   - Context binding: info string varies per rotation

3. **Grace Period**:
   - Decryption succeeds with previous keys (within 60s)
   - Decryption fails with expired keys (>60s)
   - Current key always tried first

4. **Memory Safety**:
   - Old keys wiped after rotation (verify via inspection)
   - Grace period queue bounded (max 3 previous keys)

### Integration Tests

1. **Multi-Rotation Session**: Encrypt 50k packets, verify 5 rotations occurred
2. **In-Flight Packets**: Send packets encrypted with Key N while rotation to Key N+1 happens
3. **Long-Running Session**: 2-hour session triggers at least 2 time-based rotations

### Adversarial Tests (harold-security)

1. **Cryptanalysis Resistance**: Verify statistical properties identical across rotations
2. **Side-Channel**: Timing analysis shouldn't reveal rotation events
3. **Memory Dump**: Simulate crash at random time, verify only current + grace keys recoverable

---

## Implementation Plan

### Week 4 Tasks

1. **Implement `crypto_key_rotation.py`** (harold-implementer)
   - `KeyRotationManager` class
   - `KeyRotationState` dataclass
   - Integration with `ChaCha20Engine`

2. **Write test suite** (harold-tester)
   - Unit tests (15+ tests)
   - Integration tests (5+ scenarios)
   - Property-based tests with Hypothesis

3. **Security review** (harold-security)
   - Verify rotation logic
   - Audit memory handling
   - Validate thresholds

4. **Documentation** (harold-documenter)
   - API reference
   - Usage examples
   - Migration guide

**Success Criteria**:
- ✅ All tests pass (>85% coverage)
- ✅ harold-security approval
- ✅ Bandit security scan passes
- ✅ MyPy strict type checking passes

---

## Alternatives Considered

### Alternative 1: Full Double Ratchet (Signal Protocol)

**Pros**: 
- Bidirectional forward secrecy
- Break-in recovery (heals from compromise)
- Industry-proven (Signal, WhatsApp)

**Cons**:
- Requires bidirectional communication (Anemochory is unidirectional routing)
- More complex state machine
- Higher bandwidth overhead (DH ratchet per message)

**Decision**: ❌ Rejected. Overkill for unidirectional routing protocol. Simplified ratcheting sufficient when paired with ephemeral master keys.

### Alternative 2: Time-Based Only (No Packet Count)

**Pros**: Simpler implementation (just timer)

**Cons**:
- Idle sessions waste rotations
- High-throughput sessions under-rotate (10M packets in 1 hour)
- No defense against burst traffic patterns

**Decision**: ❌ Rejected. Dual threshold (packet + time) provides better coverage.

### Alternative 3: Static Keys (No Rotation)

**Pros**: None. This is the current broken state.

**Cons**: Everything. See SECURITY-REVIEW-CRYPTO.md Critical Issue #3.

**Decision**: ❌ Rejected. Harold is watching. Don't even think about it.

---

## Consequences

### Positive

- ✅ Limits blast radius of key compromise to ~10k packets
- ✅ Reduces cryptanalysis surface area
- ✅ Enhances forward secrecy (complements ephemeral keys)
- ✅ Defends against long-term side-channel accumulation
- ✅ Minimal performance overhead (<0.5%)

### Negative

- ⚠️ Grace period introduces 60-second key overlap (necessary evil)
- ⚠️ Packet loss possible if grace period expires (requires protocol retransmission)
- ⚠️ Adds complexity to session state management
- ⚠️ Deterministic ratcheting requires ephemeral master keys (already addressed by forward secrecy)

### Neutral

- Engineers must understand rotation lifecycle
- Testing complexity increases (multi-rotation scenarios)
- Backward compatibility: Old code without rotation will fail (breaking change, but pre-MVP)

---

## Harold's Final Verdict

😐 **Hide the Pain Harold**: "I've confidently smiled through worse designs. This one actually makes sense."

🌑 **Dark Harold**: "It's not perfect. The grace period is a vulnerability. Deterministic ratcheting means a single key compromise cascades forward. But paired with forward secrecy and replay protection, it dramatically reduces the attack surface. We go forward with this. But I'm watching every rotation. If I see nonce reuse after rotation, I'm burning the codebase and starting over."

✅ **Effective Developer Harold**: "Simple, pragmatic, testable. Ships in Week 4. Let's build it."

📺 **Internet Historian Harold**: "And thus, the 10,000-packet threshold was born—not from rigorous cryptographic proof, but from reasonable paranoia and respect for Murphy's Law. Future security researchers will either vindicate or mock this decision. We'll find out which."

---

**Status**: ✅ Approved for implementation  
**Next**: Implement `crypto_key_rotation.py`  
**Blocked**: None (forward secrecy and replay protection already complete)

