"""
😐 Tests for network transport layer.

Tests packet framing, TCP server, and sender.
Uses trio's testing utilities for async test support.

🌑 Network tests without actual TCP: mock the streams, test the logic.
"""

from __future__ import annotations

import secrets
import struct

import pytest
import trio
import trio.testing

from anemochory.packet import PACKET_SIZE
from anemochory.transport import (
    FramingError,
    PacketSender,
    TransportError,
    frame_packet,
    read_framed_packet,
)


# --- Framing Tests ---


class TestFramePacket:
    """😐 Testing packet framing. The boring but critical part."""

    def test_frame_valid_packet(self) -> None:
        """Frame a valid packet."""
        packet = secrets.token_bytes(PACKET_SIZE)
        session_id = secrets.token_bytes(16)
        frame = frame_packet(packet, session_id)

        # 4 bytes length + 16 bytes session_id + packet
        assert len(frame) == 4 + 16 + PACKET_SIZE

        # Check length prefix
        length = struct.unpack(">I", frame[:4])[0]
        assert length == 16 + PACKET_SIZE

        # Check session_id
        assert frame[4:20] == session_id

        # Check packet data
        assert frame[20:] == packet

    def test_frame_invalid_session_id(self) -> None:
        """Reject invalid session_id length."""
        with pytest.raises(ValueError, match="session_id must be 16"):
            frame_packet(b"data", b"short")

    def test_frame_empty_packet(self) -> None:
        """Frame an empty packet (edge case)."""
        session_id = secrets.token_bytes(16)
        frame = frame_packet(b"", session_id)
        assert len(frame) == 4 + 16


class TestReadFramedPacket:
    """😐 Testing frame reading from streams."""

    async def test_read_valid_frame(self) -> None:
        """Read a properly framed packet."""
        packet = secrets.token_bytes(PACKET_SIZE)
        session_id = secrets.token_bytes(16)
        frame = frame_packet(packet, session_id)

        send_stream, recv_stream = trio.testing.memory_stream_pair()
        await send_stream.send_all(frame)
        await send_stream.aclose()

        read_session_id, read_packet = await read_framed_packet(recv_stream)
        assert read_session_id == session_id
        assert read_packet == packet

    async def test_read_frame_connection_closed(self) -> None:
        """Connection closed before length read."""
        send_stream, recv_stream = trio.testing.memory_stream_pair()
        await send_stream.send_all(b"\x00\x01")  # Partial length
        await send_stream.aclose()

        with pytest.raises(FramingError, match="closed"):
            await read_framed_packet(recv_stream)

    async def test_read_frame_too_short(self) -> None:
        """Frame declares length < 16 bytes."""
        send_stream, recv_stream = trio.testing.memory_stream_pair()
        # Length = 10 (< 16 required for session_id)
        await send_stream.send_all(struct.pack(">I", 10))
        await send_stream.aclose()

        with pytest.raises(FramingError, match="too short"):
            await read_framed_packet(recv_stream)

    async def test_read_frame_too_large(self) -> None:
        """Frame declares length > max allowed."""
        send_stream, recv_stream = trio.testing.memory_stream_pair()
        # Length = way too big
        await send_stream.send_all(struct.pack(">I", PACKET_SIZE + 17 + 100))
        await send_stream.aclose()

        with pytest.raises(FramingError, match="too large"):
            await read_framed_packet(recv_stream)

    async def test_read_multiple_frames(self) -> None:
        """Read multiple frames from same stream."""
        session_id = secrets.token_bytes(16)
        packet1 = secrets.token_bytes(PACKET_SIZE)
        packet2 = secrets.token_bytes(PACKET_SIZE)

        frame1 = frame_packet(packet1, session_id)
        frame2 = frame_packet(packet2, session_id)

        send_stream, recv_stream = trio.testing.memory_stream_pair()
        await send_stream.send_all(frame1 + frame2)
        await send_stream.aclose()

        sid1, p1 = await read_framed_packet(recv_stream)
        sid2, p2 = await read_framed_packet(recv_stream)

        assert sid1 == session_id
        assert p1 == packet1
        assert sid2 == session_id
        assert p2 == packet2

    async def test_read_frame_partial_data(self) -> None:
        """Connection closed in middle of packet data."""
        send_stream, recv_stream = trio.testing.memory_stream_pair()
        # Valid length but incomplete data
        await send_stream.send_all(struct.pack(">I", 32))  # Says 32 bytes coming
        await send_stream.send_all(b"x" * 10)  # Only 10 bytes sent
        await send_stream.aclose()

        with pytest.raises(FramingError, match="closed"):
            await read_framed_packet(recv_stream)


class TestPacketSender:
    """😐 Testing the packet sender. Send and pray."""

    async def test_send_fails_no_server(self) -> None:
        """Send to nonexistent server raises TransportError."""
        sender = PacketSender()
        with pytest.raises(TransportError, match="Failed to send"):
            await sender.send(
                secrets.token_bytes(PACKET_SIZE),
                secrets.token_bytes(16),
                "127.0.0.1",
                19999,  # Nobody listening here
            )

    def test_initial_sent_count(self) -> None:
        """Sender starts with zero sent count."""
        sender = PacketSender()
        assert sender.sent_count == 0


class TestFramingRoundtrip:
    """End-to-end framing verification."""

    async def test_frame_and_read_roundtrip(self) -> None:
        """Frame → send → receive → unframe preserves data."""
        packet = secrets.token_bytes(PACKET_SIZE)
        session_id = secrets.token_bytes(16)

        send_stream, recv_stream = trio.testing.memory_stream_pair()
        frame = frame_packet(packet, session_id)
        await send_stream.send_all(frame)
        await send_stream.aclose()

        read_sid, read_pkt = await read_framed_packet(recv_stream)
        assert read_sid == session_id
        assert read_pkt == packet

    async def test_small_payload_roundtrip(self) -> None:
        """Small payloads frame correctly too."""
        packet = b"tiny"
        session_id = secrets.token_bytes(16)

        send_stream, recv_stream = trio.testing.memory_stream_pair()
        frame = frame_packet(packet, session_id)
        await send_stream.send_all(frame)
        await send_stream.aclose()

        read_sid, read_pkt = await read_framed_packet(recv_stream)
        assert read_sid == session_id
        assert read_pkt == packet
