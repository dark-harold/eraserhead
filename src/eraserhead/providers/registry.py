"""
😐 Provider Registry: Central hub for provider management and event routing.

All providers register here. All events flow through here.
Subscribers attach to event streams and react accordingly.

📺 The Registry Pattern:
  In the early days, systems had hardcoded integrations. Then came
  configuration files. Then service registries. Harold's registry
  combines all three with the added benefit of existential dread
  about which providers are actually working.

🌑 The registry is a single point of coordination, NOT a single
   point of failure. Providers operate independently — the registry
   just helps them find each other and keeps Harold informed.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Callable, Coroutine
from typing import Any

from eraserhead.providers.base import (
    BaseProvider,
    ComplianceProvider,
    ProviderCapability,
    ProviderEvent,
    ProviderEventType,
    ProviderHealth,
    ProviderType,
    ScrubProvider,
    SearchProvider,
)


logger = logging.getLogger(__name__)

# Type alias for event handler callbacks
EventSubscriber = Callable[[ProviderEvent], Coroutine[Any, Any, None] | None]


# ============================================================================
# Registry Errors
# ============================================================================


class RegistryError(Exception):
    """Base registry error."""


class ProviderAlreadyRegisteredError(RegistryError):
    """Provider with this ID already exists."""


class ProviderNotFoundError(RegistryError):
    """Requested provider not found in registry."""


class NoProvidersAvailableError(RegistryError):
    """No providers available for the requested capability."""


# ============================================================================
# Provider Registry
# ============================================================================


class ProviderRegistry:
    """
    😐 Central registry for all EraserHead providers.

    Manages provider lifecycle, capability discovery, event routing,
    and health monitoring. The beating heart of the provider ecosystem.

    Features:
    - Register/unregister providers dynamically
    - Query providers by type, capability, or status
    - Subscribe to provider events (pub/sub pattern)
    - Health monitoring with automatic status tracking
    - Provider priority ordering for fallback chains

    Usage:
        registry = ProviderRegistry()

        # Register providers
        registry.register(google_search_provider)
        registry.register(gdpr_compliance_provider)

        # Subscribe to events
        async def on_result(event):
            print(f"Found: {event.data}")
        registry.subscribe(ProviderEventType.SEARCH_RESULT, on_result)

        # Query providers
        searchers = registry.get_by_capability(ProviderCapability.SEARCH_BY_EMAIL)
        for provider in searchers:
            results = await provider.search("harold@example.com")

    📺 Think of this as the phone book for privacy tools.
    🌑 Unlike a phone book, this one doesn't leak your information.
    """

    def __init__(self) -> None:
        self._providers: dict[str, BaseProvider] = {}
        self._subscribers: dict[ProviderEventType, list[EventSubscriber]] = defaultdict(list)
        self._provider_priorities: dict[str, int] = {}  # provider_id → priority (lower = higher)
        self._health_cache: dict[str, ProviderHealth] = {}
        self._event_log: list[ProviderEvent] = []
        self._max_event_log: int = 10_000  # 😐 LRU-style, because memory isn't infinite

    # ========================================================================
    # Provider Registration
    # ========================================================================

    def register(
        self,
        provider: BaseProvider,
        priority: int = 100,
    ) -> None:
        """
        Register a provider with the registry.

        Args:
            provider: The provider instance to register
            priority: Priority for capability resolution (lower = preferred)

        Raises:
            ProviderAlreadyRegisteredError: If provider ID already exists
        """
        pid = provider.provider_id
        if pid in self._providers:
            raise ProviderAlreadyRegisteredError(
                f"😐 Provider already registered: {pid}. Harold doesn't do identity crises."
            )

        self._providers[pid] = provider
        self._provider_priorities[pid] = priority

        logger.info("Registered provider: %s (%s)", pid, provider.info.provider_type)
        self._emit_sync(
            ProviderEvent(
                event_type=ProviderEventType.PROVIDER_REGISTERED,
                provider_id=pid,
                data={"name": provider.info.name, "type": provider.info.provider_type},
            )
        )

    def unregister(self, provider_id: str) -> BaseProvider:
        """
        Remove a provider from the registry.

        Args:
            provider_id: ID of the provider to remove

        Returns:
            The removed provider instance

        Raises:
            ProviderNotFoundError: If provider not found
        """
        if provider_id not in self._providers:
            raise ProviderNotFoundError(f"Provider not found: {provider_id}")

        provider = self._providers.pop(provider_id)
        self._provider_priorities.pop(provider_id, None)
        self._health_cache.pop(provider_id, None)

        logger.info("Unregistered provider: %s", provider_id)
        self._emit_sync(
            ProviderEvent(
                event_type=ProviderEventType.PROVIDER_REMOVED,
                provider_id=provider_id,
            )
        )

        return provider

    # ========================================================================
    # Provider Discovery
    # ========================================================================

    def get(self, provider_id: str) -> BaseProvider:
        """
        Get a specific provider by ID.

        Raises:
            ProviderNotFoundError: If not found
        """
        if provider_id not in self._providers:
            raise ProviderNotFoundError(f"Provider not found: {provider_id}")
        return self._providers[provider_id]

    def get_by_type(self, provider_type: ProviderType) -> list[BaseProvider]:
        """Get all providers of a specific type, sorted by priority."""
        providers = [p for p in self._providers.values() if p.info.provider_type == provider_type]
        return sorted(providers, key=lambda p: self._provider_priorities.get(p.provider_id, 100))

    def get_search_providers(self) -> list[SearchProvider]:
        """Get all search providers, sorted by priority."""
        return [p for p in self.get_by_type(ProviderType.SEARCH) if isinstance(p, SearchProvider)]

    def get_scrub_providers(self) -> list[ScrubProvider]:
        """Get all scrub providers, sorted by priority."""
        return [p for p in self.get_by_type(ProviderType.SCRUB) if isinstance(p, ScrubProvider)]

    def get_compliance_providers(self) -> list[ComplianceProvider]:
        """Get all compliance providers, sorted by priority."""
        return [
            p
            for p in self.get_by_type(ProviderType.COMPLIANCE)
            if isinstance(p, ComplianceProvider)
        ]

    def get_by_capability(
        self,
        capability: ProviderCapability,
        *,
        ready_only: bool = True,
    ) -> list[BaseProvider]:
        """
        Find providers that support a specific capability.

        Args:
            capability: The capability to search for
            ready_only: Only return providers in READY status

        Returns:
            Matching providers sorted by priority
        """
        providers = [
            p
            for p in self._providers.values()
            if p.has_capability(capability) and (not ready_only or p.is_ready)
        ]
        return sorted(providers, key=lambda p: self._provider_priorities.get(p.provider_id, 100))

    def get_ready_providers(self) -> list[BaseProvider]:
        """Get all providers in READY status."""
        return [p for p in self._providers.values() if p.is_ready]

    @property
    def all_providers(self) -> dict[str, BaseProvider]:
        """All registered providers (read-only view)."""
        return dict(self._providers)

    @property
    def provider_count(self) -> int:
        """Number of registered providers."""
        return len(self._providers)

    # ========================================================================
    # Event Subscription (Pub/Sub)
    # ========================================================================

    def subscribe(
        self,
        event_type: ProviderEventType,
        handler: EventSubscriber,
    ) -> None:
        """
        Subscribe to provider events.

        Args:
            event_type: Type of event to listen for
            handler: Callback function (sync or async)

        😐 Harold event-sources his anxiety. Now your code can too.
        """
        self._subscribers[event_type].append(handler)

    def subscribe_all(self, handler: EventSubscriber) -> None:
        """Subscribe to ALL event types. Use sparingly."""
        for event_type in ProviderEventType:
            self._subscribers[event_type].append(handler)

    def unsubscribe(
        self,
        event_type: ProviderEventType,
        handler: EventSubscriber,
    ) -> bool:
        """
        Unsubscribe from events.

        Returns True if handler was found and removed.
        """
        handlers = self._subscribers[event_type]
        if handler in handlers:
            handlers.remove(handler)
            return True
        return False

    async def emit(self, event: ProviderEvent) -> None:
        """
        Emit an event to all subscribers (async version).

        Errors in handlers are logged but don't stop event propagation.
        🌑 One bad subscriber shouldn't bring down the whole system.
        """
        self._log_event(event)
        for handler in self._subscribers.get(event.event_type, []):
            try:
                result = handler(event)
                # If handler is async, await it
                if result is not None and hasattr(result, "__await__"):
                    await result
            except Exception as e:
                logger.error(
                    "Event handler error for %s: %s",
                    event.event_type,
                    e,
                )

    def _emit_sync(self, event: ProviderEvent) -> None:
        """
        Emit event synchronously (for registration/unregistration).

        Only calls sync handlers; async handlers are skipped with warning.
        """
        self._log_event(event)
        for handler in self._subscribers.get(event.event_type, []):
            try:
                result = handler(event)
                if result is not None and hasattr(result, "__await__"):
                    logger.warning(
                        "Async handler skipped in sync emit for %s",
                        event.event_type,
                    )
            except Exception as e:
                logger.error("Sync event handler error: %s", e)

    def _log_event(self, event: ProviderEvent) -> None:
        """Log event with LRU eviction."""
        self._event_log.append(event)
        if len(self._event_log) > self._max_event_log:
            # 😐 Evict oldest 10% — not one at a time, that's wasteful
            evict_count = self._max_event_log // 10
            self._event_log = self._event_log[evict_count:]

    # ========================================================================
    # Health Monitoring
    # ========================================================================

    async def check_all_health(self) -> dict[str, ProviderHealth]:
        """
        Run health checks on all providers.

        Returns:
            Map of provider_id → health status

        😐 Harold's annual checkup, but for code.
        """
        results: dict[str, ProviderHealth] = {}
        for pid, provider in self._providers.items():
            health = await provider.health_check()
            results[pid] = health
            self._health_cache[pid] = health

            if not health.is_healthy:
                await self.emit(
                    ProviderEvent(
                        event_type=ProviderEventType.ERROR_OCCURRED,
                        provider_id=pid,
                        data={"error": health.error_message or "Unhealthy"},
                    )
                )

        return results

    async def check_health(self, provider_id: str) -> ProviderHealth:
        """Check health of a specific provider."""
        provider = self.get(provider_id)
        health = await provider.health_check()
        self._health_cache[provider_id] = health
        return health

    def get_cached_health(self, provider_id: str) -> ProviderHealth | None:
        """Get last known health status (may be stale)."""
        return self._health_cache.get(provider_id)

    # ========================================================================
    # Summary & Diagnostics
    # ========================================================================

    def summary(self) -> dict[str, Any]:
        """
        Get a summary of the registry state.

        😐 Harold's dashboard of controlled chaos.
        """
        by_type: dict[str, int] = defaultdict(int)
        by_status: dict[str, int] = defaultdict(int)
        capabilities: set[str] = set()

        for p in self._providers.values():
            by_type[p.info.provider_type] += 1
            by_status[p.status] += 1
            capabilities.update(c.value for c in p.info.capabilities)

        return {
            "total_providers": len(self._providers),
            "by_type": dict(by_type),
            "by_status": dict(by_status),
            "capabilities_available": sorted(capabilities),
            "total_subscribers": sum(len(h) for h in self._subscribers.values()),
            "event_log_size": len(self._event_log),
        }

    def get_event_log(
        self,
        event_type: ProviderEventType | None = None,
        limit: int = 100,
    ) -> list[ProviderEvent]:
        """
        Get recent events, optionally filtered by type.

        Args:
            event_type: Filter to specific event type (None = all)
            limit: Maximum events to return

        Returns:
            Most recent events (newest last)
        """
        events = self._event_log
        if event_type is not None:
            events = [e for e in events if e.event_type == event_type]
        return events[-limit:]
