"""
😐 Transport server handler coverage tests.

Tests for NodeServer._handle_connection, _forward_packet, and
edge cases in the serve/accept paths.

🌑 These test the paths where packets hit the network layer
   and things inevitably go wrong.
"""

from __future__ import annotations

import secrets
from unittest.mock import patch

import pytest
import trio
import trio.testing

from anemochory.models import NodeCapability, NodeInfo
from anemochory.node import AnemochoryNode, PacketAction, ProcessedPacket
from anemochory.packet import PACKET_SIZE
from anemochory.transport import (
    FramingError,
    NodeServer,
    PacketSender,
    TransportError,
    frame_packet,
    read_framed_packet,
)


@pytest.fixture
def mock_node() -> AnemochoryNode:
    identity = NodeInfo(
        node_id=secrets.token_bytes(16),
        address="127.0.0.1",
        port=8000,
        public_key=secrets.token_bytes(32),
        capabilities={NodeCapability.RELAY},
    )
    return AnemochoryNode(identity=identity)


class TestNodeServerHandleConnection:
    """😐 Tests for the _handle_connection path — where coverage gaps live."""

    async def test_handle_connection_timeout(self, mock_node) -> None:
        """Connection that sends nothing should trigger TooSlowError path."""
        server = NodeServer(mock_node, host="127.0.0.1", port=0)

        send_stream, recv_stream = trio.testing.memory_stream_pair()

        # Patch READ_TIMEOUT to something tiny
        with patch("anemochory.transport.READ_TIMEOUT", 0.01):
            await server._handle_connection(recv_stream)

        # Server should not crash — just break out of loop
        assert server.stats.errors == 0

    async def test_handle_connection_framing_error(self, mock_node) -> None:
        """Malformed frame should increment error count and break."""
        server = NodeServer(mock_node, host="127.0.0.1", port=0)

        send_stream, recv_stream = trio.testing.memory_stream_pair()
        # Send a frame with length = 5 (too short, < 16 for session_id)
        import struct

        await send_stream.send_all(struct.pack(">I", 5) + b"12345")
        await send_stream.aclose()

        await server._handle_connection(recv_stream)

        assert server.stats.errors >= 1

    async def test_handle_connection_exit_action(self, mock_node) -> None:
        """Packet that results in EXIT action should be logged."""
        server = NodeServer(mock_node, host="127.0.0.1", port=0)

        # Register session key so node can process the packet
        session_id = secrets.token_bytes(16)
        key = secrets.token_bytes(32)
        mock_node.register_session_key(session_id, key)

        send_stream, recv_stream = trio.testing.memory_stream_pair()
        packet = secrets.token_bytes(PACKET_SIZE)
        frame = frame_packet(packet, session_id)
        await send_stream.send_all(frame)
        await send_stream.aclose()

        # The node will DROP since this is not a valid onion packet,
        # but this exercises the packet_received path
        await server._handle_connection(recv_stream)

        assert server.stats.packets_received >= 1

    async def test_handle_connection_handler_exception(self, mock_node) -> None:
        """Exception during processing should increment error count."""
        server = NodeServer(mock_node, host="127.0.0.1", port=0)

        send_stream, recv_stream = trio.testing.memory_stream_pair()
        session_id = secrets.token_bytes(16)
        packet = secrets.token_bytes(PACKET_SIZE)
        frame = frame_packet(packet, session_id)
        await send_stream.send_all(frame)
        await send_stream.aclose()

        # Patch process_packet to explode
        with patch.object(mock_node, "process_packet", side_effect=RuntimeError("boom")):
            await server._handle_connection(recv_stream)

        assert server.stats.errors >= 1


class TestNodeServerForwardPacket:
    """😐 Tests for _forward_packet — the forwarding path."""

    async def test_forward_no_destination(self, mock_node) -> None:
        """Forward with missing address/port should log error."""
        server = NodeServer(mock_node, host="127.0.0.1", port=0)

        result = ProcessedPacket(
            action=PacketAction.FORWARD,
            packet_data=secrets.token_bytes(PACKET_SIZE),
            session_id=secrets.token_bytes(16),
            payload=b"",
            next_address=None,
            next_port=None,
            jitter_ms=0,
        )

        await server._forward_packet(result)

        assert server.stats.errors >= 1
        assert server.stats.packets_forwarded == 0

    async def test_forward_unreachable_destination(self, mock_node) -> None:
        """Forward to unreachable host should log error, not crash."""
        server = NodeServer(mock_node, host="127.0.0.1", port=0)

        result = ProcessedPacket(
            action=PacketAction.FORWARD,
            packet_data=secrets.token_bytes(PACKET_SIZE),
            session_id=secrets.token_bytes(16),
            payload=b"",
            next_address="127.0.0.1",
            next_port=1,  # Port 1 is not listening
            jitter_ms=0,
        )

        await server._forward_packet(result)

        assert server.stats.errors >= 1
        assert server.stats.packets_forwarded == 0

    async def test_forward_success(self, mock_node) -> None:
        """Successful forward to a listening server."""
        server = NodeServer(mock_node, host="127.0.0.1", port=0)

        received = []

        async with trio.open_nursery() as nursery:
            listeners = await trio.open_tcp_listeners(0, host="127.0.0.1")
            port = listeners[0].socket.getsockname()[1]

            async def accept_conn(listener):
                async with listener:
                    try:
                        stream = await listener.accept()
                        async with stream:
                            sid, pkt = await read_framed_packet(stream)
                            received.append((sid, pkt))
                    except (trio.ClosedResourceError, FramingError):
                        pass

            for listener in listeners:
                nursery.start_soon(accept_conn, listener)

            await trio.sleep(0.05)

            session_id = secrets.token_bytes(16)
            packet_data = secrets.token_bytes(PACKET_SIZE)

            result = ProcessedPacket(
                action=PacketAction.FORWARD,
                packet_data=packet_data,
                session_id=session_id,
                payload=b"",
                next_address="127.0.0.1",
                next_port=port,
                jitter_ms=0,
            )

            await server._forward_packet(result)
            await trio.sleep(0.1)
            nursery.cancel_scope.cancel()

        assert server.stats.packets_forwarded == 1
        assert len(received) == 1
        assert received[0][0] == session_id
        assert received[0][1] == packet_data


class TestNodeServerIntegration:
    """😐 Full server integration — serve, accept, process."""

    async def test_server_processes_drop_packet(self, mock_node) -> None:
        """Server accepts connection and processes (DROP) a packet."""
        async with trio.open_nursery() as nursery:
            listeners = await trio.open_tcp_listeners(0, host="127.0.0.1")
            port = listeners[0].socket.getsockname()[1]
            for listener in listeners:
                listener.socket.close()

            server = NodeServer(mock_node, host="127.0.0.1", port=port)

            async def run_server():
                try:
                    await server.serve()
                except trio.Cancelled:
                    pass

            nursery.start_soon(run_server)
            await trio.sleep(0.15)

            # Send a packet
            try:
                stream = await trio.open_tcp_stream("127.0.0.1", port)
                async with stream:
                    session_id = secrets.token_bytes(16)
                    packet = secrets.token_bytes(PACKET_SIZE)
                    frame = frame_packet(packet, session_id)
                    await stream.send_all(frame)
                    await trio.sleep(0.1)
            except OSError:
                pass

            nursery.cancel_scope.cancel()

        assert server.stats.connections_accepted >= 1
        assert server.stats.packets_received >= 1

    async def test_server_multiple_connections(self, mock_node) -> None:
        """Server handles multiple concurrent connections."""
        async with trio.open_nursery() as nursery:
            listeners = await trio.open_tcp_listeners(0, host="127.0.0.1")
            port = listeners[0].socket.getsockname()[1]
            for listener in listeners:
                listener.socket.close()

            server = NodeServer(mock_node, host="127.0.0.1", port=port)

            async def run_server():
                try:
                    await server.serve()
                except trio.Cancelled:
                    pass

            nursery.start_soon(run_server)
            await trio.sleep(0.15)

            # Send from 3 connections
            for _ in range(3):
                try:
                    stream = await trio.open_tcp_stream("127.0.0.1", port)
                    async with stream:
                        sid = secrets.token_bytes(16)
                        pkt = secrets.token_bytes(PACKET_SIZE)
                        await stream.send_all(frame_packet(pkt, sid))
                        await trio.sleep(0.05)
                except OSError:
                    pass

            nursery.cancel_scope.cancel()

        assert server.stats.connections_accepted >= 2


class TestPacketSenderEdgeCases:
    """😐 More sender edge cases."""

    async def test_send_increments_count(self) -> None:
        """Each successful send increments sent_count."""
        async with trio.open_nursery() as nursery:
            listeners = await trio.open_tcp_listeners(0, host="127.0.0.1")
            port = listeners[0].socket.getsockname()[1]

            async def accept_and_discard(listener):
                async with listener:
                    try:
                        stream = await listener.accept()
                        async with stream:
                            await stream.receive_some(4096)
                    except trio.ClosedResourceError:
                        pass

            for listener in listeners:
                nursery.start_soon(accept_and_discard, listener)

            await trio.sleep(0.05)

            sender = PacketSender()
            await sender.send(
                secrets.token_bytes(PACKET_SIZE),
                secrets.token_bytes(16),
                "127.0.0.1",
                port,
            )
            assert sender.sent_count == 1

            nursery.cancel_scope.cancel()

    async def test_send_failure_preserves_count(self) -> None:
        """Failed send should not increment count."""
        sender = PacketSender()
        try:
            await sender.send(
                secrets.token_bytes(PACKET_SIZE),
                secrets.token_bytes(16),
                "127.0.0.1",
                1,  # Not listening
            )
        except TransportError:
            pass

        assert sender.sent_count == 0
