"""
😐 Anemochory Protocol: Node Packet Processing

Implements the server-side logic for processing packets at each hop.
Each AnemochoryNode peels one encryption layer, reads routing info,
and either forwards to the next hop or handles as exit traffic.

🌑 Dark Harold: A node sees ONE layer. It cannot see content or origin.
   That's the whole point. If a node CAN see these, something is very wrong.
"""

from __future__ import annotations

import ipaddress
import logging
import secrets
import time
from dataclasses import dataclass, field
from enum import StrEnum

from anemochory.crypto_replay import ReplayProtectionManager
from anemochory.models import NodeInfo
from anemochory.packet import (
    PACKET_SIZE,
    DecryptionError,
    ReplayError,
    decrypt_layer,
)


logger = logging.getLogger(__name__)


# ============================================================================
# Constants
# ============================================================================

# Timing jitter for traffic analysis resistance
MIN_JITTER_MS = 5  # Minimum random delay before forwarding
MAX_JITTER_MS = 50  # Maximum random delay before forwarding

# Exit node limits
MAX_EXIT_PAYLOAD_SIZE = 8192  # Maximum outbound request payload
EXIT_REQUEST_TIMEOUT = 30.0  # Seconds to wait for external response


# ============================================================================
# Enums & Data Types
# ============================================================================


class PacketAction(StrEnum):
    """What to do after processing a packet."""

    FORWARD = "forward"  # Relay to next hop
    EXIT = "exit"  # Handle as exit traffic
    DROP = "drop"  # Drop packet (invalid/replay)


@dataclass
class ProcessedPacket:
    """
    Result of processing one packet at this node.

    😐 Contains everything the node needs to act on:
    what to do, where to send it, and the data.
    """

    action: PacketAction
    next_address: str | None = None
    next_port: int | None = None
    packet_data: bytes = b""
    payload: bytes = b""  # Only set for EXIT action
    session_id: bytes = b""
    error: str | None = None
    jitter_ms: float = 0.0


@dataclass
class NodeStats:
    """Node processing statistics."""

    packets_processed: int = 0
    packets_forwarded: int = 0
    packets_exited: int = 0
    packets_dropped: int = 0
    replay_attempts: int = 0
    decryption_failures: int = 0
    started_at: float = field(default_factory=time.time)


# ============================================================================
# Node Implementation
# ============================================================================


class AnemochoryNode:
    """
    😐 Processes packets at a single hop in the Anemochory network.

    Each node:
    1. Receives a 1024-byte packet
    2. Decrypts one layer using its layer key
    3. Reads routing info to determine next hop
    4. Forwards to next hop (RELAY) or handles exit (EXIT)
    5. Adds random timing jitter to resist traffic analysis

    🌑 Dark Harold's Security Model:
    - A node sees ONLY its layer key and routing info
    - It cannot determine the sender, the final destination, or the payload
    - It cannot determine its position in the path (by design)
    - Timing jitter breaks timing correlation attacks
    - Replay protection prevents captured packet replay
    """

    def __init__(
        self,
        identity: NodeInfo,
        layer_keys: dict[bytes, bytes] | None = None,
    ) -> None:
        """
        Initialize an Anemochory node.

        Args:
            identity: This node's public identity
            layer_keys: Map of session_id → layer_key for active sessions
                        (in production, populated via key exchange)

        😐 layer_keys is the secret sauce. Guard it with your life.
        🌑 If layer_keys leak, this node's layer is transparent.
        """
        self._identity = identity
        self._layer_keys: dict[bytes, bytes] = layer_keys or {}
        self._replay_manager = ReplayProtectionManager()
        self._stats = NodeStats()

    @property
    def identity(self) -> NodeInfo:
        """This node's public identity."""
        return self._identity

    @property
    def stats(self) -> NodeStats:
        """Processing statistics."""
        return self._stats

    def register_session_key(self, session_id: bytes, layer_key: bytes) -> None:
        """
        Register a layer key for a session.

        Called after key exchange with the sender.

        Args:
            session_id: 16-byte session identifier
            layer_key: 32-byte ChaCha20 key for this hop

        🌑 Keys should be rotated/expired after use.
        """
        self._layer_keys[session_id] = layer_key

    def remove_session_key(self, session_id: bytes) -> None:
        """Remove a session key (session closed or expired)."""
        self._layer_keys.pop(session_id, None)

    def process_packet(
        self,
        packet: bytes,
        session_id: bytes,
        current_time: float | None = None,
    ) -> ProcessedPacket:
        """
        Process one incoming packet.

        Steps:
        1. Look up layer key for this session
        2. Decrypt one layer
        3. Check replay protection
        4. Determine action (forward vs exit)
        5. Calculate timing jitter

        Args:
            packet: Raw 1024-byte packet
            session_id: Session identifier to look up key
            current_time: Override current time (testing)

        Returns:
            ProcessedPacket with action and data

        😐 This function never raises. It returns DROP on errors.
        """
        self._stats.packets_processed += 1

        # Step 1: Look up layer key
        layer_key = self._layer_keys.get(session_id)
        if layer_key is None:
            self._stats.packets_dropped += 1
            return ProcessedPacket(
                action=PacketAction.DROP,
                error=f"Unknown session: {session_id.hex()[:8]}...",
            )

        # Step 2: Validate packet size
        if len(packet) != PACKET_SIZE:
            self._stats.packets_dropped += 1
            return ProcessedPacket(
                action=PacketAction.DROP,
                error=f"Invalid packet size: {len(packet)}",
            )

        # Step 3: Decrypt one layer
        try:
            header, routing_info, inner_data = decrypt_layer(packet, layer_key, current_time)
        except ReplayError as e:
            self._stats.replay_attempts += 1
            self._stats.packets_dropped += 1
            logger.warning("Replay attack detected: %s", e)
            return ProcessedPacket(
                action=PacketAction.DROP,
                error=f"Replay detected: {e}",
            )
        except (DecryptionError, ValueError) as e:
            self._stats.decryption_failures += 1
            self._stats.packets_dropped += 1
            return ProcessedPacket(
                action=PacketAction.DROP,
                error=f"Decryption failed: {e}",
            )

        # Step 4: Check replay using nonce from the decrypted data
        # Use header timestamp + session_id as replay identifier
        replay_id = (
            header.timestamp.to_bytes(4, "big") + session_id + header.layer_index.to_bytes(1, "big")
        )
        if self._replay_manager.is_nonce_seen(replay_id, session_id):
            self._stats.replay_attempts += 1
            self._stats.packets_dropped += 1
            return ProcessedPacket(
                action=PacketAction.DROP,
                error="Replay: duplicate packet",
            )
        self._replay_manager.mark_nonce_seen(replay_id, session_id)

        # Step 5: Calculate timing jitter
        jitter = _calculate_jitter()

        # Step 6: Determine action
        if header.is_final_payload:
            # This is the exit node — inner_data is the final payload
            self._stats.packets_exited += 1
            return ProcessedPacket(
                action=PacketAction.EXIT,
                payload=inner_data,
                session_id=session_id,
                jitter_ms=jitter,
            )

        # Forward to next hop
        next_address = _unpack_address(routing_info.next_hop_address)
        next_port = routing_info.next_hop_port

        if next_port == 0:
            # 🌑 Zero port with non-final flag = malformed packet
            self._stats.packets_dropped += 1
            return ProcessedPacket(
                action=PacketAction.DROP,
                error="Zero port on non-exit routing",
            )

        self._stats.packets_forwarded += 1
        return ProcessedPacket(
            action=PacketAction.FORWARD,
            next_address=next_address,
            next_port=next_port,
            packet_data=inner_data,
            session_id=session_id,
            jitter_ms=jitter,
        )


# ============================================================================
# Exit Node Handler
# ============================================================================


@dataclass
class ExitResponse:
    """Response from exit node processing."""

    success: bool
    payload: bytes = b""
    error: str | None = None
    status_code: int = 0


class ExitNodeHandler:
    """
    😐 Handles traffic exiting the Anemochory network.

    The exit node is the last hop — it decrypts the final payload
    and executes the request (HTTP, DNS, etc.) on behalf of the sender.

    🌑 Dark Harold: The exit node sees the payload content but NOT
    the sender's identity. This is the design trade-off.
    Exit nodes should be operated by trusted parties.

    For MVP: Only handles raw payloads (returns them as-is).
    HTTP tunneling will be added in Phase 2.
    """

    def __init__(self) -> None:
        """Initialize exit handler."""
        self._requests_handled = 0
        self._requests_failed = 0

    @property
    def stats(self) -> dict[str, int]:
        """Handler statistics."""
        return {
            "handled": self._requests_handled,
            "failed": self._requests_failed,
        }

    def handle_payload(self, payload: bytes) -> ExitResponse:
        """
        Process an exiting payload.

        For MVP, this is a passthrough — the payload is returned as-is.
        In production, this would parse the payload as an HTTP request,
        execute it, and return the response.

        Args:
            payload: Decrypted final payload

        Returns:
            ExitResponse with the result
        """
        if not payload:
            self._requests_failed += 1
            return ExitResponse(
                success=False,
                error="Empty payload",
            )

        if len(payload) > MAX_EXIT_PAYLOAD_SIZE:
            self._requests_failed += 1
            return ExitResponse(
                success=False,
                error=f"Payload too large: {len(payload)} bytes (max {MAX_EXIT_PAYLOAD_SIZE})",
            )

        self._requests_handled += 1
        # 😐 MVP: Echo payload back. Real implementation would execute HTTP.
        return ExitResponse(
            success=True,
            payload=payload,
            status_code=200,
        )


# ============================================================================
# Utilities
# ============================================================================


def _calculate_jitter() -> float:
    """
    Calculate random timing jitter in milliseconds.

    🌑 Timing jitter breaks correlation between incoming and
    outgoing packets. Without it, an observer can match
    packets by timing alone.
    """
    return MIN_JITTER_MS + secrets.randbelow(MAX_JITTER_MS - MIN_JITTER_MS + 1)


def _unpack_address(address_bytes: bytes) -> str:
    """
    Unpack 16-byte address to string.

    Inverse of routing._pack_address.
    """
    if len(address_bytes) != 16:
        msg = f"Address must be 16 bytes, got {len(address_bytes)}"
        raise ValueError(msg)

    # Check if IPv4 (last 12 bytes are zero)
    if address_bytes[4:] == b"\x00" * 12:
        return str(ipaddress.IPv4Address(address_bytes[:4]))

    return str(ipaddress.IPv6Address(address_bytes))
