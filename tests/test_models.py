"""
😐 Tests for node identity & discovery models.

Tests NodeInfo validation, serialization, and NodePool operations.
🌑 Trust nothing, validate everything, break creatively.
"""

from __future__ import annotations

import json
import secrets
from pathlib import Path

import pytest

from anemochory.models import (
    DEFAULT_HOP_COUNT,
    MIN_POOL_SIZE,
    NODE_ID_SIZE,
    NodeCapability,
    NodeInfo,
    NodePool,
    NodePoolError,
)


# --- Fixtures ---


def _make_node(
    node_id: bytes | None = None,
    address: str = "10.0.0.1",
    port: int = 8000,
    public_key: bytes | None = None,
    capabilities: set[NodeCapability] | None = None,
    reputation: float = 0.5,
) -> NodeInfo:
    """Test node factory."""
    return NodeInfo(
        node_id=node_id or secrets.token_bytes(NODE_ID_SIZE),
        address=address,
        port=port,
        public_key=public_key or secrets.token_bytes(32),
        capabilities=capabilities or {NodeCapability.RELAY},
        reputation=reputation,
    )


# --- NodeInfo Tests ---


class TestNodeInfo:
    """😐 Testing node identity. The easy part."""

    def test_valid_node_creation(self) -> None:
        """Basic node creation with valid fields."""
        node = _make_node()
        assert len(node.node_id) == NODE_ID_SIZE
        assert len(node.public_key) == 32
        assert node.port == 8000
        assert node.can_relay

    def test_invalid_node_id_length(self) -> None:
        """🌑 Reject malformed node IDs."""
        with pytest.raises(ValueError, match="node_id must be"):
            _make_node(node_id=b"short")

    def test_invalid_public_key_length(self) -> None:
        """🌑 Reject malformed public keys."""
        with pytest.raises(ValueError, match="public_key must be"):
            _make_node(public_key=b"short")

    def test_invalid_port_zero(self) -> None:
        """🌑 Port 0 is not a valid listening port."""
        with pytest.raises(ValueError, match="port must be"):
            _make_node(port=0)

    def test_invalid_port_high(self) -> None:
        """🌑 Port 70000 is out of range."""
        with pytest.raises(ValueError, match="port must be"):
            _make_node(port=70000)

    def test_invalid_reputation_negative(self) -> None:
        """🌑 Negative reputation not allowed."""
        with pytest.raises(ValueError, match="reputation must be"):
            _make_node(reputation=-0.1)

    def test_invalid_reputation_over_one(self) -> None:
        """🌑 Reputation above 1.0 not allowed."""
        with pytest.raises(ValueError, match="reputation must be"):
            _make_node(reputation=1.5)

    def test_invalid_address(self) -> None:
        """🌑 Reject unparseable addresses."""
        with pytest.raises(ValueError, match="Invalid address"):
            _make_node(address="not-an-ip")

    def test_ipv6_address(self) -> None:
        """IPv6 addresses should work."""
        node = _make_node(address="::1")
        assert node.address == "::1"

    def test_subnet_prefix_ipv4(self) -> None:
        """/24 subnet prefix for IPv4."""
        node = _make_node(address="192.168.1.42")
        assert node.subnet_prefix == "192.168.1"

    def test_subnet_prefix_ipv6(self) -> None:
        """/48 subnet for IPv6."""
        node = _make_node(address="2001:db8:85a3::8a2e:370:7334")
        prefix = node.subnet_prefix
        assert prefix.startswith("2001:db8:85a3")

    def test_can_relay(self) -> None:
        """Check relay capability."""
        node = _make_node(capabilities={NodeCapability.RELAY})
        assert node.can_relay
        assert not node.can_exit

    def test_can_exit(self) -> None:
        """Check exit capability."""
        node = _make_node(capabilities={NodeCapability.EXIT, NodeCapability.RELAY})
        assert node.can_exit
        assert node.can_relay

    def test_serialization_roundtrip(self) -> None:
        """Serialize to dict and back."""
        node = _make_node(
            capabilities={NodeCapability.RELAY, NodeCapability.EXIT},
            reputation=0.75,
        )
        data = node.to_dict()
        restored = NodeInfo.from_dict(data)

        assert restored.node_id == node.node_id
        assert restored.address == node.address
        assert restored.port == node.port
        assert restored.public_key == node.public_key
        assert restored.capabilities == node.capabilities
        assert restored.reputation == node.reputation

    def test_json_serializable(self) -> None:
        """to_dict output must be JSON-serializable."""
        node = _make_node()
        data = json.dumps(node.to_dict())
        assert isinstance(data, str)

    def test_equality_by_node_id(self) -> None:
        """Two nodes with same node_id are equal."""
        node_id = secrets.token_bytes(NODE_ID_SIZE)
        node_a = _make_node(node_id=node_id)
        node_b = _make_node(node_id=node_id)
        assert node_a == node_b

    def test_inequality_different_id(self) -> None:
        """Different node_id = different node."""
        node_a = _make_node()
        node_b = _make_node()
        assert node_a != node_b

    def test_hash_by_node_id(self) -> None:
        """Hashable by node_id for set operations."""
        node_id = secrets.token_bytes(NODE_ID_SIZE)
        node_a = _make_node(node_id=node_id)
        node_b = _make_node(node_id=node_id)
        assert hash(node_a) == hash(node_b)
        assert len({node_a, node_b}) == 1

    def test_equality_not_implemented_for_non_node(self) -> None:
        """Comparing with non-NodeInfo returns NotImplemented."""
        node = _make_node()
        assert node != "not a node"

    def test_boundary_port_values(self) -> None:
        """Port 1 and 65535 are valid."""
        node_low = _make_node(port=1)
        node_high = _make_node(port=65535)
        assert node_low.port == 1
        assert node_high.port == 65535

    def test_reputation_boundaries(self) -> None:
        """Reputation 0.0 and 1.0 are valid."""
        node_zero = _make_node(reputation=0.0)
        node_one = _make_node(reputation=1.0)
        assert node_zero.reputation == 0.0
        assert node_one.reputation == 1.0


# --- NodePool Tests ---


class TestNodePool:
    """😐 Testing the node pool. Where routing decisions begin."""

    def test_empty_pool(self) -> None:
        """Empty pool has zero nodes and is not viable."""
        pool = NodePool()
        assert pool.size == 0
        assert not pool.is_viable
        assert len(pool) == 0

    def test_add_and_get(self) -> None:
        """Add a node and retrieve it."""
        pool = NodePool()
        node = _make_node()
        pool.add(node)
        assert pool.get(node.node_id) == node
        assert pool.size == 1

    def test_add_duplicate_same_key(self) -> None:
        """Re-adding same node (same pubkey) is an update."""
        pool = NodePool()
        node = _make_node()
        pool.add(node)
        pool.add(node)
        assert pool.size == 1

    def test_add_duplicate_different_key(self) -> None:
        """🌑 Node ID conflict with different pubkey is an attack."""
        pool = NodePool()
        node_id = secrets.token_bytes(NODE_ID_SIZE)
        node_a = _make_node(node_id=node_id, public_key=secrets.token_bytes(32))
        node_b = _make_node(node_id=node_id, public_key=secrets.token_bytes(32))
        pool.add(node_a)
        with pytest.raises(NodePoolError, match="conflict"):
            pool.add(node_b)

    def test_remove_existing(self) -> None:
        """Remove a known node."""
        pool = NodePool()
        node = _make_node()
        pool.add(node)
        pool.remove(node.node_id)
        assert pool.size == 0
        assert pool.get(node.node_id) is None

    def test_remove_unknown(self) -> None:
        """Removing unknown node is a no-op."""
        pool = NodePool()
        pool.remove(secrets.token_bytes(NODE_ID_SIZE))
        assert pool.size == 0

    def test_get_unknown(self) -> None:
        """Getting unknown node returns None."""
        pool = NodePool()
        assert pool.get(secrets.token_bytes(NODE_ID_SIZE)) is None

    def test_filter_by_capability(self) -> None:
        """Filter nodes by capability."""
        pool = NodePool()
        relay = _make_node(address="10.0.0.1", capabilities={NodeCapability.RELAY})
        exit_node = _make_node(
            address="10.0.1.1",
            capabilities={NodeCapability.RELAY, NodeCapability.EXIT},
        )
        pool.add(relay)
        pool.add(exit_node)

        exits = pool.filter(capability=NodeCapability.EXIT)
        assert len(exits) == 1
        assert exits[0] == exit_node

    def test_filter_by_reputation(self) -> None:
        """Filter nodes by minimum reputation."""
        pool = NodePool()
        low_rep = _make_node(address="10.0.0.1", reputation=0.2)
        high_rep = _make_node(address="10.0.1.1", reputation=0.8)
        pool.add(low_rep)
        pool.add(high_rep)

        good = pool.filter(min_reputation=0.5)
        assert len(good) == 1
        assert good[0] == high_rep

    def test_filter_exclude_ids(self) -> None:
        """Exclude specific node IDs from filter."""
        pool = NodePool()
        node_a = _make_node(address="10.0.0.1")
        node_b = _make_node(address="10.0.1.1")
        pool.add(node_a)
        pool.add(node_b)

        result = pool.filter(exclude_ids={node_a.node_id})
        assert len(result) == 1
        assert result[0] == node_b

    def test_filter_exclude_subnets(self) -> None:
        """
        🌑 Exclude nodes from same subnet (prevents Sybil attacks).
        """
        pool = NodePool()
        node_a = _make_node(address="10.0.1.1")
        node_b = _make_node(address="10.0.1.2")  # Same /24 as node_a
        node_c = _make_node(address="10.0.2.1")  # Different /24
        pool.add(node_a)
        pool.add(node_b)
        pool.add(node_c)

        result = pool.filter(exclude_subnets={"10.0.1"})
        assert len(result) == 1
        assert result[0] == node_c

    def test_filter_sorted_by_reputation(self) -> None:
        """Filter results sorted by reputation descending."""
        pool = NodePool()
        pool.add(_make_node(address="10.0.0.1", reputation=0.3))
        pool.add(_make_node(address="10.0.1.1", reputation=0.9))
        pool.add(_make_node(address="10.0.2.1", reputation=0.6))

        result = pool.filter()
        reputations = [n.reputation for n in result]
        assert reputations == sorted(reputations, reverse=True)

    def test_is_viable_threshold(self) -> None:
        """Pool is viable at MIN_POOL_SIZE nodes."""
        pool = NodePool()
        for i in range(MIN_POOL_SIZE - 1):
            pool.add(_make_node(address=f"10.0.{i}.1"))
        assert not pool.is_viable

        pool.add(_make_node(address=f"10.0.{MIN_POOL_SIZE}.1"))
        assert pool.is_viable

    def test_get_all(self) -> None:
        """Get all nodes."""
        pool = NodePool()
        nodes = [_make_node(address=f"10.0.{i}.1") for i in range(3)]
        for node in nodes:
            pool.add(node)
        assert len(pool.get_all()) == 3

    def test_save_and_load(self, tmp_path: Path) -> None:
        """Save pool to JSON and reload."""
        pool = NodePool.create_test_pool(5)
        path = tmp_path / "nodes.json"
        pool.save(path)

        loaded = NodePool.load(path)
        assert loaded.size == pool.size

        for node in pool.get_all():
            loaded_node = loaded.get(node.node_id)
            assert loaded_node is not None
            assert loaded_node.address == node.address
            assert loaded_node.public_key == node.public_key

    def test_save_creates_valid_json(self, tmp_path: Path) -> None:
        """Saved file is valid JSON."""
        pool = NodePool.create_test_pool(3)
        path = tmp_path / "nodes.json"
        pool.save(path)

        data = json.loads(path.read_text())
        assert "nodes" in data
        assert len(data["nodes"]) == 3

    def test_create_test_pool(self) -> None:
        """Test pool factory creates valid pool."""
        pool = NodePool.create_test_pool()
        assert pool.size == MIN_POOL_SIZE
        assert pool.is_viable

        # Should have at least one entry and one exit node
        entries = pool.filter(capability=NodeCapability.ENTRY)
        exits = pool.filter(capability=NodeCapability.EXIT)
        assert len(entries) >= 1
        assert len(exits) >= 1

    def test_create_test_pool_custom_size(self) -> None:
        """Test pool with custom size."""
        pool = NodePool.create_test_pool(20)
        assert pool.size == 20

    def test_repr(self) -> None:
        """Pool repr is informative."""
        pool = NodePool.create_test_pool(5)
        r = repr(pool)
        assert "size=5" in r
        assert "viable=" in r

    def test_filter_combined_criteria(self) -> None:
        """Filter with multiple criteria simultaneously."""
        pool = NodePool()
        # Good exit: high rep, exit cap, unique subnet
        good_exit = _make_node(
            address="10.0.0.1",
            capabilities={NodeCapability.RELAY, NodeCapability.EXIT},
            reputation=0.9,
        )
        # Bad rep exit: exit cap but low reputation
        bad_exit = _make_node(
            address="10.0.1.1",
            capabilities={NodeCapability.RELAY, NodeCapability.EXIT},
            reputation=0.1,
        )
        # Good relay: high rep but no exit
        good_relay = _make_node(
            address="10.0.2.1",
            capabilities={NodeCapability.RELAY},
            reputation=0.9,
        )
        pool.add(good_exit)
        pool.add(bad_exit)
        pool.add(good_relay)

        result = pool.filter(
            capability=NodeCapability.EXIT,
            min_reputation=0.5,
        )
        assert len(result) == 1
        assert result[0] == good_exit


class TestConstants:
    """Verify constants are sane."""

    def test_min_pool_size(self) -> None:
        """MIN_POOL_SIZE must be >= 3 * MIN_HOPS."""
        assert MIN_POOL_SIZE >= 9

    def test_default_hop_count(self) -> None:
        """DEFAULT_HOP_COUNT must be reasonable."""
        assert 3 <= DEFAULT_HOP_COUNT <= 7

    def test_node_id_size(self) -> None:
        """NODE_ID_SIZE is 16 bytes (128-bit)."""
        assert NODE_ID_SIZE == 16
