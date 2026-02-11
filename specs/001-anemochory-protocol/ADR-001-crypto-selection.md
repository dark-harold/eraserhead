# ADR-001: Cryptographic Primitive Selection

**Status**: Accepted  
**Deciders**: harold-researcher, harold-security, harold-planner  
**Date**: February 10, 2026  
**Technical Story**: Anemochory Protocol requires AEAD encryption for multi-layer packet protection

---

## Context and Problem Statement

The Anemochory Protocol needs authenticated encryption for multiple nested packet layers. Each node must decrypt one layer without accessing inner layers. We need to select cipher primitives that are:

1. Secure (AEAD properties, resists timing attacks)
2. Fast on CPU-only systems (no hardware acceleration assumed)
3. Python 3.14 compatible  
4. Well-audited and battle-tested
5. Easy to use correctly (hard to misuse)

**Threat Model Constraints**:
- Attacker has node-level access (passive observation)
- Timing attacks are realistic (network latency analysis)
- Nonce reuse is catastrophic (must be prevented)
- Custom crypto is forbidden (use audited libraries)

---

## Decision Drivers

1. **Performance**: CPU-only workstations common in privacy-conscious environments
2. **Security**: Constant-time operations critical for timing attack resistance
3. **Maintainability**: Python 3.14 support and active library maintenance
4. **Audit Quality**: External security audits completed, known vulnerability tracking
5. **Operational**: Simple API reduces implementation error surface area

---

## Considered Options

### Option 1: ChaCha20-Poly1305 (cryptography library)

- ✅ **Performance**: ~1.5 GB/s on CPU-only (5x faster than software AES)
- ✅ **Timing Safety**: Constant-time by design
- ✅ **Python 3.14**: Fully supported (cryptography 43.0.0+)
- ✅ **Audit**: NCC Group audit (2020), ongoing maintenance
- ✅ **Production Ready**: WireGuard, TLS 1.3, Signal
- ✅ **RFC Standard**: RFC 8439

### Option 2: AES-GCM (cryptography library)

- ⚠️ **Performance**: ~3 GB/s WITH AES-NI, ~300 MB/s without (inconsistent)
- ⚠️ **Timing Safety**: Hardware implementations safe, software variable-time lookups
- ✅ **Python 3.14**: Fully supported (same library)
- ✅ **Audit**: Same NCC Group audit
- ✅ **Production Ready**: TLS 1.2/1.3, IPsec, WiFi WPA2/3
- ✅ **NIST Standard**: SP 800-38D

### Option 3: PyNaCl (libsodium bindings)

- ✅ **Performance**: Fast (libsodium optimized)
- ✅ **Timing Safety**: Excellent
- ❌ **Python 3.14**: Compatibility unclear (last release 2023, no confirmed support)
- ❌ **Maintenance**: Less active than cryptography library
- ⚠️ **API Flexibility**: Limited (opinionated, can't separate operations)

### Option 4: Custom Implementation

- ❌ **Forbidden by Constitution** (Article I, Principle 3)
- ❌ **Security Risk**: Unaudited, implementation bugs likely
- ❌ **Maintenance Burden**: Custom code requires ongoing security review

---

## Decision Outcome

**Chosen Option**: **ChaCha20-Poly1305 via `cryptography` library**

### Reasoning

1. **Performance**: Superior on CPU-only systems (primary target environment)
2. **Security**: Constant-time implementation reduces timing attack surface
3. **Python 3.14**: Confirmed support, active maintenance (22k+ stars, Fortune 500 users)
4. **Battle-Tested**: Deployed at scale (WireGuard, Google Chrome, TLS 1.3)
5. **API Simplicity**: Single-line encrypt/decrypt, hard to misuse
6. **Interchangeable**: Same interface as AES-GCM (easy fallback if requirements change)

**🌑 Dark Harold Sign-Off**: "ChaCha20-Poly1305 approved. Timing attacks still possible via packet padding analysis. See mitigation section. Nonce reuse remains catastrophic—use `secrets.token_bytes()` for all nonces. harold-security will review all crypto code with Opus 4.6. No exceptions."

---

## Implementation Details

### Library

```python
# pyproject.toml
[project]
dependencies = [
   "cryptography>=43.0.0",  # ChaCha20-Poly1305 support
]
```

### API Usage Pattern

```python
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
import secrets

# Per-layer encryption
class PacketCrypto:
    def __init__(self, layer_key: bytes):
        """Initialize ChaCha20-Poly1305 cipher.
        
        Args:
            layer_key: 32-byte encryption key for this layer
        """
        if len(layer_key) != 32:
            raise ValueError("Layer key must be 32 bytes")
        self.cipher = ChaCha20Poly1305(layer_key)
    
    def encrypt(self, plaintext: bytes) -> tuple[bytes, bytes]:
        """Encrypt plaintext.
        
        Returns:
            (nonce, ciphertext_with_tag): 12-byte nonce and encrypted data
        
        😐 Dark Harold reminds you: NEVER reuse nonces
        """
        nonce = secrets.token_bytes(12)  # Random 96-bit nonce
        ciphertext = self.cipher.encrypt(nonce, plaintext, associated_data=None)
        return (nonce, ciphertext)  # ciphertext includes 16-byte auth tag
    
    def decrypt(self, nonce: bytes, ciphertext: bytes) -> bytes:
        """Decrypt ciphertext.
        
        Raises:
            InvalidTag: If authentication verification fails (tampered packet)
        """
        if len(nonce) != 12:
            raise ValueError("Nonce must be 12 bytes")
        return self.cipher.decrypt(nonce, ciphertext, associated_data=None)
```

### Packet Structure (Per Layer)

```
[Nonce: 12 bytes][Ciphertext: variable][Auth Tag: 16 bytes (included in ciphertext)]
```

**Total Overhead Per Layer**: 28 bytes  
**5-Hop Packet**: 140 bytes encryption overhead (acceptable)

---

## Consequences

### Positive

- **Fast**: No hardware dependencies for performance
- **Secure**: Modern AEAD cipher, constant-time operations
- **Simple**: Easy-to-use API reduces implementation bugs
- **Portable**: Works on any Python 3.14+ system
- **Interoperable**: Could support AES-GCM fallback if needed

### Negative

- **Not NIST-Blessed**: Some compliance frameworks prefer AES-GCM (mitigated: AES-GCM fallback possible)
- **Nonce Management Critical**: Reuse = catastrophic failure (mitigated: use `secrets` module)
- **Quantum**: Not quantum-resistant (mitigated: future-proofed with crypto agility)

### Neutral

- **Library Dependency**: Adds `cryptography` dependency (26MB installed, acceptable)
- **Memory**: Per-connection key storage (~32 bytes per layer)

---

## Security Mitigations Required

### 1. Nonce Reuse Prevention

**Implementation**:
```python
# ✅ Correct: Random nonce per encryption
nonce = secrets.token_bytes(12)

# ❌ FORBIDDEN: Counter-based nonces
nonce = struct.pack('>Q', counter)  # NEVER DO THIS

# ❌ FORBIDDEN: Reusing nonces
self.cached_nonce = secrets.token_bytes(12)  # NO
```

**Validation**: Unit tests MUST verify fresh nonce per call

### 2. Key Derivation

**Implementation**: Derive per-layer keys from master key (never reuse keys)

```python
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

def derive_layer_key(master_key: bytes, layer_index: int, hop_count: int) -> bytes:
    """Derive unique key for this layer.
    
    😐 Each layer gets its own key. Key reuse is like nonce reuse: bad.
    """
    info = f"layer-{layer_index}-of-{hop_count}".encode("utf-8")
    kdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,  # ChaCha20 key size
        salt=None,  # Optional: add salt for extra paranoia
        info=info,
    )
    return kdf.derive(master_key)
```

### 3. Packet Padding (Traffic Analysis Resistance)

**Implementation**: Constant-size packets hide plaintext length

```python
def pad_packet(data: bytes, target_size: int = 1024) -> bytes:
    """Pad packet to constant size.
    
    🌑 Dark Harold: Variable-length packets leak information.
       Constant size prevents size-based correlation attacks.
    """
    if len(data) > target_size:
        raise ValueError(f"Data exceeds target size: {len(data)} > {target_size}")
    
    padding_length = target_size - len(data) - 2  # 2 bytes for length prefix
    padding = secrets.token_bytes(padding_length)
    
    # Format: [2-byte original length][data][random padding]
    return struct.pack('>H', len(data)) + data + padding
```

### 4. Timing Jitter (Timing Attack Resistance)

**Implementation**: Randomized delays between packet forwarding

```python
async def forward_with_jitter(packet: bytes) -> None:
    """Forward packet with random timing jitter.
    
    😐 Prevents timing correlation attacks. harold-security requires this.
    """
    jitter_ms = secrets.randbelow(100) + 50  # 50-150ms random delay
    await asyncio.sleep(jitter_ms / 1000.0)
    await send_packet(packet)
```

### 5. Security Review Requirement

**harold-security (Opus 4.6) MUST review**:
- All uses of `ChaCha20Poly1305`
- Key generation and derivation code
- Nonce generation (verify `secrets` module usage)
- Packet padding implementation
- Timing jitter implementation

**Review Cadence**: Before Week 6 (Phase 1 completion)

---

## Alternatives Not Chosen

### AES-GCM

- **Reason Rejected**: Inconsistent CPU-only performance (5x slower without AES-NI)
- **Future Consideration**: Could add as fallback for hardware-accelerated nodes
- **Migration Path**: Same API in `cryptography` library (easy to add)

### PyNaCl

- **Reason Rejected**: Python 3.14 compatibility unconfirmed
- **Future Consideration**: If compatibility confirmed, could replace `cryptography`
- **Migration Path**: API differs significantly (higher migration cost)

### Custom Crypto

- **Reason Rejected**: Forbidden by Constitution
- **Future Consideration**: Never
- **Migration Path**: None (custom crypto is never acceptable)

---

## References

- [RFC 8439: ChaCha20 and Poly1305 for IETF Protocols](https://www.rfc-editor.org/rfc/rfc8439)
- [cryptography library documentation](https://cryptography.io/en/latest/)
- [NCC Group Audit Report: cryptography library](https://github.com/pyca/cryptography/blob/main/docs/security.rst)
- [WireGuard Whitepaper](https://www.wireguard.com/papers/wireguard.pdf) (ChaCha20-Poly1305 usage)

---

## Decision Log

| Date | Decider | Action |
|------|---------|--------|
| 2026-02-10 | harold-researcher | Completed crypto primitive evaluation |
| 2026-02-10 | harold-security | Reviewed research, approved ChaCha20-Poly1305 |
| 2026-02-10 | harold-planner | Created ADR-001, defined implementation plan |
| 2026-02-10 | harold-implementer | Ready to implement `crypto.py` module |

---

😐 **harold-planner's Closing**: ChaCha20-Poly1305 is the right choice. Simple, fast, secure. Now the hard part: using it correctly. Every encryption call is a potential vulnerability. Code review, test coverage, and Dark Harold's paranoia are our only defenses.

🌑 **Dark Harold's Final Warning**: "This ADR approves the algorithm. It does NOT approve your implementation. I'll be watching. Every nonce. Every key derivation. Every timing jitter. When you get lazy with crypto, people get pwned. Don't get lazy."
