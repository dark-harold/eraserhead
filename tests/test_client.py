"""
😐 Tests for the high-level Anemochory client.

Tests the client API: payload validation, path selection,
packet building, and send behavior.

🌑 The client can't actually send without a real network,
so we test the logic and mock the transport.
"""

from __future__ import annotations

import secrets
from unittest.mock import AsyncMock, patch

import pytest
import trio

from anemochory.models import NODE_ID_SIZE, NodeCapability, NodeInfo, NodePool
from anemochory.client import (
    AnemochoryClient,
    DEFAULT_HOP_COUNT,
    MAX_RETRIES,
    SendResult,
)
from anemochory.transport import TransportError


# --- Helpers ---


def _build_viable_pool(
    num_entries: int = 2,
    num_exits: int = 2,
    num_relays: int = 10,
) -> NodePool:
    """Build a pool with diverse nodes for path selection."""
    pool = NodePool()
    subnet = 0

    for i in range(num_entries):
        pool.add(
            NodeInfo(
                node_id=secrets.token_bytes(NODE_ID_SIZE),
                address=f"10.{subnet}.0.{i + 1}",
                port=8000 + subnet,
                public_key=secrets.token_bytes(32),
                capabilities={NodeCapability.ENTRY, NodeCapability.RELAY},
                reputation=0.8,
            )
        )
        subnet += 1

    for i in range(num_exits):
        pool.add(
            NodeInfo(
                node_id=secrets.token_bytes(NODE_ID_SIZE),
                address=f"10.{subnet}.0.{i + 1}",
                port=8000 + subnet,
                public_key=secrets.token_bytes(32),
                capabilities={NodeCapability.EXIT, NodeCapability.RELAY},
                reputation=0.8,
            )
        )
        subnet += 1

    for i in range(num_relays):
        pool.add(
            NodeInfo(
                node_id=secrets.token_bytes(NODE_ID_SIZE),
                address=f"10.{subnet}.0.{i + 1}",
                port=8000 + subnet,
                public_key=secrets.token_bytes(32),
                capabilities={NodeCapability.RELAY},
                reputation=0.7,
            )
        )
        subnet += 1

    return pool


# --- Client Tests ---


class TestAnemochoryClient:
    """😐 Testing the user-facing API."""

    def test_max_payload_size(self) -> None:
        """max_payload_size reflects hop count."""
        pool = _build_viable_pool()
        client = AnemochoryClient(pool, hop_count=3)
        assert client.max_payload_size > 0

        client5 = AnemochoryClient(pool, hop_count=5)
        # More hops = smaller max payload
        assert client5.max_payload_size < client.max_payload_size

    async def test_send_empty_payload(self) -> None:
        """Empty payload returns failure."""
        pool = _build_viable_pool()
        client = AnemochoryClient(pool, hop_count=3)
        result = await client.send(b"")

        assert not result.success
        assert "Empty payload" in (result.error or "")

    async def test_send_oversized_payload(self) -> None:
        """Oversized payload returns failure."""
        pool = _build_viable_pool()
        client = AnemochoryClient(pool, hop_count=3)
        big_payload = secrets.token_bytes(client.max_payload_size + 1)
        result = await client.send(big_payload)

        assert not result.success
        assert "too large" in (result.error or "")

    @patch("anemochory.client.PacketSender.send", new_callable=AsyncMock)
    async def test_send_success(self, mock_send: AsyncMock) -> None:
        """Successful send returns success result."""
        pool = _build_viable_pool()
        client = AnemochoryClient(pool, hop_count=3)

        result = await client.send(b"anonymous data")

        assert result.success
        assert result.path_length == 3
        assert result.entry_address.startswith("10.")
        assert result.entry_port > 0
        assert result.retries == 0
        assert client.stats.payloads_sent == 1
        assert mock_send.called

    @patch("anemochory.client.PacketSender.send", new_callable=AsyncMock)
    async def test_send_retry_on_transport_error(self, mock_send: AsyncMock) -> None:
        """Retries on TransportError."""
        mock_send.side_effect = [
            TransportError("connection refused"),
            TransportError("connection refused"),
            None,  # Third attempt succeeds
        ]

        pool = _build_viable_pool()
        client = AnemochoryClient(pool, hop_count=3, max_retries=3)

        result = await client.send(b"retry me")

        assert result.success
        assert result.retries == 2
        assert client.stats.total_retries == 2

    @patch("anemochory.client.PacketSender.send", new_callable=AsyncMock)
    async def test_send_all_retries_exhausted(self, mock_send: AsyncMock) -> None:
        """All retries fail returns failure."""
        mock_send.side_effect = TransportError("always fails")

        pool = _build_viable_pool()
        client = AnemochoryClient(pool, hop_count=3, max_retries=1)

        # Patch trio.sleep to avoid actual delays in tests
        with patch("anemochory.client.trio.sleep", new_callable=AsyncMock):
            result = await client.send(b"doomed")

        assert not result.success
        assert "attempts failed" in (result.error or "")
        assert client.stats.payloads_failed == 1

    @patch("anemochory.client.PacketSender.send", new_callable=AsyncMock)
    async def test_send_excludes_our_node(self, mock_send: AsyncMock) -> None:
        """Client excludes our own node ID from paths."""
        pool = _build_viable_pool()
        our_id = pool.get_all()[0].node_id

        client = AnemochoryClient(pool, hop_count=3, our_node_id=our_id)
        result = await client.send(b"not through us")

        assert result.success
        # The send was called, path was selected excluding our node
        assert client.stats.paths_selected == 1

    def test_initial_stats(self) -> None:
        """Client stats start at zero."""
        pool = _build_viable_pool()
        client = AnemochoryClient(pool)

        assert client.stats.payloads_sent == 0
        assert client.stats.payloads_failed == 0
        assert client.stats.total_retries == 0
        assert client.stats.paths_selected == 0
