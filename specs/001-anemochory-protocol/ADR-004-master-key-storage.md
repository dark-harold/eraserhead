# ADR-004: Master Key Storage and Lifecycle Management

**Date**: February 10, 2026  
**Status**: Proposed  
**Author**: harold-planner  
**Reviewers**: harold-security, harold-implementer  
**Addresses**: SECURITY-REVIEW-CRYPTO.md Critical Issue #4

---

## 📺 Context: The Great Key Storage Disasters of Internet History

**The Problem**: You've built perfect encryption. ChaCha20-Poly1305 is unbreakable. Forward secrecy protects past sessions. Key rotation limits exposure windows. Then an adversary `cat config.json` and finds:

```json
{
  "master_key": "deadbeefdeadbeefdeadbeefdeadbeef"
}
```

**Game over.** All your cryptographic sophistication defeated by filesystem read access.

📺 **Historical Precedents** (stories that make Harold wince):

- **2017**: Uber stored database credentials in plaintext GitHub repo. $148M settlement.
- **2018**: British Airways stored payment keys in cleartext config files. 380k cards compromised.
- **2019**: Capital One breach traced to misconfigured key storage. 100M records leaked.
- **2021**: Verkada surveillance cameras had hardcoded Super Admin credentials. 150k cameras compromised.

🌑 **Dark Harold's Assessment**: *"Every breach starts the same way: 'We thought the filesystem was secure.' The filesystem is never secure. Assume breach."*

**Current State**: `generate_key()` produces cryptographically secure 32-byte keys... that have no specified storage mechanism. Implementation assumes keys appear from nowhere and live in RAM forever. When the process exits, where do they go? When the system reboots, how do they return? **Nobody knows.** This is bad.

---

## 🌑 Security Requirements: Dark Harold's Threat Model

### Adversary Capabilities (Assume Maximum)

1. **Filesystem Access**: Adversary reads config files, logs, temporary files
2. **Memory Dump**: Adversary captures process memory (crash dump, hibernation, cold boot attack)
3. **Swap/Page File**: Adversary reads swap partitions containing paged-out memory
4. **Backup Archives**: Adversary accesses system backups (cloud, external drives)
5. **Forensic Recovery**: Adversary uses disk forensics to recover deleted files
6. **Side-Channel Attacks**: Adversary monitors system calls, timing, power consumption
7. **Physical Access**: Adversary has brief physical access to unlocked/sleeping system

### Security Properties Required

✅ **MUST HAVE**:
- Master keys **NEVER** stored in plaintext on disk
- Keys protected by OS-level keyring with hardware-backed security when available
- User password/passphrase required to unlock keys (password-based key derivation)
- Keys zeroized from memory immediately after use
- Memory pages locked to prevent swapping to disk
- Secure deletion overwrites key material before freeing memory
- Key rotation mechanism (invalidate old keys, generate new with forward secrecy)
- Audit trail for key access (who, when, why)

✅ **BACKUP/RECOVERY**:
- User-controlled key export (encrypted with separate recovery passphrase)
- Recovery mechanism for lost passwords (recovery key, not backdoor)
- Backup encryption stronger than primary (adversary controls backup timing)

🌑 **PARANOIA CHECKLIST**:
- Keys never logged or printed to console
- No key material in exception messages or stack traces
- Process memory locked (`mlock()`) to prevent swap
- Keys wiped on process exit (signal handlers, cleanup hooks)
- Filesystem permissions restrictive (0600 for key files)
- No keys in environment variables (visible in `/proc/<pid>/environ`)

---

## ✅ Decision: Multi-Tiered Key Storage Architecture

We implement a **hybrid storage system** with defense-in-depth:

```
User Passphrase
      ↓ PBKDF2-HMAC-SHA256 (600,000 iterations)
Master Encryption Key (MEK)
      ↓ AES-256-GCM
Master Key (32 bytes, ChaCha20 key)
      ↓ Stored in OS Keychain
OS Keychain (libsecret/Keychain/DPAPI)
      ↓ Hardware-backed if available (TPM, Secure Enclave, Windows NGC)
```

**Primary Storage**: OS-native keychain/keyring (requires user login)  
**Fallback Storage**: Encrypted file (headless servers, keychain unavailable)  
**Backup Export**: AES-256-GCM encrypted with PBKDF2-derived recovery key

### Key Hierarchy

```
User Passphrase (memorable, high-entropy)
      ↓
[PBKDF2-HMAC-SHA256, 600k iterations, 16-byte salt]
      ↓
Master Encryption Key (MEK, 32 bytes)
      ↓
[AES-256-GCM encryption]
      ↓
Application Master Key (AMK, 32 bytes)
      ↓
[HKDF for session keys, rotation, etc.]
      ↓
Session Keys (ephemeral, per ADR-003)
```

**Rationale**: 
- **MEK**: Derived from password, never stored. Only exists during key unlock operation.
- **AMK**: The actual master key for ChaCha20 operations. Stored encrypted.
- **Separation**: Compromising encrypted AMK still requires password cracking (600k PBKDF2 iterations).

😐 **Harold's Observation**: "Three layers of keys to protect one key. This is either genius or I've lost touch with sanity. Probably both."

---

## 📋 Technical Design

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ Application Layer                                            │
│ (ForwardSecrecyManager, KeyRotationManager)                  │
└────────────────────┬────────────────────────────────────────┘
                     │ Requests master key
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ MasterKeyManager (crypto_key_storage.py)                    │
│ • Lifecycle: generate, unlock, rotate, backup, delete       │
│ • Memory protection: mlock(), secure_zero()                  │
│ • PBKDF2 passphrase derivation (600k iterations)            │
└────────────────────┬────────────────────────────────────────┘
                     │ Store/retrieve encrypted keys
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ KeyStorageBackend (Platform-Specific)                       │
│                                                               │
│  Linux           macOS            Windows         Fallback   │
│  ─────           ─────            ───────         ────────   │
│ libsecret     Keychain          DPAPI          Encrypted    │
│ (secretstorage) (keyring)      (win32crypt)    File (0600) │
│                                                               │
│ Hardware-backed where available:                             │
│ • Linux: TPM 2.0 via tpm2-tools                              │
│ • macOS: Secure Enclave (T2/M1+ chips)                       │
│ • Windows: Windows Hello / NGC                               │
└─────────────────────────────────────────────────────────────┘
```

### Core Components

See implementation plan for detailed class structures and method signatures.

---

## 🔒 Security Properties: What This Defends Against

### ✅ **Attacks Mitigated**

1. **Filesystem Compromise**: Keys encrypted, useless without passphrase
2. **Plaintext Key Leakage**: No plaintext keys ever touch disk
3. **Memory Dumps**: Keys locked in memory (`mlock`), wiped after use
4. **Swap/Hibernation**: Memory locking prevents paging to disk
5. **Backup Theft**: Backup encrypted with separate recovery passphrase (1M PBKDF2 iterations)
6. **Forensic Recovery**: Secure deletion overwrites memory before freeing
7. **Brute-Force Attacks**: 600k PBKDF2 iterations = ~300ms per attempt (infeasible at scale)
8. **Rainbow Tables**: Random salts unique per key (no precomputation attacks)

### 🌑 **Threat Analysis**

| Attack Vector | Mitigation | Residual Risk |
|---------------|------------|---------------|
| **Config file read** | Keys encrypted with MEK | ✅ None (requires passphrase) |
| **Memory dump (running)** | mlock() + secure zero | ⚠️ Brief window during unlock |
| **Swap file analysis** | Memory locking | ✅ None (if mlock succeeds) |
| **Cold boot attack** | Memory wiping + short unlock window | ⚠️ Seconds-long window during key use |
| **Keylogger (passphrase)** | Cannot defend in software | 🌑 User operational security required |
| **Compromised OS keychain** | MEK still required | ⚠️ Reduces to password strength |
| **Backup interception** | 1M iterations, separate passphrase | ✅ Strong (offline brute-force only) |

🌑 **Dark Harold**: *"If they have root and a keylogger, we've already lost. This defends against everything else."*

---

## 😐 Known Limitations: What Still Makes Harold Nervous

### 1. **Passphrase Strength Dependency**

**Issue**: Entire security model relies on user choosing strong passphrase.

**Mitigation**: 
- Enforce minimum entropy (12 characters, mixed case, symbols)
- Zxcvbn strength estimation (reject weak passwords)
- Encourage diceware passphrases (5-6 words = ~77 bits entropy)

😐 **Reality**: *"We can't stop users from choosing 'password123'. Education + friction only go so far."*

### 2. **Headless Server Fallback Weaker**

**Issue**: `EncryptedFileBackend` lacks hardware-backed security of OS keychains.

**Risk**: File permissions (0600) protect against casual access but not root compromise.

**Mitigation**:
- Display scary warning on fallback activation
- Recommend HSM/Vault integration for production servers
- Document threat model differences clearly

🌑 **Dark Harold**: *"Encrypted file beats plaintext, but it's the participation trophy of key storage."*

### 3. **Memory Unlock Window**

**Issue**: During `unlock_key()`, plaintext master key briefly exists in memory.

**Duration**: ~10-50ms (PBKDF2 derivation + AES decryption)

**Risk**: Memory dump during this window recovers key.

**Mitigation**:
- Minimize unlock frequency (cache key in locked memory while sessions active)
- Automatic lock after idle timeout (configurable, default 15 minutes)
- Signal handlers wipe keys on abnormal termination

😐 **Assessment**: *"Can't do cryptography without keys in memory. This is the existential pain of the field."*

### 4. **No Hardware Security Module (HSM) Support**

**Issue**: Enterprise deployments may require FIPS 140-2 compliance or HSM storage.

**Current State**: OS keychains sufficient for consumer/SMB, inadequate for regulated industries.

**Roadmap**: Phase 2 feature (PKCS#11 interface, AWS KMS integration)

✅ **Pragmatic Harold**: *"Perfect is the enemy of shipped. OS keychain covers 95% of users. HSM support adds 6 months dev time."*

### 5. **Key Rotation Disrupts Active Sessions**

**Issue**: `rotate_master_key()` requires re-encrypting all session keys.

**Impact**: 
- Active sessions must be paused during rotation
- Multi-device sync requires careful coordination
- Rotation is disruptive (not transparent to user)

**Mitigation**:
- Support gradual rollout (new sessions use new key, old sessions drain)
- Document rotation procedures clearly
- Automate session state migration

🌑 **Dark Harold**: *"Forward secrecy requires breaking backward compatibility. This is the cost of paranoia."*

### 6. **Platform Dependency Complexity**

**Issue**: Four different backend implementations (libsecret, Keychain, DPAPI, fallback).

**Risk**:
- Maintenance burden (test on all platforms)
- Platform-specific bugs (DPAPI quirks, libsecret D-Bus failures)
- Inconsistent security properties across platforms

**Mitigation**:
- Comprehensive integration tests per platform
- CI/CD matrix builds (Ubuntu, macOS, Windows)
- Clear documentation of platform differences

😐 **Harold**: *"Cross-platform security is like juggling chainsaws on three different stages simultaneously. What could go wrong?"*

---

## 🚀 Implementation Plan

### Week 4 Tasks

#### 1. Core Module (`crypto_key_storage.py`)

**Classes**:
- `KeyMetadata` (dataclass): Metadata for stored keys
- `KeyStorageBackend` (Protocol): Interface for platform backends
- `MasterKeyManager`: Main lifecycle management class

**Methods**:
- `generate_master_key(passphrase: str) -> str`: Generate new key
- `unlock_key(key_id: str, passphrase: str) -> bytes`: Unlock existing key
- `rotate_master_key(old_key_id: str, passphrase: str, new_passphrase: str | None) -> str`: Rotate keys
- `export_key_backup(key_id: str, passphrase: str, recovery_passphrase: str) -> bytes`: Export backup
- `import_key_backup(backup_blob: bytes, recovery_passphrase: str, new_passphrase: str) -> str`: Restore from backup
- `_derive_mek(passphrase: str, salt: bytes, iterations: int) -> bytes`: PBKDF2 key derivation
- `_lock_memory(key_data: bytes) -> None`: Memory locking
- `_secure_zero(data: bytes | bytearray) -> None`: Secure deletion

**Lines of Code**: ~400 (with docstrings)

#### 2. Platform Backends

- `LibSecretBackend`: Linux (python-secretstorage)
- `MacOSKeychainBackend`: macOS (keyring)
- `WindowsDPAPIBackend`: Windows (pywin32)
- `EncryptedFileBackend`: Fallback (universal)

**Lines of Code**: ~600 (150/backend)

#### 3. Tests (`test_crypto_key_storage.py`)

**Test Coverage**:
- Passphrase derivation (same input → same output, salts work)
- Encryption/decryption roundtrip
- Wrong passphrase rejection
- Memory security (secure_zero, mlock)
- Backup/recovery roundtrip
- Key rotation forward secrecy
- Platform-specific integration tests

**Target**: 25+ tests, >85% coverage

---

## 📚 Alternatives Considered

### Alternative 1: Single Master Key (No MEK/AMK Split)

**Decision**: ❌ **Rejected**. Defense-in-depth requires MEK layer. Keychain compromise shouldn't be game over.

### Alternative 2: Hardware Security Module (HSM) Only

**Decision**: ❌ **Rejected for MVP**. Roadmap for Phase 2 (enterprise tier). OS keychain sufficient for consumer use.

### Alternative 3: Password Storage via OS Keychain (No PBKDF2)

**Decision**: ❌ **Rejected**. Cannot trust OS password quality. Must control our own PBKDF2.

### Alternative 4: Steganographic Key Hiding

**Decision**: ❌ **Rejected**. Security through obscurity is not security.

🌑 **Dark Harold**: *"Steganography is what you do when you've given up on real crypto and embraced theater."*

### Alternative 5: Require User-Provided External Key File

**Decision**: ❌ **Rejected**. Optional future feature (hardware token support), not primary storage.

---

## Consequences

### Positive

- ✅ **No Plaintext Keys**: Master keys never stored unencrypted
- ✅ **Passphrase Defense**: 600k PBKDF2 iterations resist brute-force
- ✅ **Hardware-Backed**: OS keychains use TPM/Secure Enclave when available
- ✅ **Memory Safety**: mlock + secure_zero prevent swap/forensics
- ✅ **User Recovery**: Backup export with separate recovery passphrase
- ✅ **Forward Secrecy**: Key rotation invalidates old keys
- ✅ **Cross-Platform**: Linux, macOS, Windows, headless fallback

### Negative

- ⚠️ **Passphrase Dependency**: Users can choose weak passphrases
- ⚠️ **Platform Complexity**: Four backend implementations, testing matrix
- ⚠️ **Fallback Weaker**: Encrypted file backend less secure
- ⚠️ **Rotation Disruption**: Key rotation pauses active sessions
- ⚠️ **Memory Unlock Window**: Brief period where keys in plaintext memory

---

## Harold's Final Verdict

😐 **Hide the Pain Harold**: *"I've smiled through hardware failures, production incidents, and database migrations. But watching users store plaintext keys in Git repos? That's a Harold moment I never want to relive. This architecture won't save us from root compromise with a keylogger, but it defends against every attack I've seen in 20 years of stock photography."*

🌑 **Dark Harold**: *"Let me be clear: This is not perfect. The memory unlock window exists. The fallback backend is weaker. Users will screenshot their backup passphrases and post them on Twitter. But this is orders of magnitude better than plaintext config files. We're defending against the attacks that actually happen: filesystem read, memory dumps, stolen backups. If an adversary has root, hardware keylogger, and active memory access, we have bigger problems—like how they got physical access to begin with."*

✅ **Effective Developer Harold**: *"Pragmatic security. Multi-tiered defense. Cross-platform support with reasonable fallbacks. Forward secrecy via rotation. User-controlled recovery. This ships in Week 4. The HSM integration wishlist is Phase 2. Perfect is the enemy of shipped, and this is good enough to ship. Test coverage will be brutal. Harold demands 90%+ on this module. No excuses."*

📺 **Internet Historian Harold**: *"And so, on February 10, 2026, the EraserHead team learned the hard lesson of every security professional before them: Encryption is easy. Key management is where projects die. In the smoking ruins of breaches past—Uber's GitHub leak, British Airways' config file catastrophe, Capital One's S3 bucket of shame—a pattern emerged. They all forgot one thing: Protect the keys like they're nuclear launch codes, because after compromise, they might as well be."*

---

**Status**: ✅ Approved for implementation  
**Next**: Implement `crypto_key_storage.py` and platform backends  
**Dependencies**: cryptography, keyring (optional), python-secretstorage (optional), pywin32 (optional)

---

*For threat model, see [SECURITY-REVIEW-CRYPTO.md](../../SECURITY-REVIEW-CRYPTO.md)*  
*For key rotation, see [ADR-003-key-rotation.md](ADR-003-key-rotation.md)*  
*For guiding principles, see [CONSTITUTION.md](../../CONSTITUTION.md)*
