"""
😐 Anemochory Protocol: Network Transport Layer

Trio-native async TCP transport for packet forwarding between nodes.
Handles connection management, packet framing, and graceful shutdown.

🌑 Dark Harold: The network layer is where packets meet the real world.
   Every connection is a potential surveillance point. Every byte is observed.
   Constant packet size + timing jitter = our only weapons here.
"""

from __future__ import annotations

import logging
import struct
from dataclasses import dataclass, field

import trio

from anemochory.node import AnemochoryNode, PacketAction, ProcessedPacket
from anemochory.packet import PACKET_SIZE


logger = logging.getLogger(__name__)


# ============================================================================
# Constants
# ============================================================================

# Framing: 4-byte length prefix + 16-byte session_id + packet
FRAME_HEADER_SIZE = 4 + 16  # uint32 length + session_id
DEFAULT_LISTEN_PORT = 8000
MAX_CONNECTIONS = 100
CONNECTION_TIMEOUT = 30.0  # Seconds before idle connection dropped
READ_TIMEOUT = 60.0  # Seconds to wait for a complete frame


# ============================================================================
# Exceptions
# ============================================================================


class TransportError(Exception):
    """Base transport error."""


class ConnectionLimitError(TransportError):
    """Too many concurrent connections."""


class FramingError(TransportError):
    """Invalid packet framing."""


# ============================================================================
# Packet Framing
# ============================================================================


def frame_packet(packet: bytes, session_id: bytes) -> bytes:
    """
    Frame a packet for TCP transmission.

    Format: [4-byte length][16-byte session_id][packet_data]

    😐 TCP is a stream protocol. We need framing to know where
    packets start and end. The length prefix handles that.
    """
    if len(session_id) != 16:
        msg = f"session_id must be 16 bytes, got {len(session_id)}"
        raise ValueError(msg)
    payload = session_id + packet
    return struct.pack(">I", len(payload)) + payload


async def read_framed_packet(stream: trio.SocketStream) -> tuple[bytes, bytes]:
    """
    Read one framed packet from a trio stream.

    Returns:
        (session_id, packet_data)

    Raises:
        FramingError: If frame is malformed
        trio.EndOfChannel: If connection closed
    """
    # Read 4-byte length prefix
    length_bytes = await _read_exactly(stream, 4)
    if len(length_bytes) < 4:
        raise FramingError("Connection closed during length read")

    frame_length = struct.unpack(">I", length_bytes)[0]

    if frame_length < 16:
        raise FramingError(f"Frame too short: {frame_length} bytes")
    if frame_length > PACKET_SIZE + 16:
        raise FramingError(f"Frame too large: {frame_length} bytes")

    # Read session_id + packet
    frame_data = await _read_exactly(stream, frame_length)
    if len(frame_data) < frame_length:
        raise FramingError("Connection closed during frame read")

    session_id = frame_data[:16]
    packet_data = frame_data[16:]

    return session_id, packet_data


async def _read_exactly(stream: trio.SocketStream, n: int) -> bytes:
    """Read exactly n bytes from stream."""
    data = bytearray()
    while len(data) < n:
        try:
            chunk = await stream.receive_some(n - len(data))
        except trio.ClosedResourceError:
            break
        if not chunk:
            break
        data.extend(chunk)
    return bytes(data)


# ============================================================================
# Node Server
# ============================================================================


@dataclass
class ServerStats:
    """Server operational statistics."""

    connections_accepted: int = 0
    connections_active: int = 0
    packets_received: int = 0
    packets_forwarded: int = 0
    errors: int = 0
    started_at: float = 0.0


class NodeServer:
    """
    😐 TCP server for an Anemochory node.

    Listens for incoming packets, processes them through AnemochoryNode,
    and forwards to next hops or handles as exit traffic.

    Uses trio for async I/O with structured concurrency.

    🌑 Dark Harold: Each connection reveals timing. Each packet reveals size.
    Our constant-size packets + jitter mitigate but don't eliminate this.
    """

    def __init__(
        self,
        node: AnemochoryNode,
        host: str = "0.0.0.0",
        port: int = DEFAULT_LISTEN_PORT,
        max_connections: int = MAX_CONNECTIONS,
    ) -> None:
        """
        Initialize node server.

        Args:
            node: The AnemochoryNode that processes packets
            host: Listen address
            port: Listen port
            max_connections: Maximum concurrent connections
        """
        self._node = node
        self._host = host
        self._port = port
        self._max_connections = max_connections
        self._stats = ServerStats()
        self._connection_limiter = trio.CapacityLimiter(max_connections)

    @property
    def stats(self) -> ServerStats:
        """Server statistics."""
        return self._stats

    async def serve(self, *, task_status: trio.TaskStatus[None] = trio.TASK_STATUS_IGNORED) -> None:
        """
        Start serving and process packets until cancelled.

        Args:
            task_status: Trio task status for nursery.start()

        😐 This runs forever until the nursery is cancelled.
        """
        import time

        self._stats.started_at = time.time()
        logger.info("Node server starting on %s:%d", self._host, self._port)

        listeners = await trio.open_tcp_listeners(self._port, host=self._host)
        task_status.started()

        async with trio.open_nursery() as nursery:
            for listener in listeners:
                nursery.start_soon(self._accept_loop, listener)

    async def _accept_loop(self, listener: trio.SocketListener) -> None:
        """Accept connections in a loop."""
        async with listener:
            while True:
                try:
                    stream = await listener.accept()
                    self._stats.connections_accepted += 1
                    # Spawn handler with connection limiting
                    async with self._connection_limiter:
                        self._stats.connections_active += 1
                        try:
                            await self._handle_connection(stream)
                        finally:
                            self._stats.connections_active -= 1
                except trio.ClosedResourceError:
                    break
                except Exception:
                    logger.exception("Error accepting connection")
                    self._stats.errors += 1

    async def _handle_connection(self, stream: trio.SocketStream) -> None:
        """Handle a single client connection."""
        async with stream:
            try:
                while True:
                    try:
                        with trio.fail_after(READ_TIMEOUT):
                            session_id, packet_data = await read_framed_packet(stream)
                    except trio.TooSlowError:
                        logger.debug("Connection timed out")
                        break
                    except FramingError as e:
                        logger.warning("Framing error: %s", e)
                        self._stats.errors += 1
                        break

                    self._stats.packets_received += 1

                    # Process packet through node
                    result = self._node.process_packet(packet_data, session_id)

                    # Apply timing jitter
                    if result.jitter_ms > 0:
                        await trio.sleep(result.jitter_ms / 1000.0)

                    # Handle result
                    if result.action == PacketAction.FORWARD:
                        await self._forward_packet(result)
                    elif result.action == PacketAction.EXIT:
                        # Exit handling: for now, log and drop
                        # Full exit handler integration in Task 5
                        logger.info("Exit payload: %d bytes", len(result.payload))
                    # DROP: silently ignore

            except Exception:
                logger.exception("Connection handler error")
                self._stats.errors += 1

    async def _forward_packet(self, result: ProcessedPacket) -> None:
        """Forward a processed packet to the next hop."""
        if not result.next_address or not result.next_port:
            logger.error("Forward action with no destination")
            self._stats.errors += 1
            return

        try:
            stream = await trio.open_tcp_stream(
                result.next_address,
                result.next_port,
            )
            async with stream:
                frame = frame_packet(result.packet_data, result.session_id)
                await stream.send_all(frame)
                self._stats.packets_forwarded += 1
        except OSError as e:
            logger.warning(
                "Failed to forward to %s:%d: %s",
                result.next_address,
                result.next_port,
                e,
            )
            self._stats.errors += 1


# ============================================================================
# Packet Sender (Client-side)
# ============================================================================


class PacketSender:
    """
    😐 Sends packets to entry nodes via TCP.

    Simple async TCP client for injecting packets into the network.
    Handles connection pooling for repeated sends to the same entry.
    """

    def __init__(self) -> None:
        """Initialize sender."""
        self._sent_count = 0

    @property
    def sent_count(self) -> int:
        """Number of packets sent."""
        return self._sent_count

    async def send(
        self,
        packet: bytes,
        session_id: bytes,
        address: str,
        port: int,
    ) -> None:
        """
        Send a packet to a node.

        Args:
            packet: 1024-byte packet
            session_id: Session identifier
            address: Destination IP address
            port: Destination port

        Raises:
            TransportError: If send fails
        """
        try:
            stream = await trio.open_tcp_stream(address, port)
            async with stream:
                frame = frame_packet(packet, session_id)
                await stream.send_all(frame)
                self._sent_count += 1
        except OSError as e:
            raise TransportError(f"Failed to send to {address}:{port}: {e}") from e
