"""
😐 Anemochory Protocol: End-to-End Integration Tests

Tests the full pipeline: client → path selection → packet build →
multi-hop node processing → exit payload extraction.

🌑 This is where we prove the whole thing works together.
   Individual unit tests are necessary but insufficient.
   Integration tests are where reality hits.
"""

from __future__ import annotations

import secrets

from anemochory.crypto import ChaCha20Engine
from anemochory.models import NODE_ID_SIZE, NodeCapability, NodeInfo, NodePool
from anemochory.node import AnemochoryNode, ExitNodeHandler, PacketAction
from anemochory.packet import (
    PACKET_SIZE,
    build_onion_packet,
    calculate_max_payload_size,
    generate_session_id,
)
from anemochory.routing import PathSelector


# --- Helpers ---


def _make_node_info(
    address: str,
    port: int,
    capabilities: set[NodeCapability],
) -> NodeInfo:
    return NodeInfo(
        node_id=secrets.token_bytes(NODE_ID_SIZE),
        address=address,
        port=port,
        public_key=secrets.token_bytes(32),
        capabilities=capabilities,
        reputation=0.8,
    )


def _build_diverse_pool(
    num_entries: int = 2,
    num_relays: int = 6,
    num_exits: int = 2,
) -> NodePool:
    """Build a pool with unique /24 subnets per node."""
    pool = NodePool()
    subnet = 0

    for i in range(num_entries):
        pool.add(
            _make_node_info(
                f"10.{subnet}.0.1",
                8000 + subnet,
                {NodeCapability.ENTRY, NodeCapability.RELAY},
            )
        )
        subnet += 1

    for i in range(num_relays):
        pool.add(
            _make_node_info(
                f"10.{subnet}.0.1",
                8000 + subnet,
                {NodeCapability.RELAY},
            )
        )
        subnet += 1

    for i in range(num_exits):
        pool.add(
            _make_node_info(
                f"10.{subnet}.0.1",
                8000 + subnet,
                {NodeCapability.EXIT, NodeCapability.RELAY},
            )
        )
        subnet += 1

    return pool


# --- End-to-End Tests ---


class TestEndToEnd:
    """
    😐 Full pipeline integration tests.

    Client builds packet → each node peels one layer → exit node gets payload.
    """

    def test_3_hop_full_pipeline(self) -> None:
        """
        📺 The Classic 3-Hop Journey:
        Build a 3-hop onion packet, simulate each node processing,
        and verify the exit node recovers the original payload.
        """
        pool = _build_diverse_pool()
        selector = PathSelector(pool, hop_count=3)
        path = selector.select_path()

        payload = b"This message should survive 3 hops of encryption"
        session_id = generate_session_id()

        # Build onion packet
        packet_path = path.build_packet_path()
        packet = build_onion_packet(payload, packet_path, session_id)
        assert len(packet) == PACKET_SIZE

        # Simulate each node processing
        # Entry node (index 0, outermost layer key)
        entry = AnemochoryNode(
            path.nodes[0],
            {session_id: path.layer_keys[0]},
        )
        r1 = entry.process_packet(packet, session_id)
        assert r1.action == PacketAction.FORWARD
        assert len(r1.packet_data) == PACKET_SIZE

        # Relay node (index 1, middle layer key)
        relay = AnemochoryNode(
            path.nodes[1],
            {session_id: path.layer_keys[1]},
        )
        r2 = relay.process_packet(r1.packet_data, session_id)
        assert r2.action == PacketAction.FORWARD
        assert len(r2.packet_data) == PACKET_SIZE

        # Exit node (index 2, innermost layer key)
        exit_node = AnemochoryNode(
            path.nodes[2],
            {session_id: path.layer_keys[2]},
        )
        r3 = exit_node.process_packet(r2.packet_data, session_id)
        assert r3.action == PacketAction.EXIT
        assert r3.payload == payload

    def test_5_hop_full_pipeline(self) -> None:
        """5-hop path: entry → 3 relays → exit."""
        pool = _build_diverse_pool(num_relays=10)
        selector = PathSelector(pool, hop_count=5)
        path = selector.select_path()

        payload = b"Five hops of anonymity"
        session_id = generate_session_id()

        packet_path = path.build_packet_path()
        packet = build_onion_packet(payload, packet_path, session_id)

        # Process through all 5 nodes
        current_packet = packet
        for i in range(5):
            node = AnemochoryNode(
                path.nodes[i],
                {session_id: path.layer_keys[i]},
            )
            result = node.process_packet(current_packet, session_id)

            if i < 4:
                assert result.action == PacketAction.FORWARD
                current_packet = result.packet_data
            else:
                assert result.action == PacketAction.EXIT
                assert result.payload == payload

    def test_7_hop_max_path(self) -> None:
        """Maximum 7-hop path with smallest payload."""
        pool = _build_diverse_pool(num_relays=12)
        selector = PathSelector(pool, hop_count=7)
        path = selector.select_path()

        max_size = calculate_max_payload_size(7)
        payload = secrets.token_bytes(max_size)
        session_id = generate_session_id()

        packet_path = path.build_packet_path()
        packet = build_onion_packet(payload, packet_path, session_id)

        current_packet = packet
        for i in range(7):
            node = AnemochoryNode(
                path.nodes[i],
                {session_id: path.layer_keys[i]},
            )
            result = node.process_packet(current_packet, session_id)

            if i < 6:
                assert result.action == PacketAction.FORWARD
                current_packet = result.packet_data
            else:
                assert result.action == PacketAction.EXIT
                assert result.payload == payload

    def test_wrong_key_at_any_hop_fails(self) -> None:
        """🌑 Using wrong key at ANY hop drops the packet."""
        pool = _build_diverse_pool()
        selector = PathSelector(pool, hop_count=3)
        path = selector.select_path()

        payload = b"should never arrive"
        session_id = generate_session_id()
        packet = build_onion_packet(payload, path.build_packet_path(), session_id)

        # Entry node with WRONG key
        wrong_key = ChaCha20Engine.generate_key()
        entry = AnemochoryNode(
            path.nodes[0],
            {session_id: wrong_key},
        )
        result = entry.process_packet(packet, session_id)
        assert result.action == PacketAction.DROP

    def test_constant_packet_size_through_all_hops(self) -> None:
        """
        🌑 Every packet at every hop is exactly PACKET_SIZE bytes.
        Size variation = traffic analysis = deanonymization.
        """
        pool = _build_diverse_pool()
        selector = PathSelector(pool, hop_count=3)
        path = selector.select_path()

        payload = b"constant size!"
        session_id = generate_session_id()
        packet = build_onion_packet(payload, path.build_packet_path(), session_id)
        assert len(packet) == PACKET_SIZE

        current = packet
        for i in range(3):
            node = AnemochoryNode(
                path.nodes[i],
                {session_id: path.layer_keys[i]},
            )
            result = node.process_packet(current, session_id)
            if result.action == PacketAction.FORWARD:
                assert len(result.packet_data) == PACKET_SIZE
                current = result.packet_data

    def test_exit_handler_integration(self) -> None:
        """Exit node → ExitNodeHandler processes payload."""
        pool = _build_diverse_pool()
        selector = PathSelector(pool, hop_count=3)
        path = selector.select_path()

        payload = b"exit me safely"
        session_id = generate_session_id()
        packet = build_onion_packet(payload, path.build_packet_path(), session_id)

        # Process through entry and relay
        current = packet
        for i in range(2):
            node = AnemochoryNode(
                path.nodes[i],
                {session_id: path.layer_keys[i]},
            )
            result = node.process_packet(current, session_id)
            assert result.action == PacketAction.FORWARD
            current = result.packet_data

        # Exit node
        exit_anode = AnemochoryNode(
            path.nodes[2],
            {session_id: path.layer_keys[2]},
        )
        exit_result = exit_anode.process_packet(current, session_id)
        assert exit_result.action == PacketAction.EXIT

        # Feed to ExitNodeHandler
        handler = ExitNodeHandler()
        response = handler.handle_payload(exit_result.payload)
        assert response.success
        assert response.payload == payload

    def test_different_payloads_same_packet_size(self) -> None:
        """
        😐 Different payload sizes produce identical packet sizes.
        This is the traffic analysis resistance property.
        """
        pool = _build_diverse_pool()
        selector = PathSelector(pool, hop_count=3)
        session_id = generate_session_id()

        sizes = []
        for msg in [b"a", b"hello world", b"x" * 100]:
            path = selector.select_path()
            packet = build_onion_packet(msg, path.build_packet_path(), session_id)
            sizes.append(len(packet))

        assert all(s == PACKET_SIZE for s in sizes)

    def test_replay_across_nodes(self) -> None:
        """
        🌑 Same packet sent to same node twice = replay detected.
        """
        pool = _build_diverse_pool()
        selector = PathSelector(pool, hop_count=3)
        path = selector.select_path()

        payload = b"replay me"
        session_id = generate_session_id()
        packet = build_onion_packet(payload, path.build_packet_path(), session_id)

        entry = AnemochoryNode(
            path.nodes[0],
            {session_id: path.layer_keys[0]},
        )

        r1 = entry.process_packet(packet, session_id)
        assert r1.action == PacketAction.FORWARD

        # Replay!
        r2 = entry.process_packet(packet, session_id)
        assert r2.action == PacketAction.DROP

    def test_subnet_diversity_in_path(self) -> None:
        """
        🌑 All nodes in every selected path have unique /24 subnets.
        """
        pool = _build_diverse_pool(num_relays=15)
        selector = PathSelector(pool, hop_count=5)

        for _ in range(10):
            path = selector.select_path()
            subnets = [n.subnet_prefix for n in path.nodes]
            assert len(subnets) == len(set(subnets)), "Duplicate subnets in path!"

    def test_timing_jitter_present(self) -> None:
        """Each processed packet has non-zero jitter."""
        pool = _build_diverse_pool()
        selector = PathSelector(pool, hop_count=3)
        path = selector.select_path()

        payload = b"jittery"
        session_id = generate_session_id()
        packet = build_onion_packet(payload, path.build_packet_path(), session_id)

        entry = AnemochoryNode(
            path.nodes[0],
            {session_id: path.layer_keys[0]},
        )
        result = entry.process_packet(packet, session_id)
        assert result.jitter_ms > 0
