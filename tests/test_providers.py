"""
😐 Tests for Provider Base Classes and Registry

Testing the modular provider/subscriber architecture.
Every provider, every event, every capability — verified.

🌑 harold-tester: Breaking the provider system with a smile.
"""

from __future__ import annotations

from typing import Any

import pytest

from eraserhead.providers.base import (
    ComplianceCheckResult,
    ComplianceProvider,
    ProviderCapability,
    ProviderHealth,
    ProviderInfo,
    ProviderStatus,
    ProviderType,
    ScrubProvider,
    ScrubRequest,
    ScrubResult,
    SearchProvider,
    SearchResult,
)
from eraserhead.providers.registry import (
    ProviderAlreadyRegisteredError,
    ProviderEvent,
    ProviderEventType,
    ProviderNotFoundError,
    ProviderRegistry,
)


# ============================================================================
# Test Provider Implementations (Mocks)
# ============================================================================


class MockSearchProvider(SearchProvider):
    """😐 A search provider that finds things Harold wishes didn't exist."""

    def __init__(self, provider_id: str = "mock-search") -> None:
        super().__init__(
            info=ProviderInfo(
                provider_id=provider_id,
                name="Mock Search",
                provider_type=ProviderType.SEARCH,
                capabilities={
                    ProviderCapability.SEARCH_BY_EMAIL,
                    ProviderCapability.SEARCH_BY_USERNAME,
                },
            )
        )
        self._search_results: list[SearchResult] = []

    def set_results(self, results: list[SearchResult]) -> None:
        self._search_results = results

    async def _do_initialize(self, config: dict[str, Any]) -> bool:
        return True

    async def _do_health_check(self) -> ProviderHealth:
        return ProviderHealth(is_healthy=True, status=ProviderStatus.READY)

    async def search(
        self,
        query: str,
        *,
        search_type: str = "general",
        max_results: int = 50,
        metadata: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        return self._search_results[:max_results]


class MockScrubProvider(ScrubProvider):
    """😐 A scrub provider that pretends to delete things."""

    def __init__(self, provider_id: str = "mock-scrub") -> None:
        super().__init__(
            info=ProviderInfo(
                provider_id=provider_id,
                name="Mock Scrub",
                provider_type=ProviderType.SCRUB,
                capabilities={
                    ProviderCapability.SCRUB_GDPR_REQUEST,
                    ProviderCapability.SCRUB_DIRECT_API,
                },
            )
        )
        self._removal_results: dict[str, ScrubResult] = {}

    def set_result(self, request_id: str, result: ScrubResult) -> None:
        self._removal_results[request_id] = result

    async def _do_initialize(self, config: dict[str, Any]) -> bool:
        return True

    async def _do_health_check(self) -> ProviderHealth:
        return ProviderHealth(is_healthy=True, status=ProviderStatus.READY)

    async def submit_removal(self, request: ScrubRequest) -> ScrubResult:
        if request.request_id in self._removal_results:
            return self._removal_results[request.request_id]
        return ScrubResult(
            request_id=request.request_id,
            success=True,
            method_used="mock_api",
        )

    async def check_removal_status(self, request_id: str) -> ScrubResult:
        return self._removal_results.get(
            request_id,
            ScrubResult(request_id=request_id, success=False, error_message="Not found"),
        )

    async def get_supported_methods(self) -> list[str]:
        return ["api", "gdpr_request"]


class MockComplianceProvider(ComplianceProvider):
    """😐 A compliance provider that mostly says yes."""

    def __init__(
        self,
        provider_id: str = "mock-compliance",
        always_compliant: bool = True,
    ) -> None:
        super().__init__(
            info=ProviderInfo(
                provider_id=provider_id,
                name="Mock Compliance",
                provider_type=ProviderType.COMPLIANCE,
                capabilities={
                    ProviderCapability.COMPLIANCE_GDPR,
                    ProviderCapability.COMPLIANCE_CCPA,
                },
            )
        )
        self._always_compliant = always_compliant

    async def _do_initialize(self, config: dict[str, Any]) -> bool:
        return True

    async def _do_health_check(self) -> ProviderHealth:
        return ProviderHealth(is_healthy=True, status=ProviderStatus.READY)

    async def validate_action(
        self,
        action_type: str,
        target: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> ComplianceCheckResult:
        if self._always_compliant:
            return ComplianceCheckResult(
                provider_id=self.provider_id,
                is_compliant=True,
                framework="GDPR, CCPA",
            )
        return ComplianceCheckResult(
            provider_id=self.provider_id,
            is_compliant=False,
            framework="GDPR",
            issues=["Identity proof missing", "Consent not documented"],
        )

    async def get_applicable_frameworks(self, target: dict[str, Any]) -> list[str]:
        return ["GDPR", "CCPA"]

    async def generate_request_template(self, framework: str, request_type: str) -> dict[str, Any]:
        return {"framework": framework, "type": request_type}


# ============================================================================
# Provider Base Tests
# ============================================================================


class TestBaseProvider:
    """😐 Testing the provider lifecycle — init, health, teardown."""

    @pytest.fixture
    def search_provider(self):
        return MockSearchProvider()

    @pytest.fixture
    def scrub_provider(self):
        return MockScrubProvider()

    def test_provider_starts_uninitialized(self, search_provider):
        assert search_provider.status == ProviderStatus.UNINITIALIZED
        assert not search_provider.is_ready

    @pytest.mark.anyio
    async def test_provider_initialize(self, search_provider):
        success = await search_provider.initialize()
        assert success
        assert search_provider.status == ProviderStatus.READY
        assert search_provider.is_ready

    @pytest.mark.anyio
    async def test_provider_health_check(self, search_provider):
        await search_provider.initialize()
        health = await search_provider.health_check()
        assert health.is_healthy
        assert health.status == ProviderStatus.READY

    @pytest.mark.anyio
    async def test_provider_teardown(self, search_provider):
        await search_provider.initialize()
        await search_provider.teardown()
        assert search_provider.status == ProviderStatus.DISABLED

    def test_provider_info(self, search_provider):
        assert search_provider.provider_id == "mock-search"
        assert search_provider.info.name == "Mock Search"
        assert search_provider.info.provider_type == ProviderType.SEARCH

    def test_provider_capabilities(self, search_provider):
        assert search_provider.has_capability(ProviderCapability.SEARCH_BY_EMAIL)
        assert search_provider.has_capability(ProviderCapability.SEARCH_BY_USERNAME)
        assert not search_provider.has_capability(ProviderCapability.SCRUB_GDPR_REQUEST)


class TestSearchProvider:
    """😐 Testing search providers — finding Harold's digital footprints."""

    @pytest.fixture
    def provider(self):
        return MockSearchProvider()

    @pytest.mark.anyio
    async def test_search_returns_results(self, provider):
        await provider.initialize()
        provider.set_results(
            [
                SearchResult(
                    provider_id="mock-search",
                    source_url="https://twitter.com/harold",
                    source_platform="twitter",
                    content_type="profile",
                    content_preview="Harold's account",
                ),
            ]
        )
        results = await provider.search("harold@example.com")
        assert len(results) == 1
        assert results[0].source_platform == "twitter"

    @pytest.mark.anyio
    async def test_search_by_email_checks_capability(self, provider):
        await provider.initialize()
        # Has SEARCH_BY_EMAIL capability, should attempt search
        results = await provider.search_by_email("test@example.com")
        assert isinstance(results, list)

    @pytest.mark.anyio
    async def test_search_by_email_no_capability(self):
        """Provider without SEARCH_BY_EMAIL returns empty."""
        provider = MockSearchProvider(provider_id="limited")
        provider._info.capabilities = set()  # No capabilities
        await provider.initialize()
        results = await provider.search_by_email("test@example.com")
        assert results == []

    @pytest.mark.anyio
    async def test_search_max_results(self, provider):
        await provider.initialize()
        provider.set_results(
            [
                SearchResult(
                    provider_id="mock-search",
                    source_url=f"https://example.com/{i}",
                    source_platform="web",
                    content_type="page",
                )
                for i in range(10)
            ]
        )
        results = await provider.search("harold", max_results=3)
        assert len(results) == 3


# ============================================================================
# Registry Tests
# ============================================================================


class TestProviderRegistry:
    """😐 Testing the provider registry — Harold's phone book of tools."""

    @pytest.fixture
    def registry(self):
        return ProviderRegistry()

    @pytest.fixture
    def search_provider(self):
        return MockSearchProvider()

    @pytest.fixture
    def scrub_provider(self):
        return MockScrubProvider()

    @pytest.fixture
    def compliance_provider(self):
        return MockComplianceProvider()

    def test_register_provider(self, registry, search_provider):
        registry.register(search_provider)
        assert registry.provider_count == 1
        assert registry.get(search_provider.provider_id) is search_provider

    def test_register_duplicate_raises(self, registry, search_provider):
        registry.register(search_provider)
        with pytest.raises(ProviderAlreadyRegisteredError):
            registry.register(search_provider)

    def test_unregister_provider(self, registry, search_provider):
        registry.register(search_provider)
        removed = registry.unregister(search_provider.provider_id)
        assert removed is search_provider
        assert registry.provider_count == 0

    def test_unregister_missing_raises(self, registry):
        with pytest.raises(ProviderNotFoundError):
            registry.unregister("nonexistent")

    def test_get_missing_raises(self, registry):
        with pytest.raises(ProviderNotFoundError):
            registry.get("nonexistent")

    def test_get_by_type(self, registry, search_provider, scrub_provider):
        registry.register(search_provider)
        registry.register(scrub_provider)

        searchers = registry.get_by_type(ProviderType.SEARCH)
        assert len(searchers) == 1
        assert searchers[0].provider_id == "mock-search"

        scrubbers = registry.get_by_type(ProviderType.SCRUB)
        assert len(scrubbers) == 1

    def test_get_search_providers(self, registry, search_provider, scrub_provider):
        registry.register(search_provider)
        registry.register(scrub_provider)

        searchers = registry.get_search_providers()
        assert len(searchers) == 1
        assert all(isinstance(p, SearchProvider) for p in searchers)

    def test_get_by_capability(self, registry, search_provider, scrub_provider):
        registry.register(search_provider)
        registry.register(scrub_provider)

        email_searchers = registry.get_by_capability(
            ProviderCapability.SEARCH_BY_EMAIL,
            ready_only=False,
        )
        assert len(email_searchers) == 1

        gdpr_scrubbers = registry.get_by_capability(
            ProviderCapability.SCRUB_GDPR_REQUEST,
            ready_only=False,
        )
        assert len(gdpr_scrubbers) == 1

    def test_get_by_capability_ready_only(self, registry, search_provider):
        registry.register(search_provider)
        # Provider is UNINITIALIZED, so ready_only should filter it out
        results = registry.get_by_capability(
            ProviderCapability.SEARCH_BY_EMAIL,
            ready_only=True,
        )
        assert len(results) == 0

    def test_priority_ordering(self, registry):
        p1 = MockSearchProvider("search-1")
        p2 = MockSearchProvider("search-2")
        registry.register(p1, priority=50)
        registry.register(p2, priority=10)

        searchers = registry.get_by_type(ProviderType.SEARCH)
        assert searchers[0].provider_id == "search-2"  # Lower priority = first
        assert searchers[1].provider_id == "search-1"

    def test_summary(self, registry, search_provider, scrub_provider, compliance_provider):
        registry.register(search_provider)
        registry.register(scrub_provider)
        registry.register(compliance_provider)

        summary = registry.summary()
        assert summary["total_providers"] == 3
        assert summary["by_type"]["search"] == 1
        assert summary["by_type"]["scrub"] == 1
        assert summary["by_type"]["compliance"] == 1


class TestProviderRegistryEvents:
    """😐 Testing the pub/sub event system."""

    @pytest.fixture
    def registry(self):
        return ProviderRegistry()

    def test_subscribe_receives_events(self, registry):
        received_events: list[ProviderEvent] = []

        def handler(event: ProviderEvent):
            received_events.append(event)

        registry.subscribe(ProviderEventType.PROVIDER_REGISTERED, handler)
        registry.register(MockSearchProvider())

        assert len(received_events) == 1
        assert received_events[0].event_type == ProviderEventType.PROVIDER_REGISTERED

    def test_unsubscribe(self, registry):
        received: list[ProviderEvent] = []

        def handler(event: ProviderEvent):
            received.append(event)

        registry.subscribe(ProviderEventType.PROVIDER_REGISTERED, handler)
        assert registry.unsubscribe(ProviderEventType.PROVIDER_REGISTERED, handler)

        registry.register(MockSearchProvider())
        assert len(received) == 0  # Handler was removed

    def test_subscribe_all(self, registry):
        received: list[ProviderEvent] = []

        def handler(event: ProviderEvent):
            received.append(event)

        registry.subscribe_all(handler)
        registry.register(MockSearchProvider())
        registry.unregister("mock-search")

        assert len(received) == 2  # Registered + unregistered

    def test_event_log(self, registry):
        registry.register(MockSearchProvider())
        events = registry.get_event_log()
        assert len(events) >= 1
        assert events[-1].event_type == ProviderEventType.PROVIDER_REGISTERED

    @pytest.mark.anyio
    async def test_async_event_emission(self, registry):
        received: list[ProviderEvent] = []

        async def async_handler(event: ProviderEvent):
            received.append(event)

        registry.subscribe(ProviderEventType.SEARCH_COMPLETED, async_handler)

        await registry.emit(
            ProviderEvent(
                event_type=ProviderEventType.SEARCH_COMPLETED,
                provider_id="test",
                data={"results": 5},
            )
        )

        assert len(received) == 1

    @pytest.mark.anyio
    async def test_health_check_all(self, registry):
        p1 = MockSearchProvider("s1")
        p2 = MockSearchProvider("s2")
        await p1.initialize()
        await p2.initialize()
        registry.register(p1)
        registry.register(p2)

        health = await registry.check_all_health()
        assert len(health) == 2
        assert all(h.is_healthy for h in health.values())
