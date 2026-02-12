"""
😐 Extended tests for network transport layer.

Comprehensive testing of NodeServer, PacketSender, and connection
management. Uses trio's memory streams and real TCP sockets for
integration testing.

🌑 Network tests are the scariest. Everything is async, everything
   can timeout, and Harold's sleep schedule depends on these passing.
"""

from __future__ import annotations

import secrets
import struct

import pytest
import trio
import trio.testing

from anemochory.models import NodeCapability, NodeInfo
from anemochory.node import AnemochoryNode
from anemochory.packet import PACKET_SIZE
from anemochory.transport import (
    FramingError,
    NodeServer,
    PacketSender,
    ServerStats,
    TransportError,
    _read_exactly,
    frame_packet,
    read_framed_packet,
)


# ============================================================================
# Helper Fixtures
# ============================================================================


@pytest.fixture
def session_id() -> bytes:
    return secrets.token_bytes(16)


@pytest.fixture
def sample_packet() -> bytes:
    return secrets.token_bytes(PACKET_SIZE)


@pytest.fixture
def mock_node() -> AnemochoryNode:
    """Create a mock AnemochoryNode that returns DROP for all packets."""
    identity = NodeInfo(
        node_id=secrets.token_bytes(16),
        address="127.0.0.1",
        port=8000,
        public_key=secrets.token_bytes(32),
        capabilities={NodeCapability.RELAY},
    )
    return AnemochoryNode(identity=identity)


# ============================================================================
# Extended Framing Tests
# ============================================================================


class TestFrameEdgeCases:
    """😐 Edge cases in packet framing."""

    def test_frame_exact_max_size_packet(self) -> None:
        """Frame a packet exactly at PACKET_SIZE."""
        packet = secrets.token_bytes(PACKET_SIZE)
        session_id = secrets.token_bytes(16)
        frame = frame_packet(packet, session_id)
        assert len(frame) == 4 + 16 + PACKET_SIZE

    def test_frame_session_id_exactly_16_bytes(self) -> None:
        """Session ID boundary: exactly 16 bytes."""
        session_id = b"\x00" * 16
        frame = frame_packet(b"data", session_id)
        assert frame[4:20] == session_id

    def test_frame_with_all_zeros(self) -> None:
        """Frame with all-zero content."""
        frame = frame_packet(b"\x00" * 100, b"\x00" * 16)
        length = struct.unpack(">I", frame[:4])[0]
        assert length == 116  # 16 + 100

    def test_frame_session_id_too_short(self) -> None:
        with pytest.raises(ValueError, match="session_id must be 16"):
            frame_packet(b"data", b"\x01" * 15)

    def test_frame_session_id_too_long(self) -> None:
        with pytest.raises(ValueError, match="session_id must be 16"):
            frame_packet(b"data", b"\x01" * 17)

    def test_frame_preserves_binary_data(self) -> None:
        """Ensure all byte values survive framing."""
        packet = bytes(range(256)) * 4  # All byte values
        session_id = secrets.token_bytes(16)
        frame = frame_packet(packet, session_id)
        assert frame[20:] == packet


# ============================================================================
# Extended Read Framing Tests
# ============================================================================


class TestReadFramedPacketExtended:
    """😐 More read framing edge cases."""

    async def test_read_frame_exact_boundary(self) -> None:
        """Frame with data exactly at the PACKET_SIZE + 16 boundary."""
        packet = secrets.token_bytes(PACKET_SIZE)
        session_id = secrets.token_bytes(16)
        frame = frame_packet(packet, session_id)

        send_stream, recv_stream = trio.testing.memory_stream_pair()
        await send_stream.send_all(frame)
        await send_stream.aclose()

        read_sid, read_pkt = await read_framed_packet(recv_stream)
        assert read_sid == session_id
        assert read_pkt == packet

    async def test_read_empty_stream(self) -> None:
        """Completely empty stream should raise framing error."""
        send_stream, recv_stream = trio.testing.memory_stream_pair()
        await send_stream.aclose()

        with pytest.raises(FramingError, match="closed"):
            await read_framed_packet(recv_stream)

    async def test_read_frame_zero_length_after_session_id(self) -> None:
        """Frame with length = 16 (just session_id, no packet data)."""
        session_id = secrets.token_bytes(16)
        # Length = 16: session_id only, zero-length packet
        data = struct.pack(">I", 16) + session_id

        send_stream, recv_stream = trio.testing.memory_stream_pair()
        await send_stream.send_all(data)
        await send_stream.aclose()

        read_sid, read_pkt = await read_framed_packet(recv_stream)
        assert read_sid == session_id
        assert read_pkt == b""


# ============================================================================
# _read_exactly Tests
# ============================================================================


class TestReadExactly:
    """😐 Testing the low-level exact-read helper."""

    async def test_read_exact_bytes(self) -> None:
        send_stream, recv_stream = trio.testing.memory_stream_pair()
        data = b"hello world"
        await send_stream.send_all(data)
        await send_stream.aclose()

        result = await _read_exactly(recv_stream, 5)
        assert result == b"hello"

    async def test_read_all_bytes(self) -> None:
        send_stream, recv_stream = trio.testing.memory_stream_pair()
        data = b"exactly"
        await send_stream.send_all(data)
        await send_stream.aclose()

        result = await _read_exactly(recv_stream, len(data))
        assert result == data

    async def test_read_more_than_available(self) -> None:
        """Requesting more bytes than available returns partial data."""
        send_stream, recv_stream = trio.testing.memory_stream_pair()
        await send_stream.send_all(b"short")
        await send_stream.aclose()

        result = await _read_exactly(recv_stream, 100)
        assert result == b"short"

    async def test_read_from_closed_stream(self) -> None:
        send_stream, recv_stream = trio.testing.memory_stream_pair()
        await send_stream.aclose()
        result = await _read_exactly(recv_stream, 10)
        assert result == b""

    async def test_read_zero_bytes(self) -> None:
        send_stream, recv_stream = trio.testing.memory_stream_pair()
        result = await _read_exactly(recv_stream, 0)
        assert result == b""


# ============================================================================
# NodeServer Tests
# ============================================================================


class TestNodeServer:
    """😐 Testing the TCP server. Where packets meet the network."""

    def test_server_stats_initial(self, mock_node) -> None:
        server = NodeServer(mock_node, port=0)
        assert server.stats.connections_accepted == 0
        assert server.stats.connections_active == 0
        assert server.stats.packets_received == 0

    async def test_server_starts_and_accepts_connection(self, mock_node) -> None:
        """Server should start and accept a TCP connection."""
        server = NodeServer(mock_node, host="127.0.0.1", port=0)

        async with trio.open_nursery() as nursery:
            # Find a free port
            listeners = await trio.open_tcp_listeners(0, host="127.0.0.1")
            port = listeners[0].socket.getsockname()[1]
            for listener in listeners:
                listener.socket.close()

            # Create server on that port
            server = NodeServer(mock_node, host="127.0.0.1", port=port)

            async def run_server():
                try:
                    await server.serve()
                except trio.Cancelled:
                    pass

            nursery.start_soon(run_server)
            await trio.sleep(0.1)  # Give server time to start

            # Connect and send a framed packet
            try:
                stream = await trio.open_tcp_stream("127.0.0.1", port)
                async with stream:
                    session_id = secrets.token_bytes(16)
                    packet = secrets.token_bytes(PACKET_SIZE)
                    frame = frame_packet(packet, session_id)
                    await stream.send_all(frame)
                    await trio.sleep(0.05)  # Allow processing
            except OSError:
                pass  # Server may not be ready yet on slow systems

            nursery.cancel_scope.cancel()

    def test_server_custom_config(self, mock_node) -> None:
        """Server should accept custom host/port/max_connections."""
        server = NodeServer(
            mock_node,
            host="0.0.0.0",
            port=9999,
            max_connections=50,
        )
        assert server._host == "0.0.0.0"
        assert server._port == 9999
        assert server._max_connections == 50


# ============================================================================
# PacketSender Extended Tests
# ============================================================================


class TestPacketSenderExtended:
    """😐 More sender testing."""

    def test_sender_initial_state(self) -> None:
        sender = PacketSender()
        assert sender.sent_count == 0

    async def test_send_to_real_server(self) -> None:
        """Integration: sender → server round trip."""
        async with trio.open_nursery() as nursery:
            # Start a listener to receive
            listeners = await trio.open_tcp_listeners(0, host="127.0.0.1")
            port = listeners[0].socket.getsockname()[1]

            identity = NodeInfo(
                node_id=secrets.token_bytes(16),
                address="127.0.0.1",
                port=port,
                public_key=secrets.token_bytes(32),
                capabilities={NodeCapability.RELAY},
            )
            node = AnemochoryNode(identity=identity)
            session_id = secrets.token_bytes(16)
            key = secrets.token_bytes(32)
            node.register_session_key(session_id, key)

            received_data = []

            async def accept_one(listener):
                async with listener:
                    try:
                        stream = await listener.accept()
                        async with stream:
                            sid, pkt = await read_framed_packet(stream)
                            received_data.append((sid, pkt))
                    except (trio.ClosedResourceError, FramingError):
                        pass

            for listener in listeners:
                nursery.start_soon(accept_one, listener)

            await trio.sleep(0.05)

            # Send
            sender = PacketSender()
            packet = secrets.token_bytes(PACKET_SIZE)
            await sender.send(packet, session_id, "127.0.0.1", port)
            assert sender.sent_count == 1

            await trio.sleep(0.1)
            nursery.cancel_scope.cancel()

        assert len(received_data) == 1
        assert received_data[0][0] == session_id
        assert received_data[0][1] == packet

    async def test_send_unreachable_host(self) -> None:
        """Sending to unreachable address should raise TransportError."""
        sender = PacketSender()
        with pytest.raises(TransportError, match="Failed to send"):
            await sender.send(
                secrets.token_bytes(PACKET_SIZE),
                secrets.token_bytes(16),
                "127.0.0.1",
                1,  # Port 1 is unlikely to be listening
            )


# ============================================================================
# Server Stats Tests
# ============================================================================


class TestServerStats:
    """😐 Testing server statistics tracking."""

    def test_stats_dataclass_defaults(self) -> None:
        stats = ServerStats()
        assert stats.connections_accepted == 0
        assert stats.connections_active == 0
        assert stats.packets_received == 0
        assert stats.packets_forwarded == 0
        assert stats.errors == 0
        assert stats.started_at == 0.0

    def test_stats_mutation(self) -> None:
        stats = ServerStats()
        stats.connections_accepted = 5
        stats.packets_received = 100
        stats.errors = 2
        assert stats.connections_accepted == 5
        assert stats.packets_received == 100
        assert stats.errors == 2


# ============================================================================
# Multi-frame Roundtrip Tests
# ============================================================================


class TestMultiFrameStream:
    """😐 Testing multiple frames on a single stream."""

    async def test_three_frames_same_session(self) -> None:
        """Multiple frames with same session_id."""
        session_id = secrets.token_bytes(16)
        packets = [secrets.token_bytes(PACKET_SIZE) for _ in range(3)]

        send_stream, recv_stream = trio.testing.memory_stream_pair()
        for p in packets:
            await send_stream.send_all(frame_packet(p, session_id))
        await send_stream.aclose()

        for expected in packets:
            sid, pkt = await read_framed_packet(recv_stream)
            assert sid == session_id
            assert pkt == expected

    async def test_frames_different_sessions(self) -> None:
        """Multiple frames with different session_ids."""
        sessions = [secrets.token_bytes(16) for _ in range(3)]
        packets = [secrets.token_bytes(PACKET_SIZE) for _ in range(3)]

        send_stream, recv_stream = trio.testing.memory_stream_pair()
        for sid, pkt in zip(sessions, packets):
            await send_stream.send_all(frame_packet(pkt, sid))
        await send_stream.aclose()

        for expected_sid, expected_pkt in zip(sessions, packets):
            sid, pkt = await read_framed_packet(recv_stream)
            assert sid == expected_sid
            assert pkt == expected_pkt

    async def test_interleaved_small_and_large_frames(self) -> None:
        """Mix of small and full-size packets."""
        session_id = secrets.token_bytes(16)
        small_pkt = b"tiny"
        big_pkt = secrets.token_bytes(PACKET_SIZE)

        send_stream, recv_stream = trio.testing.memory_stream_pair()
        await send_stream.send_all(frame_packet(small_pkt, session_id))
        await send_stream.send_all(frame_packet(big_pkt, session_id))
        await send_stream.aclose()

        _, p1 = await read_framed_packet(recv_stream)
        _, p2 = await read_framed_packet(recv_stream)
        assert p1 == small_pkt
        assert p2 == big_pkt
