"""
😐 Anemochory Protocol: Path Selection & Routing

Selects anonymized routing paths through the node network.
Enforces subnet diversity, capability requirements, and
reputation thresholds to resist Sybil and correlation attacks.

🌑 Dark Harold: Path selection IS the anonymity layer. If the adversary
   can predict or influence path selection, anonymity is gone.
   Randomness + diversity constraints + reputation are our shields.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field

from anemochory.crypto import ChaCha20Engine, derive_layer_key
from anemochory.models import (
    DEFAULT_HOP_COUNT,
    NodeCapability,
    NodeInfo,
    NodePool,
)
from anemochory.packet import MAX_HOPS, MIN_HOPS, LayerRoutingInfo


# ============================================================================
# Constants
# ============================================================================

MIN_REPUTATION = 0.3  # Minimum reputation for path inclusion
DEFAULT_DIVERSITY_SUBNETS = True  # Enforce /24 diversity by default


# ============================================================================
# Exceptions
# ============================================================================


class RoutingError(Exception):
    """Base routing error."""


class InsufficientNodesError(RoutingError):
    """Not enough nodes to build a path."""


class PathConstraintError(RoutingError):
    """Path constraints cannot be satisfied."""


# ============================================================================
# Path Selection
# ============================================================================


@dataclass
class RoutingPath:
    """
    A selected routing path through the Anemochory network.

    Contains the ordered list of nodes from entry to exit,
    along with per-hop encryption keys and routing information.

    😐 This is what the sender uses to build an onion packet.
    """

    nodes: list[NodeInfo]
    layer_keys: list[bytes] = field(default_factory=list)
    routing_info: list[LayerRoutingInfo] = field(default_factory=list)

    @property
    def hop_count(self) -> int:
        """Number of hops in the path."""
        return len(self.nodes)

    @property
    def entry_node(self) -> NodeInfo:
        """First node in path (entry point)."""
        return self.nodes[0]

    @property
    def exit_node(self) -> NodeInfo:
        """Last node in path (exit point)."""
        return self.nodes[-1]

    def build_packet_path(self) -> list[tuple[bytes, LayerRoutingInfo]]:
        """
        Build the (layer_key, routing_info) tuples for packet construction.

        Returns list ordered from innermost to outermost layer,
        matching build_onion_packet's expected format.

        😐 Innermost layer = exit node. Outermost = entry node.
        """
        if not self.layer_keys or not self.routing_info:
            msg = "Path keys and routing info not yet generated"
            raise RoutingError(msg)
        # Reverse: nodes[0]=entry (outermost) → nodes[-1]=exit (innermost)
        # build_onion_packet expects innermost first
        return list(
            zip(
                reversed(self.layer_keys),
                list(reversed(self.routing_info)),
                strict=True,
            )
        )


class PathSelector:
    """
    😐 Selects routing paths through the Anemochory network.

    Enforces anonymity constraints:
    1. Entry node must have ENTRY capability
    2. Exit node must have EXIT capability
    3. Intermediate nodes must have RELAY capability
    4. All nodes must meet minimum reputation threshold
    5. No two nodes from the same /24 subnet (Sybil resistance)
    6. Path length within MIN_HOPS..MAX_HOPS

    🌑 Dark Harold: Path diversity is non-negotiable.
    An adversary controlling multiple nodes in the same subnet
    can correlate traffic. Subnet checks prevent this.
    """

    def __init__(
        self,
        pool: NodePool,
        hop_count: int = DEFAULT_HOP_COUNT,
        min_reputation: float = MIN_REPUTATION,
        enforce_subnet_diversity: bool = DEFAULT_DIVERSITY_SUBNETS,
    ) -> None:
        """
        Initialize path selector.

        Args:
            pool: Pool of available nodes
            hop_count: Desired path length (3-7)
            min_reputation: Minimum node reputation for inclusion
            enforce_subnet_diversity: Require unique /24 subnets per hop

        Raises:
            ValueError: If hop_count out of range
        """
        if not MIN_HOPS <= hop_count <= MAX_HOPS:
            msg = f"hop_count must be {MIN_HOPS}-{MAX_HOPS}, got {hop_count}"
            raise ValueError(msg)

        self._pool = pool
        self._hop_count = hop_count
        self._min_reputation = min_reputation
        self._enforce_subnet_diversity = enforce_subnet_diversity

    def select_path(self, exclude_node_ids: set[bytes] | None = None) -> RoutingPath:
        """
        Select a random path satisfying all constraints.

        Algorithm:
        1. Select entry node (ENTRY capability)
        2. Select exit node (EXIT capability, different subnet)
        3. Fill intermediate hops (RELAY, unique subnets)
        4. Generate layer keys via HKDF
        5. Build routing info for each hop

        Args:
            exclude_node_ids: Node IDs to exclude (e.g., self)

        Returns:
            Complete RoutingPath with keys and routing info

        Raises:
            InsufficientNodesError: If pool too small
            PathConstraintError: If constraints unsatisfiable

        🌑 Security Note: Uses secrets.SystemRandom for all random
        selection. random module is FORBIDDEN.
        """
        exclude_node_ids = exclude_node_ids or set()

        # Step 1: Select entry node
        entry = self._select_node(
            capability=NodeCapability.ENTRY,
            exclude_ids=exclude_node_ids,
            exclude_subnets=set(),
        )
        if entry is None:
            raise InsufficientNodesError("No entry nodes available")

        used_ids = {entry.node_id} | exclude_node_ids
        used_subnets = {entry.subnet_prefix} if self._enforce_subnet_diversity else set()

        # Step 2: Select exit node
        exit_node = self._select_node(
            capability=NodeCapability.EXIT,
            exclude_ids=used_ids,
            exclude_subnets=used_subnets,
        )
        if exit_node is None:
            raise InsufficientNodesError("No exit nodes available (with subnet diversity)")

        used_ids.add(exit_node.node_id)
        if self._enforce_subnet_diversity:
            used_subnets.add(exit_node.subnet_prefix)

        # Step 3: Fill intermediate hops
        intermediate_count = self._hop_count - 2  # entry + exit already selected
        intermediates: list[NodeInfo] = []

        for _ in range(intermediate_count):
            relay = self._select_node(
                capability=NodeCapability.RELAY,
                exclude_ids=used_ids,
                exclude_subnets=used_subnets,
            )
            if relay is None:
                raise PathConstraintError(
                    f"Cannot fill {intermediate_count} intermediate hops "
                    f"with subnet diversity (found {len(intermediates)})"
                )
            intermediates.append(relay)
            used_ids.add(relay.node_id)
            if self._enforce_subnet_diversity:
                used_subnets.add(relay.subnet_prefix)

        # Step 4: Assemble path: entry → intermediates → exit
        nodes = [entry, *intermediates, exit_node]

        # Step 5: Generate per-hop layer keys
        path = RoutingPath(nodes=nodes)
        self._generate_keys(path)
        self._generate_routing_info(path)

        return path

    def _select_node(
        self,
        capability: NodeCapability,
        exclude_ids: set[bytes],
        exclude_subnets: set[str],
    ) -> NodeInfo | None:
        """
        Select a random node matching criteria.

        Uses weighted random selection biased toward higher reputation.
        🌑 Pure random from filtered set prevents prediction.
        """
        candidates = self._pool.filter(
            capability=capability,
            min_reputation=self._min_reputation,
            exclude_ids=exclude_ids,
            exclude_subnets=exclude_subnets if self._enforce_subnet_diversity else None,
        )
        if not candidates:
            return None

        # 😐 Weighted random by reputation (better nodes more likely)
        # Using secrets.SystemRandom for cryptographic randomness
        rng = secrets.SystemRandom()
        weights = [n.reputation for n in candidates]
        total = sum(weights)
        if total == 0:
            return rng.choice(candidates)

        # Weighted selection
        r = rng.uniform(0, total)
        cumulative = 0.0
        for node, weight in zip(candidates, weights, strict=True):
            cumulative += weight
            if r <= cumulative:
                return node
        return candidates[-1]  # 😐 Fallback (floating point edge case)

    def _generate_keys(self, path: RoutingPath) -> None:
        """
        Generate per-hop layer keys using HKDF.

        Each hop gets a unique key derived from a random master secret.
        🌑 Master secret is ephemeral — only exists during path creation.
        """
        master_secret = ChaCha20Engine.generate_key()
        path.layer_keys = [
            derive_layer_key(master_secret, i, path.hop_count)
            for i in range(path.hop_count)
        ]

    def _generate_routing_info(self, path: RoutingPath) -> None:
        """
        Generate routing info telling each hop where to forward.

        Each hop's routing info contains the next hop's address/port.
        The exit node's routing info has a zeroed next_hop (terminal).
        """
        session_id = secrets.token_bytes(16)
        routing_info: list[LayerRoutingInfo] = []

        for i, node in enumerate(path.nodes):
            if i < path.hop_count - 1:
                # Point to next hop
                next_node = path.nodes[i + 1]
                # Pack IPv4 address into 16 bytes (4 bytes addr + 12 zero padding)
                addr_bytes = _pack_address(next_node.address)
                info = LayerRoutingInfo(
                    next_hop_address=addr_bytes,
                    next_hop_port=next_node.port,
                    sequence_number=0,  # Set during packet build
                    session_id=session_id,
                    padding_length=0,  # Set during packet build
                )
            else:
                # Exit node: no next hop
                info = LayerRoutingInfo(
                    next_hop_address=b"\x00" * 16,
                    next_hop_port=0,
                    sequence_number=0,
                    session_id=session_id,
                    padding_length=0,
                )
            routing_info.append(info)

        path.routing_info = routing_info


def _pack_address(address: str) -> bytes:
    """
    Pack an IP address string into 16 bytes.

    IPv4: 4 bytes + 12 zero padding
    IPv6: 16 bytes native

    😐 This is the simplest address encoding. It works.
    """
    import ipaddress

    addr = ipaddress.ip_address(address)
    if isinstance(addr, ipaddress.IPv4Address):
        return addr.packed + b"\x00" * 12
    return addr.packed
