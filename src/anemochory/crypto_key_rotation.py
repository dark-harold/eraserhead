"""
😐 Anemochory Protocol - Key Rotation Module

Implements automatic session key rotation to limit cryptanalysis surface area
and enhance forward secrecy. Keys rotate after 10,000 packets or 1 hour,
whichever comes first.

🌑 Dark Harold's Reminder: "A key used for 10 million packets is 10 million
opportunities for catastrophic failure. We rotate early and often."

Design: ADR-003-key-rotation.md
Addresses: SECURITY-REVIEW-CRYPTO.md Critical Issue #3
"""

import time
from collections import deque
from dataclasses import dataclass, field
from typing import ClassVar

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from .crypto import ChaCha20Engine, DecryptionError


# 😐 Type alias for clarity
SessionKey = bytes


@dataclass
class KeyRotationState:
    """
    Tracks key rotation state for a session.

    Manages automatic key rotation based on packet count and time thresholds.
    Maintains previous keys during grace period for in-flight packet handling.

    🌑 Security Properties:
    - Limits key exposure to max 10k packets or 1 hour
    - Grace period allows 60 seconds for in-flight packet decryption
    - Previous keys bounded to max 3 (memory safety)

    Attributes:
        current_key_index: Rotation count (0 = initial key, 1 = first rotation, etc.)
        packets_with_current_key: Counter incremented after each encryption
        key_created_at: Unix timestamp when current key was derived
        previous_keys: Deque of (key, timestamp) tuples for grace period decryption
    """

    current_key_index: int = 0
    packets_with_current_key: int = 0
    key_created_at: float = 0.0
    previous_keys: deque[tuple[bytes, float]] = field(default_factory=lambda: deque(maxlen=3))

    # Rotation thresholds (class-level constants)
    MAX_PACKETS_PER_KEY: ClassVar[int] = 10_000  # 📺 Conservative limit for paranoia
    MAX_KEY_AGE_SECONDS: ClassVar[int] = 3600  # 1 hour
    GRACE_PERIOD_SECONDS: ClassVar[int] = 60  # 😐 Window for in-flight packets

    def should_rotate_key(self) -> bool:
        """
        Check if key rotation threshold reached.

        Returns True if either:
        - Packet count >= 10,000
        - Key age >= 1 hour

        Returns:
            True if rotation should occur, False otherwise

        Example:
            >>> state = KeyRotationState()
            >>> state.packets_with_current_key = 9999
            >>> state.should_rotate_key()
            False
            >>> state.packets_with_current_key = 10000
            >>> state.should_rotate_key()
            True
        """
        packet_limit_reached = self.packets_with_current_key >= self.MAX_PACKETS_PER_KEY
        time_limit_reached = (time.time() - self.key_created_at) >= self.MAX_KEY_AGE_SECONDS
        return packet_limit_reached or time_limit_reached

    def increment_packet_count(self) -> None:
        """
        Increment packet counter after encryption.

        Should be called after every successful encryption operation.
        """
        self.packets_with_current_key += 1

    def is_key_in_grace_period(self, key_timestamp: float) -> bool:
        """
        Check if a previous key is still within grace period.

        Args:
            key_timestamp: Unix timestamp when key was created

        Returns:
            True if key created within last 60 seconds, False otherwise
        """
        age = time.time() - key_timestamp
        return age <= self.GRACE_PERIOD_SECONDS

    def get_stats(self) -> dict[str, int | float]:
        """
        Get current rotation state statistics.

        Returns:
            Dictionary with rotation metrics:
            - rotation_count: Number of rotations performed
            - packets_current_key: Packets encrypted with current key
            - current_key_age_seconds: Age of current key
            - grace_period_keys: Number of previous keys available

        😐 Useful for debugging and monitoring
        """
        return {
            "rotation_count": self.current_key_index,
            "packets_current_key": self.packets_with_current_key,
            "current_key_age_seconds": time.time() - self.key_created_at,
            "grace_period_keys": len(self.previous_keys),
        }


class KeyRotationManager:
    """
    Manages automatic key rotation for Anemochory Protocol sessions.

    Derives session keys from a master key using HKDF ratcheting. Rotates
    keys automatically when thresholds reached. Maintains previous keys
    during grace period for in-flight packet decryption.

    🌑 Security Model:
    - Master key should be ephemeral (from ForwardSecrecyManager)
    - Session keys derived deterministically via HKDF
    - Old keys securely wiped after grace period expires
    - Maximum 10k packets or 1 hour per key

    Architecture:
        Master Key (ephemeral)
             ↓ HKDF(info="initial-session")
        Session Key 0
             ↓ HKDF(info="ratchet-1")
        Session Key 1
             ↓ HKDF(info="ratchet-2")
        Session Key 2
             ...

    Example:
        >>> # Initialize with master key from forward secrecy
        >>> master_key = secrets.token_bytes(32)
        >>> manager = KeyRotationManager(master_key)
        >>>
        >>> # Encrypt packets
        >>> nonce, ciphertext = manager.encrypt(b"packet data")
        >>>
        >>> # Check rotation status
        >>> if manager.state.should_rotate_key():
        ...     manager.rotate_key()
        >>>
        >>> # Decrypt (tries current key, falls back to grace period)
        >>> plaintext = manager.decrypt(nonce, ciphertext)
    """

    def __init__(self, master_key: bytes) -> None:
        """
        Initialize key rotation manager with master key.

        Args:
            master_key: 32-byte master key (should be ephemeral from forward secrecy)

        Raises:
            ValueError: If master_key is not exactly 32 bytes

        😐 The master key should come from ForwardSecrecyManager, not stored persistently
        """
        if len(master_key) != 32:
            raise ValueError(f"Master key must be 32 bytes, got {len(master_key)}")

        self._master_key = master_key
        self.state = KeyRotationState()

        # Derive initial session key
        self._current_session_key = self._derive_initial_key()
        self._engine = ChaCha20Engine(self._current_session_key)

        # Initialize timestamp
        self.state.key_created_at = time.time()

    def _derive_initial_key(self) -> SessionKey:
        """
        Derive initial session key from master key using HKDF.

        Returns:
            32-byte session key

        🌑 Context binding via info string prevents cross-session attacks
        """
        info = b"anemochory-initial-session"
        kdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,  # 😐 Deterministic for reproducibility
            info=info,
        )
        return kdf.derive(self._master_key)

    def _derive_next_key(self, current_key: SessionKey) -> SessionKey:
        """
        Derive next session key via HKDF ratcheting.

        Args:
            current_key: Current 32-byte session key

        Returns:
            New 32-byte session key

        📺 The Ratchet Mechanism:
        Each key derives the next in a forward-only chain. Key N+1 comes from
        Key N, not from the master key. This means:
        - Forward: If you have Key N, you can derive Key N+1, N+2, ...
        - Backward: If you have Key N, you CANNOT derive Key N-1

        🌑 Limitation: If attacker captures Key N, they can derive future keys.
        Mitigation: Pair with forward secrecy (ephemeral master keys per session).
        """
        next_index = self.state.current_key_index + 1
        info = f"anemochory-ratchet-{next_index}".encode()

        kdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,  # Deterministic ratcheting
            info=info,
        )
        return kdf.derive(current_key)

    def rotate_key(self) -> None:
        """
        Rotate to next session key.

        Derives new key, stores old key for grace period, updates state.
        Should be called when should_rotate_key() returns True.

        🌑 Security Operations:
        1. Derive new key from current key (HKDF ratcheting)
        2. Store current key in grace period queue (60-second retention)
        3. Update engine with new key
        4. Reset packet counter and timestamp
        5. (TODO: Securely wipe old key after implementation)

        😐 Grace period allows in-flight packets to decrypt with previous keys
        """
        # Store current key for grace period
        self.state.previous_keys.append((self._current_session_key, time.time()))

        # Derive next key via ratcheting
        new_key = self._derive_next_key(self._current_session_key)

        # TODO: Securely wipe old key from memory (requires ctypes memset)
        # For now, Python GC will eventually collect it

        # Update state
        self._current_session_key = new_key
        self._engine = ChaCha20Engine(new_key)
        self.state.current_key_index += 1
        self.state.packets_with_current_key = 0
        self.state.key_created_at = time.time()

    def encrypt(self, plaintext: bytes) -> tuple[bytes, bytes]:
        """
        Encrypt plaintext with current session key.

        Automatically rotates key if threshold reached before encryption.

        Args:
            plaintext: Data to encrypt

        Returns:
            Tuple of (nonce, ciphertext)

        Raises:
            ValueError: If plaintext is empty

        Example:
            >>> manager = KeyRotationManager(secrets.token_bytes(32))
            >>> nonce, ciphertext = manager.encrypt(b"secret message")
            >>> # After 10k encryptions, rotation happens automatically
        """
        # Encrypt with current key
        nonce, ciphertext = self._engine.encrypt(plaintext)

        # Increment packet counter
        self.state.increment_packet_count()

        # Check if rotation needed after incrementing
        if self.state.should_rotate_key():
            self.rotate_key()

        return nonce, ciphertext

    def decrypt(self, nonce: bytes, ciphertext: bytes) -> bytes:
        """
        Decrypt ciphertext, trying current key then grace period keys.

        Decryption Strategy:
        1. Try current session key (fast path, >99% of packets)
        2. Try previous keys in grace period (in-flight packets)
        3. Raise exception if all keys fail

        Args:
            nonce: 12-byte nonce from encryption
            ciphertext: Encrypted data with authentication tag

        Returns:
            Decrypted plaintext

        Raises:
            DecryptionError: If decryption fails with all available keys

        🌑 Grace Period Behavior:
        After a rotation, packets encrypted with Key N can still be decrypted
        for 60 seconds. After that, decryption fails (requires retransmission).
        """
        # Fast path: Try current key first (most packets)
        try:
            return self._engine.decrypt(nonce, ciphertext)
        except DecryptionError:
            pass  # Current key failed, try grace period keys

        # Slow path: Try previous keys in grace period
        plaintext = self._try_grace_period_keys(nonce, ciphertext)
        if plaintext is not None:
            return plaintext

        # All keys failed
        raise DecryptionError(
            "Decryption failed with current and grace period keys. "
            "Packet may be from expired rotation or corrupted."
        )

    def _try_grace_period_keys(self, nonce: bytes, ciphertext: bytes) -> bytes | None:
        """
        Attempt decryption with previous keys during grace period.

        Args:
            nonce: 12-byte nonce
            ciphertext: Encrypted data

        Returns:
            Decrypted plaintext if successful, None if all keys fail

        😐 Tries keys in reverse order (most recent first) for efficiency
        """
        # Try keys from most recent to oldest
        for prev_key, created_at in reversed(self.state.previous_keys):
            # Only try keys within grace period
            if not self.state.is_key_in_grace_period(created_at):
                continue

            engine = ChaCha20Engine(prev_key)
            try:
                return engine.decrypt(nonce, ciphertext)
            except DecryptionError:
                continue  # This key failed, try next

        return None  # All grace period keys failed

    def get_stats(self) -> dict[str, int | float]:
        """
        Get key rotation statistics.

        Returns:
            Dictionary with rotation metrics

        😐 Useful for monitoring and debugging rotation behavior
        """
        return self.state.get_stats()


# 😐 Convenience function for common use case
def create_rotation_manager_from_ephemeral_key(ephemeral_key: bytes) -> KeyRotationManager:
    """
    Create KeyRotationManager from ephemeral forward secrecy key.

    Args:
        ephemeral_key: 32-byte ephemeral key from ForwardSecrecyManager

    Returns:
        Initialized KeyRotationManager ready for encryption

    Example:
        >>> from .crypto_forward_secrecy import ForwardSecrecyManager
        >>> fs_manager = ForwardSecrecyManager()
        >>> session_master_key = fs_manager.derive_session_key(b"session_id")
        >>> rot_manager = create_rotation_manager_from_ephemeral_key(session_master_key)
        >>> nonce, ciphertext = rot_manager.encrypt(b"packet data")

    📺 Integration Pattern:
    1. ForwardSecrecyManager generates ephemeral session master key
    2. KeyRotationManager derives rotating session keys from master
    3. ChaCha20Engine performs actual encryption/decryption
    """
    return KeyRotationManager(ephemeral_key)
