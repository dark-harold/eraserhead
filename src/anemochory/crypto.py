"""
😐 Anemochory Protocol - Cryptographic Primitives

Multi-layer packet encryption using ChaCha20-Poly1305 AEAD cipher.
Implements secure key derivation, nonce generation, and encryption/decryption.

🌑 Dark Harold's Reminder: Every line of crypto code is a potential CVE.
    - NEVER reuse nonces
    - NEVER reuse keys across layers
    - ALWAYS use secrets module for randomness
    - ALL crypto code reviewed by harold-security (Opus 4.6)

References:
    - ADR-001: Cryptographic Primitive Selection
    - RFC 8439: ChaCha20 and Poly1305 for IETF Protocols
"""

from __future__ import annotations

import secrets
import struct
from typing import Protocol

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


# 😐 Constants (harold-security approved)
KEY_SIZE = 32  # ChaCha20 requires 32-byte keys
NONCE_SIZE = 12  # ChaCha20-Poly1305 requires 12-byte (96-bit) nonces
AUTH_TAG_SIZE = 16  # Poly1305 produces 16-byte authentication tags
DEFAULT_PACKET_SIZE = 1024  # Default padded packet size (bytes)


class CryptographicError(Exception):
    """Base class for all cryptographic errors.

    😐 Something went wrong with the crypto. Harold is not surprised.
    """


class EncryptionError(CryptographicError):
    """Raised when encryption fails.

    😐 This shouldn't happen unless you're doing something wrong.
    """

    pass


class DecryptionError(CryptographicError):
    """Raised when decryption or authentication fails.

    🌑 Dark Harold: Authentication failure means tampering.
        Drop the packet. Log the event. Suspect compromise.
    """

    pass


class CryptoEngine(Protocol):
    """Protocol for encryption engines.

    Defines interface that all crypto implementations must follow.
    Enables swapping ChaCha20-Poly1305 for AES-GCM if needed.

    😐 harold-planner's architectural paranoia: Design for change.
    """

    def encrypt(self, plaintext: bytes) -> tuple[bytes, bytes]:
        """Encrypt plaintext.

        Args:
            plaintext: Data to encrypt

        Returns:
            Tuple of (nonce, ciphertext) where ciphertext includes auth tag

        Raises:
            EncryptionError: If encryption fails
        """
        ...

    def decrypt(self, nonce: bytes, ciphertext: bytes) -> bytes:
        """Decrypt and authenticate ciphertext.

        Args:
            nonce: Nonce used during encryption
            ciphertext: Encrypted data including auth tag

        Returns:
            Decrypted plaintext

        Raises:
            DecryptionError: If decryption or authentication fails
        """
        ...


class ChaCha20Engine:
    """ChaCha20-Poly1305 AEAD encryption engine.

    Implements RFC 8439 authenticated encryption.
    Each engine instance is bound to a single layer key.

    Security Properties:
        - AEAD: Confidentiality + authenticity in single operation
        - Nonce: Random 96-bit nonce per encryption (NEVER reused)
        - Key: 256-bit key unique per layer
        - Constant-time: Resists timing attacks

    Example:
        >>> key = ChaCha20Engine.generate_key()
        >>> engine = ChaCha20Engine(key)
        >>> nonce, ciphertext = engine.encrypt(b"secret packet data")
        >>> plaintext = engine.decrypt(nonce, ciphertext)
        >>> assert plaintext == b"secret packet data"

    😐 harold-implementer: Simple API. Hard to misuse. Dark Harold approved.
    """

    def __init__(self, layer_key: bytes) -> None:
        """Initialize encryption engine with layer-specific key.

        Args:
            layer_key: 32-byte encryption key for this layer

        Raises:
            ValueError: If key size is incorrect

        🌑 Dark Harold: One key per layer. Never reuse keys.
        """
        if len(layer_key) != KEY_SIZE:
            raise ValueError(f"Layer key must be {KEY_SIZE} bytes, got {len(layer_key)}")

        self._cipher = ChaCha20Poly1305(layer_key)
        # 😐 Note: layer_key is NOT stored (cipher stores it internally)
        # This prevents accidental key exposure in logs/debugger

    @staticmethod
    def generate_key() -> bytes:
        """Generate a secure random 32-byte key.

        Returns:
            32-byte key suitable for ChaCha20-Poly1305

        🌑 Dark Harold: Uses secrets module. Random module is FORBIDDEN.
        """
        return secrets.token_bytes(KEY_SIZE)

    def encrypt(self, plaintext: bytes) -> tuple[bytes, bytes]:
        """Encrypt plaintext with random nonce.

        Args:
            plaintext: Data to encrypt (any length)

        Returns:
            Tuple of (nonce, ciphertext) where:
                - nonce: 12-byte random nonce
                - ciphertext: encrypted data + 16-byte auth tag

        Raises:
            EncryptionError: If encryption fails

        Security:
            - Nonce is generated randomly (NEVER reused)
            - Ciphertext includes Poly1305 authentication tag
            - Tampering detected during decryption

        😐 harold-tester: Test that nonces are unique across calls!
        """
        try:
            # Generate random nonce (😐 every time, never reuse)
            nonce = secrets.token_bytes(NONCE_SIZE)

            # Encrypt: plaintext → ciphertext + auth_tag (combined)
            ciphertext_with_tag = self._cipher.encrypt(
                nonce=nonce,
                data=plaintext,
                associated_data=None,  # 🌑 Could add packet metadata here
            )

            return (nonce, ciphertext_with_tag)

        except Exception as e:
            # 😐 This shouldn't happen, but Dark Harold insists on handling it
            raise EncryptionError(f"ChaCha20-Poly1305 encryption failed: {e}") from e

    def decrypt(self, nonce: bytes, ciphertext: bytes) -> bytes:
        """Decrypt and verify authenticity of ciphertext.

        Args:
            nonce: 12-byte nonce used during encryption
            ciphertext: Encrypted data including 16-byte auth tag

        Returns:
            Decrypted plaintext

        Raises:
            DecryptionError: If authentication fails (tampered packet)
            ValueError: If nonce size is incorrect

        Security:
            - Authentication verified before returning plaintext
            - Tampered packets raise DecryptionError
            - Constant-time comparison (timing-attack resistant)

        🌑 Dark Harold: Authentication failure means DROP THE PACKET.
            Log the event. Investigate the source. Suspect everything.
        """
        if len(nonce) != NONCE_SIZE:
            raise ValueError(f"Nonce must be {NONCE_SIZE} bytes, got {len(nonce)}")

        if len(ciphertext) < AUTH_TAG_SIZE:
            raise DecryptionError(
                f"Ciphertext too short (need at least {AUTH_TAG_SIZE} bytes "
                f"for auth tag), got {len(ciphertext)}"
            )

        try:
            # Decrypt + verify authentication tag
            return self._cipher.decrypt(nonce=nonce, data=ciphertext, associated_data=None)

        except InvalidTag as e:
            # 🌑 Authentication failed: packet was tampered with
            raise DecryptionError("Authentication failed: packet tampered or corrupted") from e
        except Exception as e:
            # 😐 Other decryption errors
            raise DecryptionError(f"ChaCha20-Poly1305 decryption failed: {e}") from e


def derive_layer_key(master_key: bytes, layer_index: int, total_layers: int) -> bytes:
    """Derive unique encryption key for a specific layer.

    Uses HKDF (HMAC-based Key Derivation Function) to derive layer-specific
    keys from a master key. Each layer gets a cryptographically independent key.

    Args:
        master_key: Master secret key (any length, recommend 32+ bytes)
        layer_index: Zero-based layer index (0 = outermost layer)
        total_layers: Total number of layers in the packet

    Returns:
        32-byte derived key for this layer

    Raises:
        ValueError: If layer_index >= total_layers

    Example:
        >>> master = ChaCha20Engine.generate_key()
        >>> layer_0_key = derive_layer_key(master, 0, 5)  # Outermost
        >>> layer_4_key = derive_layer_key(master, 4, 5)  # Innermost
        >>> assert layer_0_key != layer_4_key  # Keys are independent

    Security:
        - Each layer key is cryptographically independent
        - Knowledge of one layer key doesn't reveal others
        - Changing total_layers changes all derived keys (binding)

    🌑 Dark Harold: One key per layer. Never reuse the master key directly.
        If you encrypt with master_key, I will find you. And I will be
        disappointed. Which is worse than being found.
    """
    if layer_index >= total_layers:
        raise ValueError(f"layer_index ({layer_index}) must be < total_layers ({total_layers})")

    # Context info binds key to specific layer and hop count
    # 😐 Including total_layers prevents layer confusion attacks
    info = f"anemochory-layer-{layer_index}-of-{total_layers}".encode()

    # HKDF with SHA-256 (😐 Could use SHA-512 for extra paranoia, but SHA-256 sufficient)
    kdf = HKDF(
        algorithm=hashes.SHA256(),
        length=KEY_SIZE,  # Output: 32 bytes for ChaCha20
        salt=None,  # 🌑 Optional: could add random salt for extra security
        info=info,
    )

    return kdf.derive(master_key)


def pad_packet(data: bytes, target_size: int = DEFAULT_PACKET_SIZE) -> bytes:
    """Pad packet to constant size (traffic analysis resistance).

    Pads data to a fixed size using random padding. Prevents size-based
    correlation attacks where packet sizes leak information about content.

    Args:
        data: Packet data to pad
        target_size: Target padded size in bytes (default: 1024)

    Returns:
        Padded packet: [2-byte length][data][random padding]

    Raises:
        ValueError: If data exceeds target_size

    Format:
        Byte 0-1: uint16 big-endian original data length
        Byte 2...: Original data
        Remaining: Random padding (cryptographically secure)

    Example:
        >>> data = b"secret"
        >>> padded = pad_packet(data, target_size=64)
        >>> assert len(padded) == 64
        >>> unpadded = unpad_packet(padded)
        >>> assert unpadded == b"secret"

    Security:
        - Random padding (not zeros) prevents pattern detection
        - Constant size across all packets resists size correlation
        - Length prefix enables unambiguous unpadding

    🌑 Dark Harold: Variable-length packets leak information.
        Constant padding is REQUIRED for all anonymized packets.
        Think I'm paranoid? Good. You're learning.
    """
    if len(data) > target_size - 2:  # Need 2 bytes for length prefix
        raise ValueError(
            f"Data too large ({len(data)} bytes) for target size ({target_size} bytes)"
        )

    # Calculate padding needed
    padding_size = target_size - len(data) - 2  # 2 bytes for length prefix

    # Generate random padding (😐 NOT zeros, that would be a pattern)
    padding = secrets.token_bytes(padding_size)

    # Format: [2-byte length][data][random padding]
    length_prefix = struct.pack(">H", len(data))  # Big-endian uint16

    return length_prefix + data + padding


def unpad_packet(padded: bytes) -> bytes:
    """Remove padding from constant-size packet.

    Extracts original data from padded packet.

    Args:
        padded: Padded packet from pad_packet()

    Returns:
        Original unpadded data

    Raises:
        ValueError: If packet format is invalid

    😐 harold-tester: Test with malformed packets (wrong length prefix)!
    """
    if len(padded) < 2:
        raise ValueError("Padded packet too short (need at least 2 bytes for length)")

    # Extract length prefix
    data_length = struct.unpack(">H", padded[:2])[0]

    # Validate length
    if data_length > len(padded) - 2:
        raise ValueError(
            f"Invalid length prefix ({data_length}) exceeds packet size "
            f"({len(padded) - 2} bytes after prefix)"
        )

    # Extract original data (skip 2-byte prefix, take data_length bytes)
    return padded[2 : 2 + data_length]


# 😐 harold-implementer's closing thoughts:
# - ChaCha20-Poly1305 is fast and secure
# - API is simple and hard to misuse
# - Nonce generation is cryptographically secure
# - Key derivation prevents layer key reuse
# - Packet padding resists traffic analysis
#
# 🌑 Dark Harold's exit interview:
# - Every encryption is a potential failure point
# - Nonce reuse is catastrophic (test for it)
# - Key leakage is catastrophic (never log keys)
# - Timing attacks are real (use constant-time operations)
# - This module will be reviewed by harold-security before Week 6
# - If you modify this file, harold-security reviews again
# - No exceptions. No shortcuts. Security is not negotiable.
