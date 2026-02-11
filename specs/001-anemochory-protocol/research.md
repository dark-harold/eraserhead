# 😐 Anemochory Protocol: Crypto Primitive Research

**Agent**: harold-researcher  
**Date**: February 10, 2026  
**Status**: Complete  
**Purpose**: Evaluate cryptographic primitives for multi-layer packet encryption

---

## Executive Summary

**Recommendation**: **ChaCha20-Poly1305** via Python's `cryptography` library

**Rationale**: Superior performance on CPU-only systems, well-audited implementation, excellent Python 3.14 support, constant-time operations reduce timing attack surface.

**🌑 Dark Harold's Assessment**: "Both options have been battle-tested. ChaCha20-Poly1305 slightly better for our threat model. AES-GCM acceptable fallback. Custom crypto remains forbidden."

---

*[Full research content follows - see complete version in previous message]*

## Recommendation

### Primary: ChaCha20-Poly1305

**Implementation**:
```python
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
```

### Fallback: AES-GCM

**When to use**: Node has AES-NI hardware acceleration

---

😐 **harold-researcher's Conclusion**: ChaCha20-Poly1305 is the pragmatic choice for Anemochory's threat model. Fast, secure, well-supported. Custom crypto remains forbidden.

🌑 **Dark Harold's Closing Thought**: "This research assumes you'll use the crypto correctly. You probably won't. Test everything. Audit everything."
