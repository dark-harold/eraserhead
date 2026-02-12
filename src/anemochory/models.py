"""
😐 Anemochory Protocol: Node Identity & Discovery Models

Defines node identity, capabilities, and pool management for routing.
Each node in the Anemochory network has a cryptographic identity and
advertised capabilities that routing algorithms use for path selection.

🌑 Dark Harold: Node identity is public. Node compromise is assumed.
   Design so that no single node can deanonymize traffic.
"""

from __future__ import annotations

import ipaddress
import json
import secrets
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


# 😐 Constants
NODE_ID_SIZE = 16  # 128-bit node identifier
MIN_POOL_SIZE = 9  # Minimum nodes for 3-hop diversity
DEFAULT_HOP_COUNT = 5  # Balanced anonymity/latency


class NodeCapability(StrEnum):
    """
    Advertised node capabilities.

    😐 Nodes declare what they can do. We verify later (or not).
    🌑 Malicious nodes will lie about capabilities. Trust nothing.
    """

    RELAY = "relay"  # Can forward packets
    EXIT = "exit"  # Can make external requests
    ENTRY = "entry"  # Accepts incoming connections
    HIGH_BANDWIDTH = "high_bandwidth"  # >100 Mbps
    LOW_LATENCY = "low_latency"  # <50ms avg RTT


@dataclass
class NodeInfo:
    """
    Identity and metadata for a single Anemochory node.

    😐 This is the public face of a node. Private keys stay private.
    🌑 All fields are attacker-visible. Design accordingly.

    Attributes:
        node_id: Unique 16-byte identifier (derived from public key hash)
        address: Network address (IPv4/IPv6 string)
        port: Listening port
        public_key: X25519 public key for key exchange (32 bytes)
        capabilities: Set of advertised capabilities
        reputation: Trust score 0.0-1.0 (1.0 = fully trusted)
        subnet: /24 subnet prefix for diversity enforcement
    """

    node_id: bytes
    address: str
    port: int
    public_key: bytes
    capabilities: set[NodeCapability] = field(default_factory=lambda: {NodeCapability.RELAY})
    reputation: float = 0.5

    def __post_init__(self) -> None:
        """Validate node identity fields."""
        if len(self.node_id) != NODE_ID_SIZE:
            msg = f"node_id must be {NODE_ID_SIZE} bytes, got {len(self.node_id)}"
            raise ValueError(msg)
        if len(self.public_key) != 32:
            msg = f"public_key must be 32 bytes, got {len(self.public_key)}"
            raise ValueError(msg)
        if not 1 <= self.port <= 65535:
            msg = f"port must be 1-65535, got {self.port}"
            raise ValueError(msg)
        if not 0.0 <= self.reputation <= 1.0:
            msg = f"reputation must be 0.0-1.0, got {self.reputation}"
            raise ValueError(msg)
        # Validate address is parseable
        try:
            ipaddress.ip_address(self.address)
        except ValueError as e:
            msg = f"Invalid address: {self.address}"
            raise ValueError(msg) from e

    @property
    def subnet_prefix(self) -> str:
        """
        Get /24 subnet prefix for diversity enforcement.

        🌑 Nodes in the same /24 might be controlled by the same operator.
        """
        addr = ipaddress.ip_address(self.address)
        if isinstance(addr, ipaddress.IPv4Address):
            # /24 prefix: first 3 octets
            parts = str(addr).split(".")
            return f"{parts[0]}.{parts[1]}.{parts[2]}"
        # IPv6: /48 prefix
        network = ipaddress.IPv6Network(f"{addr}/48", strict=False)
        return str(network.network_address)

    @property
    def can_relay(self) -> bool:
        """Check if node can relay packets."""
        return NodeCapability.RELAY in self.capabilities

    @property
    def can_exit(self) -> bool:
        """Check if node can serve as exit node."""
        return NodeCapability.EXIT in self.capabilities

    def to_dict(self) -> dict[str, object]:
        """Serialize to JSON-compatible dict."""
        return {
            "node_id": self.node_id.hex(),
            "address": self.address,
            "port": self.port,
            "public_key": self.public_key.hex(),
            "capabilities": sorted(self.capabilities),
            "reputation": self.reputation,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NodeInfo:
        """Deserialize from JSON-compatible dict."""
        return cls(
            node_id=bytes.fromhex(data["node_id"]),
            address=data["address"],
            port=data["port"],
            public_key=bytes.fromhex(data["public_key"]),
            capabilities={NodeCapability(c) for c in data.get("capabilities", ["relay"])},
            reputation=data.get("reputation", 0.5),
        )

    def __hash__(self) -> int:
        """Hash by node_id for set operations."""
        return hash(self.node_id)

    def __eq__(self, other: object) -> bool:
        """Equality by node_id."""
        if not isinstance(other, NodeInfo):
            return NotImplemented
        return self.node_id == other.node_id


class NodePoolError(Exception):
    """Raised when node pool operations fail."""


class NodePool:
    """
    😐 Registry of known Anemochory nodes.

    Manages the set of nodes available for routing. Supports
    filtering by capability, reputation thresholds, and subnet
    diversity constraints.

    🌑 Dark Harold: A compromised pool = compromised routing.
    Bootstrap from multiple sources. Verify node identities.
    """

    def __init__(self) -> None:
        """Initialize empty node pool."""
        self._nodes: dict[bytes, NodeInfo] = {}

    def add(self, node: NodeInfo) -> None:
        """
        Add a node to the pool.

        Args:
            node: Node to register

        Raises:
            NodePoolError: If node_id conflicts with different node
        """
        existing = self._nodes.get(node.node_id)
        if existing is not None and existing.public_key != node.public_key:
            msg = f"Node ID conflict: {node.node_id.hex()[:8]}... has different public key"
            raise NodePoolError(msg)
        self._nodes[node.node_id] = node

    def remove(self, node_id: bytes) -> None:
        """Remove a node by ID. Silently ignores unknown nodes."""
        self._nodes.pop(node_id, None)

    def get(self, node_id: bytes) -> NodeInfo | None:
        """Get node by ID, or None if not found."""
        return self._nodes.get(node_id)

    def filter(
        self,
        capability: NodeCapability | None = None,
        min_reputation: float = 0.0,
        exclude_ids: set[bytes] | None = None,
        exclude_subnets: set[str] | None = None,
    ) -> list[NodeInfo]:
        """
        Filter nodes by criteria.

        Args:
            capability: Required capability (None = any)
            min_reputation: Minimum reputation score
            exclude_ids: Node IDs to exclude
            exclude_subnets: Subnet prefixes to exclude

        Returns:
            List of matching nodes, sorted by reputation (descending)
        """
        exclude_ids = exclude_ids or set()
        exclude_subnets = exclude_subnets or set()

        result = []
        for node in self._nodes.values():
            if node.node_id in exclude_ids:
                continue
            if node.reputation < min_reputation:
                continue
            if capability is not None and capability not in node.capabilities:
                continue
            if node.subnet_prefix in exclude_subnets:
                continue
            result.append(node)

        # Sort by reputation descending (best nodes first)
        result.sort(key=lambda n: n.reputation, reverse=True)
        return result

    @property
    def size(self) -> int:
        """Number of nodes in pool."""
        return len(self._nodes)

    @property
    def is_viable(self) -> bool:
        """
        Check if pool has enough nodes for minimum path diversity.

        😐 Need at least MIN_POOL_SIZE nodes for 3-hop paths
        with subnet diversity.
        """
        return self.size >= MIN_POOL_SIZE

    def get_all(self) -> list[NodeInfo]:
        """Get all nodes in the pool."""
        return list(self._nodes.values())

    def save(self, path: Path) -> None:
        """
        Save pool to JSON file.

        😐 Bootstrap node list persistence.
        🌑 Verify integrity after loading (nodes could be tampered).
        """
        data = {"nodes": [node.to_dict() for node in self._nodes.values()]}
        path.write_text(json.dumps(data, indent=2))

    @classmethod
    def load(cls, path: Path) -> NodePool:
        """Load pool from JSON file."""
        pool = cls()
        data = json.loads(path.read_text())
        for node_data in data.get("nodes", []):
            pool.add(NodeInfo.from_dict(node_data))
        return pool

    @classmethod
    def create_test_pool(cls, size: int = MIN_POOL_SIZE) -> NodePool:
        """
        Create a pool of test nodes with random identities.

        😐 For testing only. Real pools come from bootstrapping.
        """
        pool = cls()
        for i in range(size):
            capabilities = {NodeCapability.RELAY}
            if i == size - 1:
                capabilities.add(NodeCapability.EXIT)
            if i == 0:
                capabilities.add(NodeCapability.ENTRY)

            node = NodeInfo(
                node_id=secrets.token_bytes(NODE_ID_SIZE),
                address=f"10.0.{i // 256}.{i % 256 + 1}",
                port=8000 + i,
                public_key=secrets.token_bytes(32),
                capabilities=capabilities,
                reputation=0.5 + (secrets.randbelow(50) / 100),
            )
            pool.add(node)
        return pool

    def __len__(self) -> int:
        return self.size

    def __repr__(self) -> str:
        return f"NodePool(size={self.size}, viable={self.is_viable})"
