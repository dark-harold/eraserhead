"""
😐 Anemochory Protocol: High-Level Client API

The user-facing interface for sending anonymized traffic.
Handles path selection, packet construction, and transmission
behind a simple API.

🌑 Dark Harold: This is the one API users interact with directly.
   If it's confusing, they'll bypass anonymization. Keep it simple.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import trio

from anemochory.models import NodePool
from anemochory.packet import (
    build_onion_packet,
    calculate_max_payload_size,
    generate_session_id,
)
from anemochory.routing import PathSelector
from anemochory.transport import PacketSender, TransportError


logger = logging.getLogger(__name__)


# ============================================================================
# Constants
# ============================================================================

DEFAULT_HOP_COUNT = 5
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 1.0


# ============================================================================
# Client
# ============================================================================


@dataclass
class SendResult:
    """Result of sending an anonymized payload."""

    success: bool
    path_length: int = 0
    entry_address: str = ""
    entry_port: int = 0
    error: str | None = None
    retries: int = 0


@dataclass
class ClientStats:
    """Client operational statistics."""

    payloads_sent: int = 0
    payloads_failed: int = 0
    total_retries: int = 0
    paths_selected: int = 0


class AnemochoryClient:
    """
    😐 High-level client for sending anonymized traffic.

    Orchestrates the full send pipeline:
    1. Select a random path through the network
    2. Build an onion-encrypted packet
    3. Send to the entry node via TCP

    Usage:
        pool = NodePool.create_test_pool(15)
        client = AnemochoryClient(pool, hop_count=5)

        # Synchronous-style with trio
        async with trio.open_nursery() as nursery:
            result = await client.send(b"anonymous payload")

    🌑 Dark Harold: The client knows the full path — it has to, to build
    the onion packet. But it never reveals the path to any single node.
    Each node only sees its own layer key and next hop.
    """

    def __init__(
        self,
        pool: NodePool,
        hop_count: int = DEFAULT_HOP_COUNT,
        max_retries: int = MAX_RETRIES,
        our_node_id: bytes | None = None,
    ) -> None:
        """
        Initialize the Anemochory client.

        Args:
            pool: Pool of available nodes
            hop_count: Number of hops per path (3-7)
            max_retries: Maximum retry attempts on failure
            our_node_id: Our own node ID to exclude from paths
        """
        self._pool = pool
        self._hop_count = hop_count
        self._max_retries = max_retries
        self._our_node_id = our_node_id
        self._sender = PacketSender()
        self._stats = ClientStats()

    @property
    def stats(self) -> ClientStats:
        """Client statistics."""
        return self._stats

    @property
    def max_payload_size(self) -> int:
        """Maximum payload size for configured hop count."""
        return calculate_max_payload_size(self._hop_count)

    async def send(self, payload: bytes) -> SendResult:
        """
        Send an anonymized payload through the Anemochory network.

        Steps:
        1. Validate payload size
        2. Select a random path
        3. Build onion-encrypted packet
        4. Send to entry node
        5. Retry on failure (up to max_retries)

        Args:
            payload: Data to send anonymously (max size depends on hop count)

        Returns:
            SendResult with success/failure and metadata

        😐 This is the simple API. All the crypto complexity is hidden.
        """
        max_size = self.max_payload_size
        if len(payload) > max_size:
            return SendResult(
                success=False,
                error=f"Payload too large: {len(payload)} bytes (max {max_size} for {self._hop_count} hops)",
            )

        if not payload:
            return SendResult(
                success=False,
                error="Empty payload",
            )

        exclude_ids = {self._our_node_id} if self._our_node_id else None
        retries = 0

        for attempt in range(self._max_retries + 1):
            try:
                # Select path
                selector = PathSelector(
                    self._pool,
                    hop_count=self._hop_count,
                )
                path = selector.select_path(exclude_node_ids=exclude_ids)
                self._stats.paths_selected += 1

                # Build onion packet
                session_id = generate_session_id()
                packet_path = path.build_packet_path()
                packet = build_onion_packet(
                    payload=payload,
                    path=packet_path,
                    _session_id=session_id,
                )

                # Send to entry node
                await self._sender.send(
                    packet=packet,
                    session_id=session_id,
                    address=path.entry_node.address,
                    port=path.entry_node.port,
                )

                self._stats.payloads_sent += 1
                return SendResult(
                    success=True,
                    path_length=path.hop_count,
                    entry_address=path.entry_node.address,
                    entry_port=path.entry_node.port,
                    retries=retries,
                )

            except TransportError:
                retries += 1
                self._stats.total_retries += 1
                if attempt < self._max_retries:
                    await trio.sleep(RETRY_DELAY_SECONDS)
                    continue
                break

            except Exception as e:
                self._stats.payloads_failed += 1
                return SendResult(
                    success=False,
                    error=f"Send failed: {e}",
                    retries=retries,
                )

        self._stats.payloads_failed += 1
        return SendResult(
            success=False,
            error=f"All {self._max_retries + 1} attempts failed",
            retries=retries,
        )
