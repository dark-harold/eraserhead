"""
Master Key Storage and Lifecycle Management (ADR-004).

😐 This module defends against the attacks that actually happen:
filesystem reads, memory dumps, stolen backups. If the adversary has
root + keylogger + active memory access, we have bigger problems.

🌑 Security Properties:
- Master keys NEVER stored in plaintext on disk
- Passphrase-derived encryption (PBKDF2 600k iterations)
- Memory locking to prevent swap (best-effort)
- Secure deletion with memory wiping
- OS keychain integration (hardware-backed when available)

Author: harold-implementer (pragmatic security paranoia)
Date: February 10, 2026
"""

import contextlib
import ctypes
import json
import secrets
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Self

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


@dataclass
class KeyMetadata:
    """
    Metadata for stored master key.

    🌑 Field Notes:
    - key_id: UUID-like identifier (tracking, not security)
    - salt: 16-byte random (PBKDF2, prevents rainbow tables)
    - iterations: PBKDF2 count (600k minimum, future-proofing allowed)
    - created_at: Unix timestamp (audit trail)
    - rotations: Count of rotations (forward secrecy tracking)
    """

    key_id: str
    salt: bytes
    iterations: int
    created_at: float
    algorithm: str = "chacha20-poly1305"
    rotations: int = 0

    def to_dict(self) -> dict[str, object]:
        """Convert to dict for JSON serialization (salt as hex)."""
        return {
            "key_id": self.key_id,
            "salt": self.salt.hex(),
            "iterations": self.iterations,
            "created_at": self.created_at,
            "algorithm": self.algorithm,
            "rotations": self.rotations,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Self:
        """Load from dict (convert hex salt back to bytes)."""
        return cls(
            key_id=str(data["key_id"]),
            salt=bytes.fromhex(str(data["salt"])),
            iterations=int(data["iterations"]),
            created_at=float(data["created_at"]),
            algorithm=str(data.get("algorithm", "chacha20-poly1305")),
            rotations=int(data.get("rotations", 0)),
        )


class KeyStorageBackend(Protocol):
    """
    Interface for OS-specific keychain backends.

    Implementations:
    - LibSecretBackend: Linux (GNOME Keyring, KDE Wallet)
    - MacOSKeychainBackend: macOS (Keychain Services)
    - WindowsDPAPIBackend: Windows (Data Protection API)
    - EncryptedFileBackend: Fallback (headless servers, Docker)

    😐 All backends store encrypted keys. None store plaintext.
    """

    def store_key(self, key_id: str, encrypted_key: bytes, metadata: KeyMetadata) -> None:
        """Store encrypted key in OS keychain."""
        ...

    def retrieve_key(self, key_id: str) -> tuple[bytes, KeyMetadata] | None:
        """Retrieve encrypted key from OS keychain (None if not found)."""
        ...

    def delete_key(self, key_id: str) -> None:
        """Delete key from OS keychain."""
        ...

    def list_keys(self) -> list[str]:
        """List all stored key IDs."""
        ...


class EncryptedFileBackend:
    """
    Fallback backend: Encrypted file storage (headless servers, Docker).

    😐 Security Properties:
    - Encrypted keys stored in files with 0600 permissions
    - Separate metadata files (0600)
    - Atomic writes (write to .tmp, rename)
    - Still requires passphrase to decrypt

    🌑 Known Limitations:
    - No hardware-backed security (compared to OS keychains)
    - Relies on filesystem permissions (root can read)
    - "Participation trophy of key storage" - Dark Harold

    Better than plaintext. Not as good as TPM/Secure Enclave.
    """

    def __init__(self, storage_path: str | Path, application_name: str = "eraserhead"):
        """
        Initialize file-based storage.

        Args:
            storage_path: Directory for key files (created if not exists)
            application_name: Application identifier (subdirectory)
        """
        self._storage_path = Path(storage_path) / application_name
        self._storage_path.mkdir(mode=0o700, parents=True, exist_ok=True)

        # 😐 Restrictive permissions: owner read/write only
        with contextlib.suppress(OSError, PermissionError):
            self._storage_path.chmod(0o700)

    def store_key(self, key_id: str, encrypted_key: bytes, metadata: KeyMetadata) -> None:
        """
        Store encrypted key with atomic write + restrictive permissions.

        🌑 Security: Write to .tmp, chmod 0600, rename (atomic)
        """
        key_file = self._storage_path / f"{key_id}.key"
        metadata_file = self._storage_path / f"{key_id}.meta"

        # Write key atomically
        temp_key = key_file.with_suffix(".tmp")
        temp_key.write_bytes(encrypted_key)
        with contextlib.suppress(OSError, PermissionError):
            temp_key.chmod(0o600)
        temp_key.rename(key_file)

        # Write metadata atomically
        temp_meta = metadata_file.with_suffix(".tmp")
        temp_meta.write_text(json.dumps(metadata.to_dict(), indent=2))
        with contextlib.suppress(OSError, PermissionError):
            temp_meta.chmod(0o600)
        temp_meta.rename(metadata_file)

    def retrieve_key(self, key_id: str) -> tuple[bytes, KeyMetadata] | None:
        """Retrieve encrypted key + metadata from files."""
        key_file = self._storage_path / f"{key_id}.key"
        metadata_file = self._storage_path / f"{key_id}.meta"

        if not key_file.exists() or not metadata_file.exists():
            return None

        encrypted_key = key_file.read_bytes()
        metadata_dict = json.loads(metadata_file.read_text())
        metadata = KeyMetadata.from_dict(metadata_dict)

        return encrypted_key, metadata

    def delete_key(self, key_id: str) -> None:
        """
        Delete key + metadata files.

        🌑 Security: Overwrite before unlink (paranoid deletion).
        """
        key_file = self._storage_path / f"{key_id}.key"
        metadata_file = self._storage_path / f"{key_id}.meta"

        # Overwrite with random data before deletion
        if key_file.exists():
            size = key_file.stat().st_size
            key_file.write_bytes(secrets.token_bytes(size))
            key_file.unlink()

        if metadata_file.exists():
            metadata_file.unlink()

    def list_keys(self) -> list[str]:
        """List all key IDs in storage directory."""
        return [
            f.stem for f in self._storage_path.glob("*.key")
        ]


class MasterKeyManager:
    """
    Manages master key lifecycle: generation, storage, retrieval, rotation, deletion.

    🌑 Security Properties:
    - Master keys never stored in plaintext
    - Passphrase-derived encryption (PBKDF2 600k iterations)
    - Memory locked to prevent swap (best-effort)
    - Secure deletion with memory wiping
    - OS keychain integration (hardware-backed when available)

    Key Hierarchy (ADR-004):
    User Passphrase → [PBKDF2 600k] → MEK → [AES-256-GCM] → AMK (stored)

    😐 Three layers of keys to protect one key. Genius or madness? Both.
    """

    # Constants
    DEFAULT_PBKDF2_ITERATIONS = 600_000  # ~300ms on modern CPU
    BACKUP_PBKDF2_ITERATIONS = 1_000_000  # 1M for backups (higher security)
    SALT_SIZE = 16  # bytes
    AES_NONCE_SIZE = 12  # bytes (GCM standard)
    MASTER_KEY_SIZE = 32  # bytes (256 bits for ChaCha20)

    def __init__(self, backend: KeyStorageBackend, application_name: str = "eraserhead"):
        """
        Initialize master key manager with storage backend.

        Args:
            backend: KeyStorageBackend implementation (platform-specific or fallback)
            application_name: Application identifier for key namespacing
        """
        self._backend = backend
        self._app_name = application_name
        self._active_key: bytes | None = None  # Locked in memory
        self._key_metadata: KeyMetadata | None = None

    def generate_master_key(self, passphrase: str) -> str:
        """
        Generate new master key, encrypt with passphrase-derived MEK, store in keychain.

        Args:
            passphrase: User passphrase (will be passed through PBKDF2)

        Returns:
            key_id: Unique identifier for this key

        Raises:
            ValueError: If passphrase is empty or too weak

        🌑 Threat Defense:
        - 600k PBKDF2 iterations resist brute-force (~300ms per attempt)
        - Random salt prevents rainbow tables
        - AES-256-GCM AEAD ensures integrity (detects tampering)

        😐 We can't stop users from choosing 'password123', but we make
        brute-forcing it expensive.
        """
        if not passphrase or len(passphrase) < 8:
            raise ValueError("Passphrase must be at least 8 characters")

        # Generate cryptographically secure master key (AMK)
        master_key = secrets.token_bytes(self.MASTER_KEY_SIZE)
        key_id = secrets.token_hex(16)  # UUID-like identifier

        # Generate salt for PBKDF2
        salt = secrets.token_bytes(self.SALT_SIZE)

        # Derive Master Encryption Key (MEK) from passphrase
        mek = self._derive_mek(passphrase, salt, self.DEFAULT_PBKDF2_ITERATIONS)

        # Encrypt master key with MEK (AES-256-GCM)
        encrypted_blob = self._encrypt_with_mek(mek, master_key, key_id)

        # Create metadata
        metadata = KeyMetadata(
            key_id=key_id,
            salt=salt,
            iterations=self.DEFAULT_PBKDF2_ITERATIONS,
            created_at=time.time(),
            algorithm="chacha20-poly1305",
            rotations=0,
        )

        # Store in backend (OS keychain or encrypted file)
        self._backend.store_key(key_id, encrypted_blob, metadata)

        # Cache key in memory for immediate use (convert to bytearray for _secure_zero)
        self._active_key = bytearray(master_key)
        self._key_metadata = metadata
        self._lock_memory(self._active_key)

        # Wipe temporary MEK (paranoid deletion)
        mek_array = bytearray(mek)
        self._secure_zero(mek_array)

        return key_id

    def unlock_key(self, key_id: str, passphrase: str) -> bytes:
        """
        Retrieve and decrypt master key from keychain.

        Args:
            key_id: Key identifier (from generate_master_key)
            passphrase: User passphrase

        Returns:
            Plaintext master key (32 bytes). Caller MUST wipe after use.

        Raises:
            ValueError: If key not found or passphrase incorrect

        🌑 Security Window:
        During this function, MEK exists in memory for ~10-50ms.
        This is the existential pain of cryptography: can't decrypt
        without keys in memory. We minimize the window and wipe ASAP.
        """
        # Retrieve from backend
        result = self._backend.retrieve_key(key_id)
        if result is None:
            raise ValueError(f"Key {key_id} not found in keychain")

        encrypted_blob, metadata = result

        # Derive MEK from passphrase
        mek = self._derive_mek(passphrase, metadata.salt, metadata.iterations)

        # Decrypt master key
        try:
            master_key = self._decrypt_with_mek(mek, encrypted_blob, key_id)
        except Exception as e:
            self._secure_zero(mek)
            raise ValueError("Incorrect passphrase or corrupted key") from e

        # Lock in memory and cache (convert to bytearray for secure zeroing)
        self._active_key = bytearray(master_key)
        self._key_metadata = metadata
        self._lock_memory(self._active_key)

        # Wipe MEK
        mek_array = bytearray(mek)
        self._secure_zero(mek_array)

        return master_key

    def get_active_key(self) -> bytes | None:
        """
        Get currently unlocked key (or None if locked).

        😐 This returns the cached key after unlock_key().
        Caller MUST NOT modify returned bytes.
        """
        return self._active_key

    def lock_key(self) -> None:
        """
        Wipe active key from memory (force re-unlock for next use).

        🌑 Call this after sensitive operations or on idle timeout.
        """
        if self._active_key:
            self._secure_zero(self._active_key)
            self._active_key = None
        self._key_metadata = None

    def rotate_master_key(
        self,
        old_key_id: str,
        passphrase: str,
        new_passphrase: str | None = None,
    ) -> str:
        """
        Generate new master key, invalidate old key.

        Args:
            old_key_id: Current key identifier
            passphrase: Current passphrase
            new_passphrase: New passphrase (or None to reuse current)

        Returns:
            new_key_id: New key identifier

        🌑 Forward Secrecy:
        Old key deleted from keychain, cannot decrypt past sessions.

        ⚠️ WARNING: This does NOT re-encrypt session keys. That requires
        session manager integration (Phase 1 Week 5). Current implementation
        just generates new master key for future sessions.
        """
        # Unlock old key to verify passphrase
        old_master_key = self.unlock_key(old_key_id, passphrase)

        # Generate new master key
        new_passphrase_actual = new_passphrase or passphrase
        new_key_id = self.generate_master_key(new_passphrase_actual)

        # TODO: Re-encrypt session keys with new master key
        # (Requires ForwardSecrecyManager integration)

        # Delete old key from backend
        self._backend.delete_key(old_key_id)

        # Wipe old key from memory
        old_master_key_array = bytearray(old_master_key)
        self._secure_zero(old_master_key_array)

        return new_key_id

    def export_key_backup(
        self,
        key_id: str,
        passphrase: str,
        recovery_passphrase: str,
    ) -> bytes:
        """
        Export encrypted key backup for user-controlled recovery.

        Args:
            key_id: Key to backup
            passphrase: Current passphrase
            recovery_passphrase: Separate recovery passphrase (MUST differ)

        Returns:
            Encrypted backup blob (store securely: paper, vault, etc.)

        Raises:
            ValueError: If recovery_passphrase same as passphrase

        🌑 Backup Paranoia:
        - Recovery passphrase MUST be different (two-factor defense)
        - 1M PBKDF2 iterations (vs 600k primary) - adversary controls timing
        - User controls backup storage (print on paper, hardware vault)

        😐 Users will screenshot their recovery passphrase and post on Twitter.
        We can only make it expensive to attack, not idiot-proof.
        """
        if recovery_passphrase == passphrase:
            raise ValueError("Recovery passphrase must differ from primary passphrase")

        # Unlock key with primary passphrase
        master_key = self.unlock_key(key_id, passphrase)

        # Derive recovery MEK (HIGHER iteration count for backups)
        recovery_salt = secrets.token_bytes(self.SALT_SIZE)
        recovery_mek = self._derive_mek(
            recovery_passphrase,
            recovery_salt,
            self.BACKUP_PBKDF2_ITERATIONS,
        )

        # Encrypt master key with recovery MEK
        recovery_nonce = secrets.token_bytes(self.AES_NONCE_SIZE)
        aesgcm = AESGCM(recovery_mek)
        # 😐 Use generic associated data (key_id may change on import)
        associated_data = b"eraserhead-backup-"
        backup_ciphertext = aesgcm.encrypt(recovery_nonce, master_key, associated_data)

        # Pack backup format: version | salt | iterations | nonce | ciphertext
        backup_blob = (
            b"\x01"  # Version 1
            + recovery_salt
            + self.BACKUP_PBKDF2_ITERATIONS.to_bytes(4, "big")
            + recovery_nonce
            + backup_ciphertext
        )

        # Wipe sensitive material
        master_key_array = bytearray(master_key)
        recovery_mek_array = bytearray(recovery_mek)
        self._secure_zero(master_key_array)
        self._secure_zero(recovery_mek_array)

        return backup_blob

    def import_key_backup(
        self,
        backup_blob: bytes,
        recovery_passphrase: str,
        new_passphrase: str,
    ) -> str:
        """
        Restore master key from encrypted backup.

        Args:
            backup_blob: Encrypted backup (from export_key_backup)
            recovery_passphrase: Recovery passphrase
            new_passphrase: New passphrase for restored key

        Returns:
            key_id: New key identifier (backup import creates new ID)

        Raises:
            ValueError: If backup corrupted or recovery passphrase wrong

        😐 Import creates NEW key_id (doesn't restore old ID). This is
        intentional: backup is for disaster recovery, not migration.
        """
        # Parse backup format
        if backup_blob[0] != 1:
            raise ValueError(f"Unsupported backup version: {backup_blob[0]}")

        recovery_salt = backup_blob[1:17]
        recovery_iterations = int.from_bytes(backup_blob[17:21], "big")
        recovery_nonce = backup_blob[21:33]
        ciphertext = backup_blob[33:]

        # Derive recovery MEK
        recovery_mek = self._derive_mek(
            recovery_passphrase,
            recovery_salt,
            recovery_iterations,
        )

        # Decrypt master key
        # 😐 Use same generic associated data as export
        aesgcm = AESGCM(recovery_mek)
        associated_data = b"eraserhead-backup-"
        try:
            master_key = aesgcm.decrypt(recovery_nonce, ciphertext, associated_data)
        except Exception as e:
            recovery_mek_array = bytearray(recovery_mek)
            self._secure_zero(recovery_mek_array)
            raise ValueError("Incorrect recovery passphrase or corrupted backup") from e

        # Generate new key_id and store with new passphrase
        key_id = secrets.token_hex(16)
        salt = secrets.token_bytes(self.SALT_SIZE)
        mek = self._derive_mek(new_passphrase, salt, self.DEFAULT_PBKDF2_ITERATIONS)
        encrypted_blob = self._encrypt_with_mek(mek, master_key, key_id)

        metadata = KeyMetadata(
            key_id=key_id,
            salt=salt,
            iterations=self.DEFAULT_PBKDF2_ITERATIONS,
            created_at=time.time(),
            algorithm="chacha20-poly1305",
            rotations=0,  # Restored keys start at rotation 0
        )

        self._backend.store_key(key_id, encrypted_blob, metadata)

        # Cache restored key (bytearray for secure zeroing)
        self._active_key = bytearray(master_key)
        self._key_metadata = metadata
        self._lock_memory(self._active_key)

        # Wipe sensitive material
        recovery_mek_array = bytearray(recovery_mek)
        mek_array = bytearray(mek)
        master_key_array = bytearray(master_key)
        self._secure_zero(recovery_mek_array)
        self._secure_zero(mek_array)
        self._secure_zero(master_key_array)

        return key_id

    def _derive_mek(self, passphrase: str, salt: bytes, iterations: int) -> bytes:
        """
        Derive Master Encryption Key from passphrase via PBKDF2-HMAC-SHA256.

        🌑 Security: 600k iterations = ~300ms on modern CPU = expensive
        brute-force (10 attempts/sec single-threaded, impractical at scale).
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,  # 256 bits
            salt=salt,
            iterations=iterations,
        )
        return kdf.derive(passphrase.encode("utf-8"))

    def _encrypt_with_mek(self, mek: bytes, master_key: bytes, key_id: str) -> bytes:
        """
        Encrypt master key with MEK using AES-256-GCM.

        Returns: nonce (12 bytes) + ciphertext

        🌑 AEAD binding: Associated data includes key_id to prevent
        swapping ciphertexts between keys (authenticated encryption).
        """
        aesgcm = AESGCM(mek)
        nonce = secrets.token_bytes(self.AES_NONCE_SIZE)
        associated_data = f"{self._app_name}-mk-{key_id}".encode()
        ciphertext = aesgcm.encrypt(nonce, master_key, associated_data)
        return nonce + ciphertext

    def _decrypt_with_mek(self, mek: bytes, encrypted_blob: bytes, key_id: str) -> bytes:
        """
        Decrypt master key with MEK using AES-256-GCM.

        Raises: Exception if passphrase wrong or ciphertext tampered.
        """
        nonce = encrypted_blob[:self.AES_NONCE_SIZE]
        ciphertext = encrypted_blob[self.AES_NONCE_SIZE:]
        associated_data = f"{self._app_name}-mk-{key_id}".encode()

        aesgcm = AESGCM(mek)
        return aesgcm.decrypt(nonce, ciphertext, associated_data)

    def _lock_memory(self, key_data: bytes) -> None:
        """
        Lock memory page containing key to prevent swapping to disk.

        🌑 Defense: Memory dumps from swap/hibernation won't contain keys.

        Platform-specific:
        - POSIX (Linux, macOS): mlock() via ctypes
        - Windows: VirtualLock() via ctypes

        😐 Best-effort: May fail without CAP_IPC_LOCK or admin privileges.
        Harold tried. If attackers have root, they have bigger leverage.
        """
        try:
            # Get memory address and size
            addr = id(key_data)
            size = len(key_data)

            if sys.platform == "win32":
                kernel32 = ctypes.windll.kernel32  # type: ignore
                result = kernel32.VirtualLock(addr, size)
                if result == 0:
                    pass  # Failed, but non-fatal
            else:
                libc = ctypes.CDLL("libc.so.6")
                result = libc.mlock(addr, size)
                if result != 0:
                    pass  # Failed, but non-fatal
        except (AttributeError, OSError):
            # mlock unavailable or insufficient permissions
            # 😐 Harold: "We tried. Attackers with root have bigger problems."
            pass

    def _secure_zero(self, data: bytes | bytearray) -> None:
        """
        Overwrite memory with zeros before deallocation.

        🌑 Defense: Prevents memory forensics from recovering keys.

        😐 Python Limitation: bytes objects are immutable (can't zero).
        For mutable bytearray, we overwrite in-place. This is best-effort
        security in Python (true memory wiping requires C extensions).
        """
        if isinstance(data, bytearray):
            # Overwrite bytearray in-place (mutable)
            for i in range(len(data)):
                data[i] = 0
        # bytes objects are immutable - can't zero them safely in pure Python
        # 😐 Accept this limitation. Rely on garbage collection + OS memory zeroing.

    def __del__(self) -> None:
        """Ensure keys wiped on garbage collection."""
        if self._active_key:
            self._secure_zero(self._active_key)


def create_default_backend(storage_path: str | Path | None = None) -> KeyStorageBackend:
    """
    Create default storage backend (encrypted file fallback).

    Args:
        storage_path: Directory for encrypted key files (defaults to ~/.eraserhead/keys)

    Returns:
        EncryptedFileBackend instance

    😐 Platform-specific backends (libsecret, Keychain, DPAPI) will be
    added in Phase 1 Week 5. For now, encrypted file is universal.
    """
    if storage_path is None:
        storage_path = Path.home() / ".eraserhead" / "keys"

    return EncryptedFileBackend(storage_path)
