"""
😐 Anemochory Protocol: Forward Secrecy Module

Implements ephemeral key exchange using X25519 ECDH to provide forward secrecy.
Addresses SECURITY-REVIEW-CRYPTO.md Critical Issue #1.

🌑 Security Guarantee: If a node is compromised AFTER session ends,
   past sessions remain secure because ephemeral keys are never persisted.
"""

import secrets
import time
from dataclasses import dataclass

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


# Constants
SESSION_ID_SIZE = 32  # 32 bytes for 256-bit security
SHARED_SECRET_SIZE = 32  # X25519 output size
KEY_SIZE = 32  # ChaCha20-Poly1305 key size


class ForwardSecrecyError(Exception):
    """Raised for forward secrecy operation failures"""

    pass


@dataclass
class SessionKeyPair:
    """
    Ephemeral key pair for one session.

    😐 These keys are temporary - discarded after session ends.
    🌑 Never persist these keys to disk/database.

    Attributes:
        private_key: X25519 private key for ECDH
        public_key: Serialized public key to send to peer
        session_id: Random identifier binding this session
    """

    private_key: x25519.X25519PrivateKey
    public_key: bytes
    session_id: bytes

    def __post_init__(self) -> None:
        """Validate field sizes"""
        if len(self.public_key) != SHARED_SECRET_SIZE:
            raise ValueError(
                f"Public key must be {SHARED_SECRET_SIZE} bytes, got {len(self.public_key)}"
            )
        if len(self.session_id) != SESSION_ID_SIZE:
            raise ValueError(
                f"Session ID must be {SESSION_ID_SIZE} bytes, got {len(self.session_id)}"
            )


class ForwardSecrecyManager:
    """
    😐 Manages ephemeral key exchanges for forward secrecy.

    🌑 Security Properties:
    - Past sessions remain secure even if current keys compromised
    - Each session uses unique ephemeral keys (never reused)
    - Session IDs bind keys to specific sessions (prevents cross-session attacks)
    - Timestamps bind keys to specific time windows

    Example usage:
        >>> # Node A: Generate ephemeral keypair
        >>> manager = ForwardSecrecyManager()
        >>> our_keypair = manager.generate_session_keypair()
        >>>
        >>> # Exchange public keys with Node B (secure channel)
        >>> # ... send our_keypair.public_key, receive their_public_key ...
        >>>
        >>> # Node A: Derive shared secret
        >>> shared = manager.derive_shared_secret(
        ...     our_keypair.private_key,
        ...     their_public_key
        ... )
        >>>
        >>> # Node A: Derive session master key
        >>> master_key = manager.derive_session_master_key(
        ...     shared,
        ...     our_keypair.session_id
        ... )
        >>>
        >>> # Use with existing ChaCha20Engine from crypto.py
        >>> from eraserhead.anemochory.crypto import ChaCha20Engine
        >>> engine = ChaCha20Engine(master_key)
        >>> nonce, ciphertext = engine.encrypt(b"packet data")
    """

    def __init__(self) -> None:
        """
        Initialize forward secrecy manager.

        😐 Stateless by design - no session tracking needed.
        """
        pass

    def generate_session_keypair(self) -> SessionKeyPair:
        """
        Generate ephemeral X25519 keypair for new session.

        😐 Each call generates unique keys - never reused.
        🌑 Caller must protect private_key in memory, zeroize after use.

        Returns:
            SessionKeyPair with fresh ephemeral keys and random session ID

        Example:
            >>> manager = ForwardSecrecyManager()
            >>> keypair = manager.generate_session_keypair()
            >>> assert len(keypair.session_id) == 32
            >>> assert len(keypair.public_key) == 32
        """
        # Generate ephemeral X25519 keypair
        private_key = x25519.X25519PrivateKey.generate()
        public_key = private_key.public_key()

        # Serialize public key for transmission
        public_key_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        )

        # Generate cryptographically random session ID
        session_id = secrets.token_bytes(SESSION_ID_SIZE)

        return SessionKeyPair(
            private_key=private_key,
            public_key=public_key_bytes,
            session_id=session_id,
        )

    def derive_shared_secret(
        self, our_private_key: x25519.X25519PrivateKey, their_public_key: bytes
    ) -> bytes:
        """
        Perform ECDH key exchange and derive shared secret.

        😐 Both parties compute same shared secret from different key pairs.
        🌑 Shared secret is sensitive - use immediately, then zeroize.

        Args:
            our_private_key: Our ephemeral private key
            their_public_key: Peer's public key (32 bytes, raw format)

        Returns:
            32-byte shared secret

        Raises:
            ForwardSecrecyError: If key exchange fails (invalid public key)

        Example:
            >>> # Alice and Bob exchange secrets
            >>> manager = ForwardSecrecyManager()
            >>> alice_kp = manager.generate_session_keypair()
            >>> bob_kp = manager.generate_session_keypair()
            >>>
            >>> alice_secret = manager.derive_shared_secret(
            ...     alice_kp.private_key, bob_kp.public_key
            ... )
            >>> bob_secret = manager.derive_shared_secret(
            ...     bob_kp.private_key, alice_kp.public_key
            ... )
            >>> assert alice_secret == bob_secret
        """
        try:
            # Validate peer public key size
            if len(their_public_key) != SHARED_SECRET_SIZE:
                raise ValueError(
                    f"Peer public key must be {SHARED_SECRET_SIZE} bytes, got {len(their_public_key)}"
                )

            # Deserialize peer's public key
            peer_public_key = x25519.X25519PublicKey.from_public_bytes(
                their_public_key
            )

            # Perform ECDH
            return our_private_key.exchange(peer_public_key)


        except Exception as e:
            raise ForwardSecrecyError(f"ECDH key exchange failed: {e}") from e

    def derive_session_master_key(
        self,
        shared_secret: bytes,
        session_id: bytes,
        context: str = "anemochory-session",
        timestamp: int | None = None,
    ) -> bytes:
        """
        Derive session master key from shared secret using HKDF.

        😐 Binds key to session_id and timestamp for uniqueness.
        🌑 Different session IDs produce different keys from same shared secret.

        Args:
            shared_secret: Output from ECDH (32 bytes)
            session_id: Random session identifier (32 bytes)
            context: Protocol context string (default: "anemochory-session")
            timestamp: Optional Unix timestamp (default: current time)

        Returns:
            32-byte master key for ChaCha20-Poly1305

        Raises:
            ForwardSecrecyError: If key derivation fails

        Example:
            >>> manager = ForwardSecrecyManager()
            >>> shared = secrets.token_bytes(32)
            >>> session_id = secrets.token_bytes(32)
            >>>
            >>> # Different session IDs = different keys
            >>> key1 = manager.derive_session_master_key(shared, session_id)
            >>> key2 = manager.derive_session_master_key(shared, secrets.token_bytes(32))
            >>> assert key1 != key2
        """
        try:
            # Validate inputs
            if len(shared_secret) != SHARED_SECRET_SIZE:
                raise ValueError(
                    f"Shared secret must be {SHARED_SECRET_SIZE} bytes, got {len(shared_secret)}"
                )
            if len(session_id) != SESSION_ID_SIZE:
                raise ValueError(
                    f"Session ID must be {SESSION_ID_SIZE} bytes, got {len(session_id)}"
                )

            # Use current time if not provided
            if timestamp is None:
                timestamp = int(time.time())

            # Construct HKDF info string with session binding
            # Format: "context|session_id_hex|timestamp"  # noqa: ERA001
            info = f"{context}|{session_id.hex()}|{timestamp}".encode()

            # Derive key using HKDF-SHA256
            # Note: salt=None is acceptable here as shared_secret has high entropy
            # 🌑 Future enhancement: Add random salt per session for defense-in-depth
            kdf = HKDF(
                algorithm=hashes.SHA256(),
                length=KEY_SIZE,
                salt=None,  # Optional: could add random salt
                info=info,
            )

            return kdf.derive(shared_secret)


        except Exception as e:
            raise ForwardSecrecyError(f"Key derivation failed: {e}") from e

    @staticmethod
    def serialize_public_key(public_key: x25519.X25519PublicKey) -> bytes:
        """
        Serialize X25519 public key to raw bytes for transmission.

        Args:
            public_key: X25519 public key object

        Returns:
            32-byte raw public key
        """
        return public_key.public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        )

    @staticmethod
    def deserialize_public_key(public_key_bytes: bytes) -> x25519.X25519PublicKey:
        """
        Deserialize raw bytes to X25519 public key object.

        Args:
            public_key_bytes: 32-byte raw public key

        Returns:
            X25519 public key object

        Raises:
            ForwardSecrecyError: If deserialization fails
        """
        try:
            if len(public_key_bytes) != SHARED_SECRET_SIZE:
                raise ValueError(
                    f"Public key must be {SHARED_SECRET_SIZE} bytes, got {len(public_key_bytes)}"
                )
            return x25519.X25519PublicKey.from_public_bytes(public_key_bytes)
        except Exception as e:
            raise ForwardSecrecyError(f"Public key deserialization failed: {e}") from e
