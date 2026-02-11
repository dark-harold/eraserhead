"""
😐 Tests for routing path selection.

Tests PathSelector constraints: hop count, capabilities,
subnet diversity, reputation thresholds, and key generation.

🌑 If path selection is predictable, anonymity is dead.
"""

from __future__ import annotations

import secrets

import pytest

from anemochory.models import (
    NODE_ID_SIZE,
    NodeCapability,
    NodeInfo,
    NodePool,
)
from anemochory.routing import (
    InsufficientNodesError,
    PathConstraintError,
    PathSelector,
    RoutingError,
    RoutingPath,
    _pack_address,
)


# --- Helpers ---


def _make_node(
    address: str = "10.0.0.1",
    port: int = 8000,
    capabilities: set[NodeCapability] | None = None,
    reputation: float = 0.7,
) -> NodeInfo:
    """Create a test node."""
    return NodeInfo(
        node_id=secrets.token_bytes(NODE_ID_SIZE),
        address=address,
        port=port,
        public_key=secrets.token_bytes(32),
        capabilities=capabilities or {NodeCapability.RELAY},
        reputation=reputation,
    )


def _build_viable_pool(
    num_entries: int = 2,
    num_exits: int = 2,
    num_relays: int = 5,
) -> NodePool:
    """Build a pool with enough diverse nodes for 3-hop paths."""
    pool = NodePool()
    subnet = 0

    for i in range(num_entries):
        pool.add(
            _make_node(
                address=f"10.{subnet}.0.{i + 1}",
                capabilities={NodeCapability.ENTRY, NodeCapability.RELAY},
            )
        )
        subnet += 1

    for i in range(num_exits):
        pool.add(
            _make_node(
                address=f"10.{subnet}.0.{i + 1}",
                capabilities={NodeCapability.EXIT, NodeCapability.RELAY},
            )
        )
        subnet += 1

    for i in range(num_relays):
        pool.add(
            _make_node(
                address=f"10.{subnet}.0.{i + 1}",
                capabilities={NodeCapability.RELAY},
            )
        )
        subnet += 1

    return pool


# --- PathSelector Tests ---


class TestPathSelector:
    """😐 Testing the thing that decides whether your traffic is anonymous."""

    def test_invalid_hop_count_low(self) -> None:
        """Reject hop count below MIN_HOPS."""
        pool = NodePool()
        with pytest.raises(ValueError, match="hop_count must be"):
            PathSelector(pool, hop_count=2)

    def test_invalid_hop_count_high(self) -> None:
        """Reject hop count above MAX_HOPS."""
        pool = NodePool()
        with pytest.raises(ValueError, match="hop_count must be"):
            PathSelector(pool, hop_count=8)

    def test_valid_hop_counts(self) -> None:
        """Hop counts 3-7 are accepted."""
        pool = NodePool()
        for hc in range(3, 8):
            selector = PathSelector(pool, hop_count=hc)
            assert selector._hop_count == hc

    def test_select_path_basic_3_hops(self) -> None:
        """Select a valid 3-hop path."""
        pool = _build_viable_pool()
        selector = PathSelector(pool, hop_count=3)
        path = selector.select_path()

        assert path.hop_count == 3
        assert NodeCapability.ENTRY in path.entry_node.capabilities
        assert NodeCapability.EXIT in path.exit_node.capabilities

    def test_select_path_5_hops(self) -> None:
        """Select a 5-hop path (default)."""
        pool = _build_viable_pool(num_relays=10)
        selector = PathSelector(pool, hop_count=5)
        path = selector.select_path()

        assert path.hop_count == 5
        assert NodeCapability.ENTRY in path.entry_node.capabilities
        assert NodeCapability.EXIT in path.exit_node.capabilities

    def test_path_has_layer_keys(self) -> None:
        """Path includes per-hop layer keys."""
        pool = _build_viable_pool()
        selector = PathSelector(pool, hop_count=3)
        path = selector.select_path()

        assert len(path.layer_keys) == 3
        for key in path.layer_keys:
            assert len(key) == 32

    def test_layer_keys_unique(self) -> None:
        """Each hop gets a unique key."""
        pool = _build_viable_pool()
        selector = PathSelector(pool, hop_count=3)
        path = selector.select_path()

        assert len(set(path.layer_keys)) == 3

    def test_path_has_routing_info(self) -> None:
        """Path includes routing info for each hop."""
        pool = _build_viable_pool()
        selector = PathSelector(pool, hop_count=3)
        path = selector.select_path()

        assert len(path.routing_info) == 3

    def test_routing_info_points_to_next_hop(self) -> None:
        """Each routing info points to the next node."""
        pool = _build_viable_pool()
        selector = PathSelector(pool, hop_count=3)
        path = selector.select_path()

        # Entry (index 0) should point to middle (index 1)
        ri = path.routing_info[0]
        next_node = path.nodes[1]
        assert ri.next_hop_port == next_node.port

    def test_exit_routing_info_zeroed(self) -> None:
        """Exit node's routing info has zeroed next_hop."""
        pool = _build_viable_pool()
        selector = PathSelector(pool, hop_count=3)
        path = selector.select_path()

        exit_ri = path.routing_info[-1]
        assert exit_ri.next_hop_address == b"\x00" * 16
        assert exit_ri.next_hop_port == 0

    def test_subnet_diversity_enforced(self) -> None:
        """
        🌑 No two nodes from the same /24 subnet.
        """
        pool = _build_viable_pool()
        selector = PathSelector(pool, hop_count=3, enforce_subnet_diversity=True)
        path = selector.select_path()

        subnets = [n.subnet_prefix for n in path.nodes]
        assert len(subnets) == len(set(subnets)), "Duplicate subnets in path!"

    def test_no_entry_nodes_raises(self) -> None:
        """🌑 No entry nodes = routing failure."""
        pool = NodePool()
        for i in range(5):
            pool.add(
                _make_node(
                    address=f"10.{i}.0.1",
                    capabilities={NodeCapability.RELAY},
                )
            )
        pool.add(
            _make_node(
                address="10.10.0.1",
                capabilities={NodeCapability.EXIT, NodeCapability.RELAY},
            )
        )
        selector = PathSelector(pool, hop_count=3)
        with pytest.raises(InsufficientNodesError, match="entry"):
            selector.select_path()

    def test_no_exit_nodes_raises(self) -> None:
        """🌑 No exit nodes = routing failure."""
        pool = NodePool()
        pool.add(
            _make_node(
                address="10.0.0.1",
                capabilities={NodeCapability.ENTRY, NodeCapability.RELAY},
            )
        )
        for i in range(5):
            pool.add(
                _make_node(
                    address=f"10.{i + 1}.0.1",
                    capabilities={NodeCapability.RELAY},
                )
            )
        selector = PathSelector(pool, hop_count=3)
        with pytest.raises(InsufficientNodesError, match="exit"):
            selector.select_path()

    def test_insufficient_relays_raises(self) -> None:
        """Not enough relays for intermediate hops."""
        pool = NodePool()
        pool.add(
            _make_node(
                address="10.0.0.1",
                capabilities={NodeCapability.ENTRY, NodeCapability.RELAY},
            )
        )
        pool.add(
            _make_node(
                address="10.1.0.1",
                capabilities={NodeCapability.EXIT, NodeCapability.RELAY},
            )
        )
        # Need 1 relay for 3-hop but pool has no pure relays
        selector = PathSelector(pool, hop_count=3)
        with pytest.raises(PathConstraintError):
            selector.select_path()

    def test_exclude_node_ids(self) -> None:
        """Excluded node IDs are never in path."""
        pool = _build_viable_pool()
        all_nodes = pool.get_all()
        exclude = {all_nodes[0].node_id}

        selector = PathSelector(pool, hop_count=3)
        path = selector.select_path(exclude_node_ids=exclude)

        path_ids = {n.node_id for n in path.nodes}
        assert path_ids.isdisjoint(exclude)

    def test_reputation_filter(self) -> None:
        """Nodes below min_reputation excluded."""
        pool = NodePool()
        pool.add(
            _make_node(
                address="10.0.0.1",
                capabilities={NodeCapability.ENTRY, NodeCapability.RELAY},
                reputation=0.1,  # Below threshold
            )
        )
        pool.add(
            _make_node(
                address="10.1.0.1",
                capabilities={NodeCapability.EXIT, NodeCapability.RELAY},
                reputation=0.8,
            )
        )
        selector = PathSelector(pool, hop_count=3, min_reputation=0.5)
        with pytest.raises(InsufficientNodesError):
            selector.select_path()

    def test_disable_subnet_diversity(self) -> None:
        """Can disable subnet diversity constraint."""
        pool = NodePool()
        # All in same /24 — normally would fail diversity check
        pool.add(
            _make_node(
                address="10.0.0.1",
                capabilities={NodeCapability.ENTRY, NodeCapability.RELAY},
            )
        )
        pool.add(
            _make_node(
                address="10.0.0.2",
                capabilities={NodeCapability.EXIT, NodeCapability.RELAY},
            )
        )
        pool.add(
            _make_node(
                address="10.0.0.3",
                capabilities={NodeCapability.RELAY},
            )
        )
        selector = PathSelector(pool, hop_count=3, enforce_subnet_diversity=False)
        path = selector.select_path()
        assert path.hop_count == 3

    def test_build_packet_path_ordering(self) -> None:
        """build_packet_path returns innermost-first ordering."""
        pool = _build_viable_pool()
        selector = PathSelector(pool, hop_count=3)
        path = selector.select_path()

        packet_path = path.build_packet_path()
        assert len(packet_path) == 3

        # First element should be exit node's key (innermost)
        assert packet_path[0][0] == path.layer_keys[-1]
        # Last element should be entry node's key (outermost)
        assert packet_path[-1][0] == path.layer_keys[0]

    def test_multiple_paths_differ(self) -> None:
        """😐 Two path selections should (usually) differ."""
        pool = _build_viable_pool(num_relays=15)
        selector = PathSelector(pool, hop_count=3)

        paths = [selector.select_path() for _ in range(10)]
        node_sets = [frozenset(n.node_id for n in p.nodes) for p in paths]

        # At least 2 different paths in 10 attempts
        assert len(set(node_sets)) >= 2, "Path selection appears deterministic!"


class TestRoutingPath:
    """Tests for RoutingPath dataclass."""

    def test_hop_count(self) -> None:
        """hop_count reflects node list length."""
        nodes = [_make_node(address=f"10.{i}.0.1") for i in range(3)]
        path = RoutingPath(nodes=nodes)
        assert path.hop_count == 3

    def test_entry_exit_nodes(self) -> None:
        """entry_node and exit_node are first and last."""
        nodes = [_make_node(address=f"10.{i}.0.1") for i in range(4)]
        path = RoutingPath(nodes=nodes)
        assert path.entry_node is nodes[0]
        assert path.exit_node is nodes[-1]

    def test_build_packet_path_requires_keys(self) -> None:
        """build_packet_path raises if keys not generated."""
        nodes = [_make_node(address=f"10.{i}.0.1") for i in range(3)]
        path = RoutingPath(nodes=nodes)
        with pytest.raises(RoutingError, match="not yet generated"):
            path.build_packet_path()


class TestPackAddress:
    """Tests for IP address packing."""

    def test_ipv4_packing(self) -> None:
        """IPv4 packed to 16 bytes (4 + 12 zero padding)."""
        packed = _pack_address("10.0.0.1")
        assert len(packed) == 16
        assert packed[:4] == bytes([10, 0, 0, 1])
        assert packed[4:] == b"\x00" * 12

    def test_ipv6_packing(self) -> None:
        """IPv6 packed to native 16 bytes."""
        packed = _pack_address("::1")
        assert len(packed) == 16
        assert packed[-1] == 1

    def test_invalid_address(self) -> None:
        """Invalid address raises ValueError."""
        with pytest.raises(ValueError):
            _pack_address("not-an-ip")
