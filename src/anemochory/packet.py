"""
😐 Anemochory Protocol: Packet Format Implementation

Nested onion packet structure with multi-layer encryption, replay protection,
and traffic analysis resistance.

Based on: specs/001-anemochory-protocol/ADR-002-packet-format.md
Security: Addresses SECURITY-REVIEW-CRYPTO.md Critical Issues #2, #5
"""

from __future__ import annotations

import secrets
import struct
import time
from dataclasses import dataclass
from enum import IntEnum

from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

# Import crypto primitives
from anemochory.crypto import (
    AUTH_TAG_SIZE,
    KEY_SIZE,
    NONCE_SIZE,
    CryptographicError,
)


# ============================================================================
# Protocol Constants
# ============================================================================

# Packet structure sizes
PACKET_SIZE = 1024  # Total packet size (constant for traffic analysis resistance)
HEADER_SIZE = 8  # Unencrypted header
ROUTING_INFO_SIZE = 44  # Routing information per layer (16+2+8+16+2)

# Derived sizes
ENCRYPTED_PAYLOAD_SIZE = PACKET_SIZE - HEADER_SIZE  # 1016 bytes
INNER_PACKET_SIZE = (
    ENCRYPTED_PAYLOAD_SIZE - NONCE_SIZE - ROUTING_INFO_SIZE - AUTH_TAG_SIZE
)  # 944 bytes (inner data after peeling outermost layer)

# Layer overhead (encryption + routing per layer)
LAYER_OVERHEAD = NONCE_SIZE + ROUTING_INFO_SIZE + AUTH_TAG_SIZE  # 72 bytes per layer

# Protocol limits
MIN_HOPS = 3  # Minimum path length for anonymity
MAX_HOPS = 7  # Maximum path length (conservative limit)
MAX_PAYLOAD_SIZE = INNER_PACKET_SIZE - (
    LAYER_OVERHEAD * (MAX_HOPS - 1)
)  # 512 bytes for 7-hop

# Security constraints
MAX_PACKET_AGE_SECONDS = 60  # Replay protection window
MAX_CLOCK_SKEW_SECONDS = 5  # Tolerance for clock differences


# ============================================================================
# Protocol Enums
# ============================================================================


class AddressType(IntEnum):
    """Network address types supported in routing."""

    IPV4 = 0x01  # IPv4 (mapped to IPv6)
    IPV6 = 0x02  # IPv6
    ONION_V3 = 0x03  # Tor-like onion address


class PacketFlags(IntEnum):
    """Bit flags in packet header."""

    IS_FINAL_PAYLOAD = 0x01  # Bit 0: Last hop (contains final payload)
    REQUIRES_ACK = 0x02  # Bit 1: Reliability (future feature)
    # Bits 2-7: Reserved (must be 0)


# ============================================================================
# Data Structures
# ============================================================================


@dataclass
class PacketHeader:
    """
    Unencrypted packet header (8 bytes).

    😐 The only part visible to all hops. Keep it minimal.
    """

    version: int  # Protocol version (1 byte, currently 0x01)
    hop_count: int  # Total hops in path (1 byte, 3-7)
    layer_index: int  # Current layer (1 byte, N down to 1)
    flags: int  # Bit flags (1 byte, see PacketFlags)
    timestamp: int  # Unix epoch seconds (4 bytes, network byte order)

    def __post_init__(self):
        """Validate header fields."""
        if not 0 <= self.version <= 0xFF:
            raise ValueError(f"Invalid version: {self.version}")
        if not MIN_HOPS <= self.hop_count <= MAX_HOPS:
            raise ValueError(f"Invalid hop_count: {self.hop_count}")
        if not 1 <= self.layer_index <= self.hop_count:
            raise ValueError(
                f"Invalid layer_index {self.layer_index} for hop_count {self.hop_count}"
            )
        if not 0 <= self.flags <= 0xFF:
            raise ValueError(f"Invalid flags: {self.flags}")

    @property
    def is_final_payload(self) -> bool:
        """Check if this is the final hop."""
        return bool(self.flags & PacketFlags.IS_FINAL_PAYLOAD)

    def to_bytes(self) -> bytes:
        """Serialize header to 8 bytes."""
        return struct.pack(
            ">BBBBL",  # Big-endian: 4 bytes + 1 long (4 bytes)
            self.version,
            self.hop_count,
            self.layer_index,
            self.flags,
            self.timestamp,
        )

    @staticmethod
    def from_bytes(data: bytes) -> PacketHeader:
        """Deserialize header from 8 bytes."""
        if len(data) != HEADER_SIZE:
            raise ValueError(f"Invalid header size: {len(data)} (expected {HEADER_SIZE})")

        version, hop_count, layer_index, flags, timestamp = struct.unpack(">BBBBL", data)
        return PacketHeader(
            version=version,
            hop_count=hop_count,
            layer_index=layer_index,
            flags=flags,
            timestamp=timestamp,
        )


@dataclass
class LayerRoutingInfo:
    """
    Per-layer routing information (encrypted, 56 bytes).

    🌑 This tells each hop where to forward. Never visible to other hops.
    """

    next_hop_address: bytes  # IPv6 or onion address (16 bytes)
    next_hop_port: int  # Destination port (2 bytes)
    sequence_number: int  # Per-session sequence (8 bytes)
    session_id: bytes  # Session identifier UUID (16 bytes)
    padding_length: int  # Final payload padding (2 bytes, 0 for intermediate hops)

    def __post_init__(self):
        """Validate routing info fields."""
        if len(self.next_hop_address) != 16:
            raise ValueError(
                f"Invalid address length: {len(self.next_hop_address)} (expected 16)"
            )
        if not 0 <= self.next_hop_port <= 65535:
            raise ValueError(f"Invalid port: {self.next_hop_port}")
        if not 0 <= self.sequence_number < 2**64:
            raise ValueError(f"Invalid sequence_number: {self.sequence_number}")
        if len(self.session_id) != 16:
            raise ValueError(
                f"Invalid session_id length: {len(self.session_id)} (expected 16)"
            )
        if not 0 <= self.padding_length < INNER_PACKET_SIZE:
            raise ValueError(f"Invalid padding_length: {self.padding_length}")

    def to_bytes(self) -> bytes:
        """Serialize routing info to 44 bytes."""
        return struct.pack(
            ">16sHQ16sH",  # address(16) + port(2) + seq(8) + session(16) + padding(2)
            self.next_hop_address,
            self.next_hop_port,
            self.sequence_number,
            self.session_id,
            self.padding_length,
        )

    @staticmethod
    def from_bytes(data: bytes) -> LayerRoutingInfo:
        """Deserialize routing info from 44 bytes."""
        if len(data) != ROUTING_INFO_SIZE:
            raise ValueError(
                f"Invalid routing info size: {len(data)} (expected {ROUTING_INFO_SIZE})"
            )

        address, port, seq, session, padding = struct.unpack(">16sHQ16sH", data)
        return LayerRoutingInfo(
            next_hop_address=address,
            next_hop_port=port,
            sequence_number=seq,
            session_id=session,
            padding_length=padding,
        )


# ============================================================================
# Packet Construction (Sender)
# ============================================================================


def build_onion_packet(
    payload: bytes,
    path: list[tuple[bytes, LayerRoutingInfo]],  # (layer_key, routing_info) per hop
    _session_id: bytes,  # Reserved for future key derivation
    base_sequence: int = 0,
) -> bytes:
    """
    Build a complete onion packet for multi-hop routing.

    😐 The sender's job: wrap the payload in N layers of encryption.
    Each hop peels one layer. Like an onion, but with more math.

    Args:
        payload: Final payload data (max 440 bytes for 7-hop path)
        path: List of (layer_key, routing_info) tuples from innermost to outermost
        session_id: Session identifier for key derivation
        base_sequence: Starting sequence number

    Returns:
        Complete 1024-byte encrypted packet

    Raises:
        ValueError: If path length invalid or payload too large
        CryptographicError: If encryption fails

    🌑 Security Note: Each layer is independently encrypted with unique nonce.
    Nonce collision = catastrophic. We check for it.
    """
    hop_count = len(path)
    if not MIN_HOPS <= hop_count <= MAX_HOPS:
        raise ValueError(f"Invalid path length: {hop_count} (must be {MIN_HOPS}-{MAX_HOPS})")

    # Calculate maximum payload size for this path
    max_payload = calculate_max_payload_size(hop_count)
    if len(payload) > max_payload:
        raise ValueError(
            f"Payload too large: {len(payload)} bytes (max {max_payload} for {hop_count} hops)"
        )

    # Timestamp for entire packet (used across all layers)
    timestamp = int(time.time())

    # Start with payload, pad to max payload size for this hop count
    # 😐 Only the innermost layer gets padding. Outer layers wrap as-is.
    padding_needed = max_payload - len(payload)
    padding = secrets.token_bytes(padding_needed)
    current_data = payload + padding

    seen_nonces: set[bytes] = set()

    # Encrypt layers from innermost (layer 1) to outermost (layer N)
    for layer_idx in range(hop_count):
        layer_number = layer_idx + 1  # Layer 1, 2, ..., N
        layer_key, routing_info = path[layer_idx]

        # Update sequence number for this layer
        routing_info.sequence_number = base_sequence + layer_idx

        # Store padding length for final payload layer only
        if layer_idx == 0:
            routing_info.padding_length = padding_needed

        # Serialize routing info
        routing_bytes = routing_info.to_bytes()

        # Construct plaintext: routing_info + current_data
        plaintext = routing_bytes + current_data

        # Generate unique nonce with collision detection
        nonce = _generate_unique_nonce(seen_nonces)

        # Associated data: layer_number binds this encryption to its position
        # 🌑 Prevents layer stripping, confusion, and replay with modified hop count
        associated_data = struct.pack(">BBL", layer_number, hop_count, timestamp)

        # Encrypt with ChaCha20-Poly1305
        cipher = ChaCha20Poly1305(layer_key)
        try:
            ciphertext_with_tag = cipher.encrypt(nonce, plaintext, associated_data)
        except Exception as e:
            raise CryptographicError(f"Encryption failed: {e}") from e

        # Encrypted output becomes input for next layer
        current_data = nonce + ciphertext_with_tag

    # Verify outermost encrypted data is ENCRYPTED_PAYLOAD_SIZE
    if len(current_data) != ENCRYPTED_PAYLOAD_SIZE:
        raise CryptographicError(
            f"Invalid encrypted payload size: {len(current_data)} "
            f"(expected {ENCRYPTED_PAYLOAD_SIZE})"
        )

    # Construct final packet header
    header = PacketHeader(
        version=0x01,
        hop_count=hop_count,
        layer_index=hop_count,  # Outermost layer
        flags=PacketFlags.IS_FINAL_PAYLOAD if hop_count == 1 else 0,
        timestamp=timestamp,
    )

    # Assemble complete packet
    full_packet = header.to_bytes() + current_data

    if len(full_packet) != PACKET_SIZE:
        raise CryptographicError(
            f"Invalid packet size: {len(full_packet)} (expected {PACKET_SIZE})"
        )

    return full_packet


def _generate_unique_nonce(seen_nonces: set[bytes]) -> bytes:
    """
    Generate a unique nonce with collision detection.

    🌑 Nonce reuse = catastrophic for ChaCha20-Poly1305. We check.
    """
    max_attempts = 10
    for _ in range(max_attempts):
        nonce = secrets.token_bytes(NONCE_SIZE)
        if nonce not in seen_nonces:
            seen_nonces.add(nonce)
            return nonce
    raise CryptographicError(
        "Nonce collision after 10 attempts - RNG may be compromised"
    )


# ============================================================================
# Packet Processing (Receiver)
# ============================================================================


class PacketError(Exception):
    """Base exception for packet processing errors."""

    pass


class ReplayError(PacketError):
    """Packet timestamp outside valid window (replay attack detected)."""

    pass


class DecryptionError(PacketError):
    """Decryption or authentication failure."""

    pass


def decrypt_layer(
    packet: bytes,
    layer_key: bytes,
    current_time: float | None = None,
) -> tuple[PacketHeader, LayerRoutingInfo, bytes]:
    """
    Decrypt one layer of the onion packet.

    😐 Each node peels one layer, extracts routing info, forwards the rest.
    🌑 VALIDATE EVERYTHING. Trust NOTHING. Nation-state adversaries watch.

    Args:
        packet: Full 1024-byte packet
        layer_key: Decryption key for this layer
        current_time: Current Unix timestamp (defaults to time.time())

    Returns:
        Tuple of (header, routing_info, next_packet_or_payload)

    Raises:
        ReplayError: If timestamp outside valid window
        DecryptionError: If authentication fails or packet malformed
        ValueError: If packet structure invalid
    """
    if len(packet) != PACKET_SIZE:
        raise ValueError(f"Invalid packet size: {len(packet)} (expected {PACKET_SIZE})")

    if len(layer_key) != KEY_SIZE:
        raise ValueError(f"Invalid key size: {len(layer_key)} (expected {KEY_SIZE})")

    # Parse unencrypted header
    try:
        header = PacketHeader.from_bytes(packet[:HEADER_SIZE])
    except Exception as e:
        raise DecryptionError(f"Invalid packet header: {e}") from e

    # Validate timestamp (replay protection - Critical Issue #2)
    if current_time is None:
        current_time = time.time()

    packet_age = current_time - header.timestamp
    if packet_age > MAX_PACKET_AGE_SECONDS:
        raise ReplayError(
            f"Packet too old: {packet_age:.1f}s (max {MAX_PACKET_AGE_SECONDS}s)"
        )
    if packet_age < -MAX_CLOCK_SKEW_SECONDS:
        raise ReplayError(
            f"Packet from future: {-packet_age:.1f}s (max skew {MAX_CLOCK_SKEW_SECONDS}s)"
        )

    # Extract body (may include padding from previous hops)
    body = packet[HEADER_SIZE:]

    # Compute how much of the body is real encrypted content
    # 🌑 Each peeled layer reduces the encrypted size by LAYER_OVERHEAD
    layers_already_peeled = header.hop_count - header.layer_index
    real_encrypted_size = ENCRYPTED_PAYLOAD_SIZE - layers_already_peeled * LAYER_OVERHEAD

    if real_encrypted_size < NONCE_SIZE + ROUTING_INFO_SIZE + AUTH_TAG_SIZE:
        raise DecryptionError("Encrypted content too small for valid layer")

    encrypted_content = body[:real_encrypted_size]

    # Extract nonce and ciphertext
    nonce = encrypted_content[:NONCE_SIZE]
    ciphertext_with_tag = encrypted_content[NONCE_SIZE:]

    # Reconstruct associated data (layer_index binds to position)
    associated_data = struct.pack(
        ">BBL", header.layer_index, header.hop_count, header.timestamp
    )

    # Decrypt with ChaCha20-Poly1305
    cipher = ChaCha20Poly1305(layer_key)
    try:
        plaintext = cipher.decrypt(nonce, ciphertext_with_tag, associated_data)
    except Exception as e:
        # Authentication tag verification failed - tampering or wrong key
        raise DecryptionError(f"Decryption failed: {e}") from e

    # Parse routing information
    try:
        routing_info = LayerRoutingInfo.from_bytes(plaintext[:ROUTING_INFO_SIZE])
    except Exception as e:
        raise DecryptionError(f"Invalid routing info: {e}") from e

    # Extract inner data (next layer's encrypted content or final payload)
    inner_data = plaintext[ROUTING_INFO_SIZE:]

    # Check if final hop
    if header.is_final_payload:
        # Remove padding from final payload
        if routing_info.padding_length > len(inner_data):
            raise DecryptionError(
                f"Invalid padding length: {routing_info.padding_length} > {len(inner_data)}"
            )

        payload_length = len(inner_data) - routing_info.padding_length
        final_payload = inner_data[:payload_length]

        return header, routing_info, final_payload

    # Construct next packet for forwarding
    # 😐 Pad inner_data to ENCRYPTED_PAYLOAD_SIZE for constant packet size
    next_header = PacketHeader(
        version=header.version,
        hop_count=header.hop_count,
        layer_index=header.layer_index - 1,
        flags=PacketFlags.IS_FINAL_PAYLOAD
        if header.layer_index == 2
        else 0,  # Mark next hop as final if we're second-to-last
        timestamp=header.timestamp,  # Preserve original timestamp
    )

    # Pad body to maintain constant 1024-byte packet size
    # 🌑 Random padding prevents traffic analysis based on body size
    padding_needed = ENCRYPTED_PAYLOAD_SIZE - len(inner_data)
    padded_body = inner_data + secrets.token_bytes(padding_needed)

    next_packet = next_header.to_bytes() + padded_body

    if len(next_packet) != PACKET_SIZE:
        raise DecryptionError(f"Invalid next packet size: {len(next_packet)}")

    return header, routing_info, next_packet


# ============================================================================
# Utilities
# ============================================================================


def generate_session_id() -> bytes:
    """
    Generate a cryptographically random session ID.

    😐 UUID v4 equivalent: 16 random bytes.
    🌑 Used for ephemeral key derivation (forward secrecy).
    """
    return secrets.token_bytes(16)


def validate_packet_size(packet: bytes) -> bool:
    """Verify packet is exactly 1024 bytes (traffic analysis resistance)."""
    return len(packet) == PACKET_SIZE


def calculate_max_payload_size(hop_count: int) -> int:
    """
    Calculate maximum payload size for given hop count.

    Args:
        hop_count: Number of hops (3-7)

    Returns:
        Maximum payload size in bytes
    """
    if not MIN_HOPS <= hop_count <= MAX_HOPS:
        raise ValueError(f"Invalid hop_count: {hop_count}")

    return INNER_PACKET_SIZE - (LAYER_OVERHEAD * (hop_count - 1))


# ============================================================================
# 😐 Harold's Packet Implementation Notes
# ============================================================================

"""
Dark Harold's Security Observations 🌑:

1. **Nonce Uniqueness**: We generate nonces with secrets.token_bytes() and check
   for collisions. Birthday paradox says ~2^48 encryptions before 50% collision
   probability. We enforce uniqueness anyway. Paranoia saves lives.

2. **Timestamp Replay Protection**: 60-second window is tight enough to prevent
   long-term replay but loose enough for real network conditions. Clock skew
   tolerance of 5 seconds handles NTP drift. Nation-states can't replay packets
   from yesterday's traffic dump.

3. **Associated Data Binding**: layer_index + hop_count + timestamp bound via
   AEAD prevents:
   - Layer stripping (can't remove outer layers)
   - Layer confusion (can't swap layers between packets)
   - Replay with modified hop count

4. **Constant Packet Size**: Every packet is exactly 1024 bytes. Small payloads
   get padded with random bytes. Traffic analysis harder when all packets look
   identical. Welcome to anonymity engineering.

5. **Forward Secrecy Ready**: session_id field enables ephemeral key derivation
   (Week 5 implementation). Master key compromise won't expose historical traffic.

Status: Implements packet format per ADR-002.
Next: routing.py (path selection), then ephemeral key exchange (Week 5).

If this code fails catastrophically, at least the errors will be well-documented.
"""
