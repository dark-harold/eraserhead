"""
😐 Anemochory Protocol: Secure Session Manager

Integrates all security modules into a coherent session lifecycle:
  MasterKeyManager → ForwardSecrecyManager → KeyRotationManager → ChaCha20Engine
                                                     ↕
                                         ReplayProtectionManager

🌑 This is the glue that turns standalone crypto primitives into a
   working security stack. If any module fails, the whole session fails.
   That's a feature, not a bug.

📺 The Integration Story:
  Phase 1 built five independent crypto modules. Each excellent in isolation.
  None useful alone. This module makes them talk to each other, like a
  group therapy session for paranoid cryptographic primitives.
"""

import hashlib
import secrets
import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import Self

from .crypto_forward_secrecy import ForwardSecrecyManager, SessionKeyPair
from .crypto_key_rotation import KeyRotationManager
from .crypto_replay import ReplayProtectionManager


# ============================================================================
# Constants
# ============================================================================

SESSION_ID_SIZE = 16  # 128-bit session identifier (packet.py compatible)
PROTOCOL_VERSION = 0x01


# ============================================================================
# Session State
# ============================================================================


class SessionState(Enum):
    """Session lifecycle states."""

    CREATED = auto()  # Session initialized, not yet established
    KEY_EXCHANGE = auto()  # Awaiting peer's public key
    ESTABLISHED = auto()  # Keys exchanged, ready for encryption
    CLOSED = auto()  # Session ended, keys wiped


class SessionError(Exception):
    """Base exception for session operations."""


class SessionStateError(SessionError):
    """Operation invalid for current session state."""


# ============================================================================
# Secure Session
# ============================================================================


@dataclass
class SessionStats:
    """
    Session statistics for monitoring.

    😐 Numbers that tell you how paranoid you should be.
    """

    session_id: str
    state: str
    packets_sent: int = 0
    packets_received: int = 0
    key_rotations: int = 0
    replay_attempts_blocked: int = 0
    session_started_at: float = 0.0
    session_duration_seconds: float = 0.0


class SecureSession:
    """
    😐 Manages a complete secure communication session.

    Orchestrates all security modules:
    1. ForwardSecrecyManager: Ephemeral key exchange (X25519 ECDH)
    2. KeyRotationManager: Automatic key ratcheting (10k packets / 1h)
    3. ReplayProtectionManager: Nonce tracking + timestamp validation

    Lifecycle:
        create() → initiate_key_exchange() → complete_key_exchange() →
        encrypt()/decrypt() → close()

    🌑 Security Properties:
    - Forward secrecy: Past sessions safe if current keys compromised
    - Key rotation: Limits exposure per key (10k packets max)
    - Replay protection: Captured packets can't be replayed
    - Session isolation: Each session has unique key material
    - Memory security: Keys wiped on close (best-effort)

    Example:
        >>> # Node A: Create and initiate
        >>> session_a = SecureSession.create()
        >>> our_public_key = session_a.initiate_key_exchange()
        >>>
        >>> # Exchange public keys via secure channel...
        >>>
        >>> # Node A: Complete exchange with peer's key
        >>> session_a.complete_key_exchange(their_public_key)
        >>>
        >>> # Encrypt/decrypt
        >>> nonce, ciphertext = session_a.encrypt(b"hello")
        >>> plaintext = session_b.decrypt(nonce, ciphertext)
        >>>
        >>> # Cleanup
        >>> session_a.close()
    """

    def __init__(self) -> None:
        """
        Initialize session (use SecureSession.create() instead).

        😐 Direct __init__ is discouraged - use the factory method.
        """
        self._state = SessionState.CREATED
        self._session_id = secrets.token_bytes(SESSION_ID_SIZE)
        self._started_at = time.time()

        # Security modules (initialized during key exchange)
        self._fs_manager = ForwardSecrecyManager()
        self._keypair: SessionKeyPair | None = None
        self._rotation_manager: KeyRotationManager | None = None
        self._replay_manager = ReplayProtectionManager()

        # Counters
        self._packets_sent = 0
        self._packets_received = 0
        self._replay_blocks = 0
        self._sequence_number = 0

    @classmethod
    def create(cls) -> Self:
        """
        Factory method for creating a new secure session.

        Returns:
            New SecureSession in CREATED state

        😐 Preferred over direct construction.
        """
        return cls()

    @property
    def state(self) -> SessionState:
        """Current session state."""
        return self._state

    @property
    def session_id(self) -> bytes:
        """Session identifier (16 bytes)."""
        return self._session_id

    def initiate_key_exchange(self) -> bytes:
        """
        Generate ephemeral keypair and return public key for peer.

        Must be called before complete_key_exchange().

        Returns:
            32-byte public key to send to peer

        Raises:
            SessionStateError: If session not in CREATED state

        🌑 The private key stays in memory until session closes.
        Never serialize or persist it.
        """
        if self._state != SessionState.CREATED:
            raise SessionStateError(f"Cannot initiate key exchange in state {self._state.name}")

        self._keypair = self._fs_manager.generate_session_keypair()
        self._state = SessionState.KEY_EXCHANGE

        return self._keypair.public_key

    def complete_key_exchange(self, peer_public_key: bytes) -> None:
        """
        Complete key exchange with peer's public key.

        Derives shared secret → session master key → initializes rotation.

        Args:
            peer_public_key: Peer's 32-byte X25519 public key

        Raises:
            SessionStateError: If not in KEY_EXCHANGE state
            SessionError: If key exchange fails

        🌑 After this, the session is ESTABLISHED and ready for encryption.
        The shared secret is immediately consumed by HKDF - never stored.
        """
        if self._state != SessionState.KEY_EXCHANGE:
            raise SessionStateError(f"Cannot complete key exchange in state {self._state.name}")

        if self._keypair is None:
            raise SessionStateError("No keypair generated - call initiate_key_exchange() first")

        try:
            # Perform ECDH
            shared_secret = self._fs_manager.derive_shared_secret(
                self._keypair.private_key, peer_public_key
            )

            # 🌑 Derive deterministic session binding from both public keys
            # Both sides sort keys identically → same HKDF input
            keys_sorted = sorted([self._keypair.public_key, peer_public_key])
            shared_session_id = hashlib.sha256(keys_sorted[0] + keys_sorted[1]).digest()

            # Derive session master key (binds to shared session_id)
            session_master_key = self._fs_manager.derive_session_master_key(
                shared_secret,
                shared_session_id,
                context="anemochory-secure-session",
                timestamp=0,  # 😐 Timestamp excluded: both sides must derive same key
            )

            # Initialize key rotation with session master key
            self._rotation_manager = KeyRotationManager(session_master_key)

            # 😐 Best-effort cleanup of intermediate key material
            # Python limitations: can't truly wipe immutable bytes
            del shared_secret
            del session_master_key

            self._state = SessionState.ESTABLISHED

        except Exception as e:
            self._state = SessionState.CLOSED
            raise SessionError(f"Key exchange failed: {e}") from e

    def establish_with_shared_key(self, shared_key: bytes) -> None:
        """
        Establish session directly with a pre-shared key (testing/fallback).

        Skips ECDH exchange - uses provided key directly with KeyRotationManager.

        Args:
            shared_key: 32-byte symmetric key

        Raises:
            SessionStateError: If not in CREATED state
            ValueError: If key is wrong size

        😐 For testing or when key exchange happens out-of-band.
        🌑 Less secure than ECDH - no forward secrecy guarantee.
        """
        if self._state != SessionState.CREATED:
            raise SessionStateError(f"Cannot establish with shared key in state {self._state.name}")

        if len(shared_key) != 32:
            raise ValueError(f"Shared key must be 32 bytes, got {len(shared_key)}")

        self._rotation_manager = KeyRotationManager(shared_key)
        self._state = SessionState.ESTABLISHED

    def encrypt(self, plaintext: bytes) -> tuple[bytes, bytes]:
        """
        Encrypt plaintext with session key (auto-rotates when needed).

        Args:
            plaintext: Data to encrypt

        Returns:
            Tuple of (nonce, ciphertext)

        Raises:
            SessionStateError: If session not ESTABLISHED
            ValueError: If plaintext is empty

        🌑 Each encryption:
        1. Creates replay protection metadata
        2. Encrypts with current session key
        3. Increments sequence number
        4. Auto-rotates key if threshold reached
        """
        if self._state != SessionState.ESTABLISHED:
            raise SessionStateError(f"Cannot encrypt in state {self._state.name}")

        if self._rotation_manager is None:
            raise SessionStateError("Session not properly established")

        # Encrypt with auto-rotating key
        nonce, ciphertext = self._rotation_manager.encrypt(plaintext)

        # Track for replay protection (sender side)
        self._replay_manager.mark_nonce_seen(nonce, self._session_id)

        # Update counters
        self._packets_sent += 1
        self._sequence_number += 1

        return nonce, ciphertext

    def decrypt(self, nonce: bytes, ciphertext: bytes) -> bytes:
        """
        Decrypt ciphertext with replay protection.

        Args:
            nonce: 12-byte nonce from encryption
            ciphertext: Encrypted data

        Returns:
            Decrypted plaintext

        Raises:
            SessionStateError: If session not ESTABLISHED
            SessionError: If replay attack detected
            DecryptionError: If decryption fails

        🌑 Each decryption:
        1. Checks nonce against replay protection (reject duplicates)
        2. Decrypts with current key (falls back to grace period keys)
        3. Records nonce as seen
        """
        if self._state != SessionState.ESTABLISHED:
            raise SessionStateError(f"Cannot decrypt in state {self._state.name}")

        if self._rotation_manager is None:
            raise SessionStateError("Session not properly established")

        # Check for replay attack
        if self._replay_manager.is_nonce_seen(nonce, self._session_id):
            self._replay_blocks += 1
            raise SessionError("🌑 Replay attack detected: duplicate nonce")

        # Decrypt (tries current key + grace period keys)
        plaintext = self._rotation_manager.decrypt(nonce, ciphertext)

        # Mark nonce as seen AFTER successful decryption
        self._replay_manager.mark_nonce_seen(nonce, self._session_id)
        self._packets_received += 1

        return plaintext

    def close(self) -> None:
        """
        Close session and wipe key material.

        😐 Best-effort memory cleanup. Python's immutable bytes
        are a known limitation (documented in ADR-004).

        🌑 After close(), all operations raise SessionStateError.
        """
        self._state = SessionState.CLOSED

        # Wipe what we can
        self._keypair = None
        self._rotation_manager = None
        self._session_id = b"\x00" * SESSION_ID_SIZE

    def get_stats(self) -> SessionStats:
        """
        Get session statistics.

        Returns:
            SessionStats with current metrics
        """
        rotation_stats = self._rotation_manager.get_stats() if self._rotation_manager else {}

        return SessionStats(
            session_id=self._session_id.hex(),
            state=self._state.name,
            packets_sent=self._packets_sent,
            packets_received=self._packets_received,
            key_rotations=int(rotation_stats.get("rotation_count", 0)),
            replay_attempts_blocked=self._replay_blocks,
            session_started_at=self._started_at,
            session_duration_seconds=time.time() - self._started_at,
        )

    def __del__(self) -> None:
        """Cleanup on garbage collection."""
        if self._state != SessionState.CLOSED:
            self.close()

    def __repr__(self) -> str:
        return (
            f"SecureSession(id={self._session_id.hex()[:8]}..., "
            f"state={self._state.name}, "
            f"sent={self._packets_sent}, recv={self._packets_received})"
        )
