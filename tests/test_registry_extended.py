"""
😐 Extended tests for Provider Registry.

Testing event log LRU eviction, async error handling,
health check edge cases, and subscription management.

🌑 Harold's phone book needs stress testing.
"""

from __future__ import annotations

from typing import Any

import pytest

from eraserhead.providers.base import (
    ProviderCapability,
    ProviderEvent,
    ProviderEventType,
    ProviderHealth,
    ProviderInfo,
    ProviderStatus,
    ProviderType,
    SearchProvider,
    SearchResult,
)
from eraserhead.providers.registry import (
    ProviderNotFoundError,
    ProviderRegistry,
)


# ============================================================================
# Test Helpers
# ============================================================================


class SimpleSearchProvider(SearchProvider):
    """Minimal search provider for registry tests."""

    def __init__(
        self,
        provider_id: str = "simple-search",
        healthy: bool = True,
        init_success: bool = True,
    ) -> None:
        super().__init__(
            info=ProviderInfo(
                provider_id=provider_id,
                name=f"Simple Search ({provider_id})",
                provider_type=ProviderType.SEARCH,
                capabilities={ProviderCapability.SEARCH_BY_EMAIL},
            )
        )
        self._healthy = healthy
        self._init_success = init_success

    async def _do_initialize(self, config: dict[str, Any]) -> bool:
        return self._init_success

    async def _do_health_check(self) -> ProviderHealth:
        if self._healthy:
            return ProviderHealth(is_healthy=True, status=ProviderStatus.READY)
        return ProviderHealth(
            is_healthy=False,
            status=ProviderStatus.ERROR,
            error_message="😐 Provider is not feeling well",
        )

    async def search(
        self,
        query: str,
        *,
        search_type: str = "general",
        max_results: int = 50,
        metadata: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        return []


class FailingProvider(SearchProvider):
    """Provider that raises during health check."""

    def __init__(self, provider_id: str = "failing") -> None:
        super().__init__(
            info=ProviderInfo(
                provider_id=provider_id,
                name="Failing Provider",
                provider_type=ProviderType.SEARCH,
                capabilities=set(),
            )
        )

    async def _do_initialize(self, config: dict[str, Any]) -> bool:
        raise RuntimeError("💥 Init explosion")

    async def _do_health_check(self) -> ProviderHealth:
        raise ConnectionError("💥 Health check explosion")

    async def search(self, query: str, **kwargs: Any) -> list[SearchResult]:
        return []


# ============================================================================
# Event Log LRU Eviction Tests
# ============================================================================


class TestEventLogEviction:
    """😐 Testing LRU eviction of the event log."""

    def test_event_log_respects_max_size(self) -> None:
        """Event log should evict oldest events when full."""
        registry = ProviderRegistry()
        registry._max_event_log = 20  # Small limit for testing

        # Register/unregister enough providers to exceed limit
        for i in range(15):
            p = SimpleSearchProvider(f"provider-{i}")
            registry.register(p)

        # Should have pruned old events
        assert len(registry._event_log) <= 20

    def test_event_log_eviction_preserves_recent(self) -> None:
        """After eviction, most recent events should still be there."""
        registry = ProviderRegistry()
        registry._max_event_log = 10

        for i in range(20):
            p = SimpleSearchProvider(f"p-{i}")
            registry.register(p)

        events = registry.get_event_log()
        # Should have the most recent events
        recent_ids = {e.provider_id for e in events}
        # The very last registered provider should be in events
        assert "p-19" in recent_ids

    def test_event_log_filtered_by_type(self) -> None:
        """get_event_log with type filter works correctly."""
        registry = ProviderRegistry()
        p = SimpleSearchProvider("test-p")
        registry.register(p)
        registry.unregister("test-p")

        reg_events = registry.get_event_log(event_type=ProviderEventType.PROVIDER_REGISTERED)
        unreg_events = registry.get_event_log(event_type=ProviderEventType.PROVIDER_REMOVED)
        assert len(reg_events) >= 1
        assert len(unreg_events) >= 1

    def test_event_log_limit(self) -> None:
        """get_event_log limit parameter works."""
        registry = ProviderRegistry()
        for i in range(10):
            registry.register(SimpleSearchProvider(f"p-{i}"))

        events = registry.get_event_log(limit=3)
        assert len(events) == 3


# ============================================================================
# Async Event Emission Tests
# ============================================================================


class TestAsyncEventEmission:
    """😐 Testing async pub/sub event handling."""

    async def test_async_handler_error_doesnt_stop_propagation(self) -> None:
        """Error in one async handler shouldn't stop others."""
        registry = ProviderRegistry()
        received: list[ProviderEvent] = []

        async def failing_handler(event: ProviderEvent) -> None:
            raise ValueError("💥 Handler exploded")

        async def working_handler(event: ProviderEvent) -> None:
            received.append(event)

        registry.subscribe(ProviderEventType.SEARCH_COMPLETED, failing_handler)
        registry.subscribe(ProviderEventType.SEARCH_COMPLETED, working_handler)

        await registry.emit(
            ProviderEvent(
                event_type=ProviderEventType.SEARCH_COMPLETED,
                provider_id="test",
            )
        )

        # Working handler should still receive the event
        assert len(received) == 1

    async def test_sync_handler_in_async_emit(self) -> None:
        """Sync handlers (returning None) should work in async emit."""
        registry = ProviderRegistry()
        received: list[ProviderEvent] = []

        def sync_handler(event: ProviderEvent) -> None:
            received.append(event)

        registry.subscribe(ProviderEventType.SEARCH_COMPLETED, sync_handler)

        await registry.emit(
            ProviderEvent(
                event_type=ProviderEventType.SEARCH_COMPLETED,
                provider_id="test",
            )
        )
        assert len(received) == 1

    def test_sync_emit_skips_async_handlers(self) -> None:
        """_emit_sync should skip async handlers with warning."""
        registry = ProviderRegistry()
        sync_received: list[ProviderEvent] = []

        async def async_handler(event: ProviderEvent) -> None:
            pass  # Should be skipped

        def sync_handler(event: ProviderEvent) -> None:
            sync_received.append(event)

        registry.subscribe(ProviderEventType.PROVIDER_REGISTERED, async_handler)
        registry.subscribe(ProviderEventType.PROVIDER_REGISTERED, sync_handler)

        # Register triggers _emit_sync
        registry.register(SimpleSearchProvider("sync-test"))

        # Sync handler should have received the event
        assert len(sync_received) >= 1

    def test_sync_emit_handler_error(self) -> None:
        """Error in sync handler shouldn't crash registration."""
        registry = ProviderRegistry()

        def bad_handler(event: ProviderEvent) -> None:
            raise RuntimeError("💥")

        registry.subscribe(ProviderEventType.PROVIDER_REGISTERED, bad_handler)

        # Should not raise
        registry.register(SimpleSearchProvider("error-test"))
        assert registry.provider_count == 1


# ============================================================================
# Health Check Tests
# ============================================================================


class TestHealthCheck:
    """😐 Testing health monitoring."""

    async def test_check_healthy_provider(self) -> None:
        registry = ProviderRegistry()
        p = SimpleSearchProvider("healthy-p", healthy=True)
        await p.initialize()
        registry.register(p)

        health = await registry.check_health("healthy-p")
        assert health.is_healthy
        assert health.status == ProviderStatus.READY

    async def test_check_unhealthy_provider_emits_error_event(self) -> None:
        """Unhealthy provider should trigger ERROR_OCCURRED event."""
        registry = ProviderRegistry()
        p = SimpleSearchProvider("sick-p", healthy=False)
        await p.initialize()
        registry.register(p)

        error_events: list[ProviderEvent] = []

        async def capture_error(event: ProviderEvent) -> None:
            error_events.append(event)

        registry.subscribe(ProviderEventType.ERROR_OCCURRED, capture_error)

        health_results = await registry.check_all_health()
        assert not health_results["sick-p"].is_healthy
        assert len(error_events) == 1

    async def test_check_failing_provider(self) -> None:
        """Provider that raises during health check."""
        registry = ProviderRegistry()
        p = FailingProvider("crash-p")
        # Skip initialize (it would fail) — manually set status
        p._status = ProviderStatus.READY
        registry.register(p)

        health = await registry.check_health("crash-p")
        assert not health.is_healthy
        assert health.status == ProviderStatus.ERROR

    async def test_cached_health(self) -> None:
        """Health cache should store last result."""
        registry = ProviderRegistry()
        p = SimpleSearchProvider("cached-p")
        await p.initialize()
        registry.register(p)

        # No cache initially
        assert registry.get_cached_health("cached-p") is None

        # After check, cache populated
        await registry.check_health("cached-p")
        cached = registry.get_cached_health("cached-p")
        assert cached is not None
        assert cached.is_healthy

    async def test_check_nonexistent_provider(self) -> None:
        registry = ProviderRegistry()
        with pytest.raises(ProviderNotFoundError):
            await registry.check_health("ghost")


# ============================================================================
# Subscription Management Tests
# ============================================================================


class TestSubscriptionManagement:
    """😐 Testing subscribe/unsubscribe edge cases."""

    def test_unsubscribe_returns_false_for_unknown(self) -> None:
        registry = ProviderRegistry()

        def handler(event: ProviderEvent) -> None:
            pass

        result = registry.unsubscribe(ProviderEventType.SEARCH_COMPLETED, handler)
        assert result is False

    def test_multiple_subscriptions_same_handler(self) -> None:
        """Same handler can subscribe to multiple event types."""
        registry = ProviderRegistry()
        received: list[ProviderEvent] = []

        def handler(event: ProviderEvent) -> None:
            received.append(event)

        registry.subscribe(ProviderEventType.PROVIDER_REGISTERED, handler)
        registry.subscribe(ProviderEventType.PROVIDER_REMOVED, handler)

        registry.register(SimpleSearchProvider("multi-sub"))
        registry.unregister("multi-sub")

        assert len(received) == 2

    def test_subscribe_all_receives_all_events(self) -> None:
        """subscribe_all should receive register and unregister events."""
        registry = ProviderRegistry()
        received: list[ProviderEvent] = []

        def handler(event: ProviderEvent) -> None:
            received.append(event)

        registry.subscribe_all(handler)
        registry.register(SimpleSearchProvider("all-sub"))
        registry.unregister("all-sub")

        types = {e.event_type for e in received}
        assert ProviderEventType.PROVIDER_REGISTERED in types
        assert ProviderEventType.PROVIDER_REMOVED in types


# ============================================================================
# Provider Discovery Edge Cases
# ============================================================================


class TestProviderDiscovery:
    """😐 Testing provider query methods."""

    def test_get_ready_providers_empty(self) -> None:
        registry = ProviderRegistry()
        assert registry.get_ready_providers() == []

    async def test_get_ready_providers_filters_uninitialized(self) -> None:
        registry = ProviderRegistry()
        unready = SimpleSearchProvider("unready")
        ready = SimpleSearchProvider("ready")
        await ready.initialize()

        registry.register(unready)
        registry.register(ready)

        ready_providers = registry.get_ready_providers()
        assert len(ready_providers) == 1
        assert ready_providers[0].provider_id == "ready"

    def test_all_providers_returns_copy(self) -> None:
        """all_providers should return a copy, not internal dict."""
        registry = ProviderRegistry()
        p = SimpleSearchProvider("copy-test")
        registry.register(p)

        providers = registry.all_providers
        providers["injected"] = p  # type: ignore[assignment]
        assert "injected" not in registry._providers

    def test_summary_with_no_providers(self) -> None:
        registry = ProviderRegistry()
        summary = registry.summary()
        assert summary["total_providers"] == 0
        assert summary["total_subscribers"] == 0

    async def test_get_by_capability_mixed_ready(self) -> None:
        """ready_only should filter uninitialized providers."""
        registry = ProviderRegistry()
        ready = SimpleSearchProvider("ready-cap")
        unready = SimpleSearchProvider("unready-cap")
        await ready.initialize()

        registry.register(ready)
        registry.register(unready)

        # ready_only=True should only return initialized
        results = registry.get_by_capability(ProviderCapability.SEARCH_BY_EMAIL, ready_only=True)
        assert len(results) == 1
        assert results[0].provider_id == "ready-cap"

        # ready_only=False returns both
        results = registry.get_by_capability(ProviderCapability.SEARCH_BY_EMAIL, ready_only=False)
        assert len(results) == 2


# ============================================================================
# Provider Lifecycle Edge Cases
# ============================================================================


class TestProviderLifecycleEdgeCases:
    """🌑 Edge cases in provider initialization and teardown."""

    async def test_initialize_failure(self) -> None:
        """Provider that fails to initialize should be in ERROR state."""
        p = FailingProvider("fail-init")
        result = await p.initialize()
        assert result is False
        assert p.status == ProviderStatus.ERROR

    async def test_initialize_returns_false(self) -> None:
        """Provider returning False from init stays in ERROR."""
        p = SimpleSearchProvider("soft-fail", init_success=False)
        result = await p.initialize()
        assert result is False
        assert p.status == ProviderStatus.ERROR

    async def test_teardown_sets_disabled(self) -> None:
        p = SimpleSearchProvider("teardown-test")
        await p.initialize()
        assert p.is_ready
        await p.teardown()
        assert p.status == ProviderStatus.DISABLED
        assert not p.is_ready
