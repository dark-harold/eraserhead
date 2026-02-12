"""
😐 Tests for node packet processing.

Tests AnemochoryNode packet handling: decryption, forwarding,
exit handling, replay detection, and timing jitter.

🌑 Each test verifies that a node sees ONLY what it should see.
"""

from __future__ import annotations

import secrets

import pytest

from anemochory.crypto import ChaCha20Engine
from anemochory.models import NODE_ID_SIZE, NodeCapability, NodeInfo
from anemochory.node import (
    MAX_EXIT_PAYLOAD_SIZE,
    MAX_JITTER_MS,
    MIN_JITTER_MS,
    AnemochoryNode,
    ExitNodeHandler,
    PacketAction,
    _calculate_jitter,
    _unpack_address,
)
from anemochory.packet import (
    PACKET_SIZE,
    LayerRoutingInfo,
    build_onion_packet,
)
from anemochory.routing import _pack_address


# --- Helpers ---


def _make_node_identity(
    address: str = "10.0.0.1",
    port: int = 8000,
    capabilities: set[NodeCapability] | None = None,
) -> NodeInfo:
    """Create a test node identity."""
    return NodeInfo(
        node_id=secrets.token_bytes(NODE_ID_SIZE),
        address=address,
        port=port,
        public_key=secrets.token_bytes(32),
        capabilities=capabilities or {NodeCapability.RELAY},
    )


def _build_test_packet(
    hop_count: int = 3,
) -> tuple[bytes, list[bytes], bytes]:
    """
    Build a test onion packet with known keys.

    Returns:
        (packet, peel_order_keys, session_id)
        peel_order_keys[0] is outermost (first to decrypt = entry node)
        peel_order_keys[-1] is innermost (last to decrypt = exit node)

    🌑 Key ordering matters. Getting it wrong = silent decryption failure.
    """
    session_id = secrets.token_bytes(16)

    # Generate independent random keys for each hop
    # peel_keys[0] = outermost (entry), peel_keys[-1] = innermost (exit)
    peel_keys = [ChaCha20Engine.generate_key() for _ in range(hop_count)]

    # build_onion_packet expects path ordered innermost-first:
    # path[0] = (exit_key, exit_routing), path[-1] = (entry_key, entry_routing)
    path: list[tuple[bytes, LayerRoutingInfo]] = []

    for layer_idx in range(hop_count):
        # layer_idx 0 = innermost (exit), layer_idx N-1 = outermost (entry)
        # Map to peel order: innermost = peel_keys[-1], outermost = peel_keys[0]
        peel_idx = hop_count - 1 - layer_idx
        key = peel_keys[peel_idx]

        if layer_idx == 0:
            # Innermost (exit): no next hop
            next_addr = b"\x00" * 16
            next_port = 0
        else:
            # Points to the node that will process the INNER layer
            # Inner layer's node address
            inner_idx = layer_idx - 1
            next_addr = _pack_address(f"10.0.{inner_idx}.1")
            next_port = 8000 + inner_idx

        info = LayerRoutingInfo(
            next_hop_address=next_addr,
            next_hop_port=next_port,
            sequence_number=0,
            session_id=session_id,
            padding_length=0,
        )
        path.append((key, info))

    payload = b"Hello from the anonymous sender!"
    packet = build_onion_packet(payload, path, session_id)

    return packet, peel_keys, session_id


# --- AnemochoryNode Tests ---


class TestAnemochoryNode:
    """😐 Testing the node that peels onion layers."""

    def test_process_unknown_session(self) -> None:
        """Unknown session ID → DROP."""
        identity = _make_node_identity()
        node = AnemochoryNode(identity)

        packet = secrets.token_bytes(PACKET_SIZE)
        session_id = secrets.token_bytes(16)
        result = node.process_packet(packet, session_id)

        assert result.action == PacketAction.DROP
        assert "Unknown session" in (result.error or "")
        assert node.stats.packets_dropped == 1

    def test_process_invalid_size(self) -> None:
        """Wrong packet size → DROP."""
        identity = _make_node_identity()
        session_id = secrets.token_bytes(16)
        layer_key = ChaCha20Engine.generate_key()
        node = AnemochoryNode(identity, {session_id: layer_key})

        result = node.process_packet(b"short", session_id)
        assert result.action == PacketAction.DROP
        assert "Invalid packet size" in (result.error or "")

    def test_process_decrypt_failure(self) -> None:
        """Wrong key → decryption failure → DROP."""
        identity = _make_node_identity()
        session_id = secrets.token_bytes(16)
        wrong_key = ChaCha20Engine.generate_key()
        node = AnemochoryNode(identity, {session_id: wrong_key})

        packet, _, _ = _build_test_packet()
        result = node.process_packet(packet, session_id)

        assert result.action == PacketAction.DROP
        assert node.stats.decryption_failures == 1

    def test_process_forward_action(self) -> None:
        """Entry node correctly decrypts and forwards."""
        packet, layer_keys, session_id = _build_test_packet(hop_count=3)

        identity = _make_node_identity()
        # Entry node uses the outermost key (layer_keys[0])
        node = AnemochoryNode(identity, {session_id: layer_keys[0]})

        result = node.process_packet(packet, session_id)

        assert result.action == PacketAction.FORWARD
        assert result.next_address is not None
        assert result.next_port is not None
        assert result.next_port > 0
        assert len(result.packet_data) == PACKET_SIZE
        assert result.jitter_ms >= MIN_JITTER_MS
        assert node.stats.packets_forwarded == 1

    def test_process_exit_action(self) -> None:
        """
        Exit node decrypts to final payload.

        Build a 3-hop packet, peel 2 layers manually to get
        the packet that the exit node would receive.
        """
        packet, layer_keys, session_id = _build_test_packet(hop_count=3)

        # Simulate entry node processing (peel layer 0)
        entry = AnemochoryNode(
            _make_node_identity(),
            {session_id: layer_keys[0]},
        )
        r1 = entry.process_packet(packet, session_id)
        assert r1.action == PacketAction.FORWARD

        # Simulate relay node processing (peel layer 1)
        relay = AnemochoryNode(
            _make_node_identity(),
            {session_id: layer_keys[1]},
        )
        r2 = relay.process_packet(r1.packet_data, session_id)
        assert r2.action == PacketAction.FORWARD

        # Exit node processing (peel layer 2 = final)
        exit_node = AnemochoryNode(
            _make_node_identity(),
            {session_id: layer_keys[2]},
        )
        r3 = exit_node.process_packet(r2.packet_data, session_id)

        assert r3.action == PacketAction.EXIT
        assert r3.payload == b"Hello from the anonymous sender!"
        assert exit_node.stats.packets_exited == 1

    def test_replay_detection(self) -> None:
        """🌑 Same packet twice → replay detected."""
        packet, layer_keys, session_id = _build_test_packet(hop_count=3)

        identity = _make_node_identity()
        node = AnemochoryNode(identity, {session_id: layer_keys[0]})

        r1 = node.process_packet(packet, session_id)
        assert r1.action == PacketAction.FORWARD

        # Send same packet again → replay
        r2 = node.process_packet(packet, session_id)
        assert r2.action == PacketAction.DROP
        assert node.stats.replay_attempts >= 1

    def test_register_and_remove_session_key(self) -> None:
        """Register and remove session keys."""
        identity = _make_node_identity()
        node = AnemochoryNode(identity)
        session_id = secrets.token_bytes(16)
        key = ChaCha20Engine.generate_key()

        # Initially unknown
        result = node.process_packet(secrets.token_bytes(PACKET_SIZE), session_id)
        assert result.action == PacketAction.DROP

        # Register
        node.register_session_key(session_id, key)
        assert node._layer_keys[session_id] == key

        # Remove
        node.remove_session_key(session_id)
        result = node.process_packet(secrets.token_bytes(PACKET_SIZE), session_id)
        assert result.action == PacketAction.DROP

    def test_stats_tracking(self) -> None:
        """Stats correctly track packet processing."""
        packet, layer_keys, session_id = _build_test_packet(hop_count=3)
        identity = _make_node_identity()
        node = AnemochoryNode(identity, {session_id: layer_keys[0]})

        node.process_packet(packet, session_id)

        assert node.stats.packets_processed == 1
        assert node.stats.packets_forwarded == 1
        assert node.stats.packets_dropped == 0

    def test_timing_jitter_in_results(self) -> None:
        """Processed packets include timing jitter."""
        packet, layer_keys, session_id = _build_test_packet(hop_count=3)
        identity = _make_node_identity()
        node = AnemochoryNode(identity, {session_id: layer_keys[0]})

        result = node.process_packet(packet, session_id)
        assert result.jitter_ms >= MIN_JITTER_MS
        assert result.jitter_ms <= MAX_JITTER_MS

    def test_identity_property(self) -> None:
        """Node exposes its identity."""
        identity = _make_node_identity()
        node = AnemochoryNode(identity)
        assert node.identity is identity


# --- ExitNodeHandler Tests ---


class TestExitNodeHandler:
    """😐 Testing exit node payload handling."""

    def test_handle_valid_payload(self) -> None:
        """Valid payload returns success."""
        handler = ExitNodeHandler()
        response = handler.handle_payload(b"test data")

        assert response.success
        assert response.payload == b"test data"
        assert response.status_code == 200
        assert handler.stats["handled"] == 1

    def test_handle_empty_payload(self) -> None:
        """Empty payload returns failure."""
        handler = ExitNodeHandler()
        response = handler.handle_payload(b"")

        assert not response.success
        assert "Empty payload" in (response.error or "")
        assert handler.stats["failed"] == 1

    def test_handle_oversized_payload(self) -> None:
        """Oversized payload returns failure."""
        handler = ExitNodeHandler()
        big_payload = secrets.token_bytes(MAX_EXIT_PAYLOAD_SIZE + 1)
        response = handler.handle_payload(big_payload)

        assert not response.success
        assert "too large" in (response.error or "")
        assert handler.stats["failed"] == 1

    def test_handle_max_size_payload(self) -> None:
        """Exactly max size payload succeeds."""
        handler = ExitNodeHandler()
        payload = secrets.token_bytes(MAX_EXIT_PAYLOAD_SIZE)
        response = handler.handle_payload(payload)

        assert response.success


# --- Utility Tests ---


class TestCalculateJitter:
    """Tests for timing jitter calculation."""

    def test_jitter_in_range(self) -> None:
        """Jitter is within configured bounds."""
        for _ in range(100):
            jitter = _calculate_jitter()
            assert MIN_JITTER_MS <= jitter <= MAX_JITTER_MS

    def test_jitter_varies(self) -> None:
        """😐 Jitter is not constant (would defeat the purpose)."""
        jitters = {_calculate_jitter() for _ in range(100)}
        assert len(jitters) > 1


class TestUnpackAddress:
    """Tests for address unpacking."""

    def test_ipv4_roundtrip(self) -> None:
        """Pack and unpack IPv4."""
        packed = _pack_address("192.168.1.42")
        unpacked = _unpack_address(packed)
        assert unpacked == "192.168.1.42"

    def test_ipv6_roundtrip(self) -> None:
        """Pack and unpack IPv6."""
        packed = _pack_address("::1")
        unpacked = _unpack_address(packed)
        assert unpacked == "::1"

    def test_invalid_length(self) -> None:
        """Wrong byte length raises ValueError."""
        with pytest.raises(ValueError, match="16 bytes"):
            _unpack_address(b"short")
