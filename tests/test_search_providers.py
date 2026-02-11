"""
😐 Tests for Search Provider Implementations.

Finding Harold's digital footprint with a confident smile
and internal dread about what we'll discover.

🌑 Dark Harold: Every search result is evidence that privacy
   doesn't exist by default. We test the tools that prove it.
"""

from __future__ import annotations

from typing import Any

import pytest

from eraserhead.providers.base import (
    ProviderCapability,
    ProviderStatus,
    SearchResult,
)
from eraserhead.providers.search.providers import (
    CacheArchiveSearchProvider,
    DataBrokerSearchProvider,
    SearchEngineConfig,
    SearchEngineProvider,
    SocialMediaSearchProvider,
    create_default_search_providers,
)


# ============================================================================
# Search Engine Provider Tests
# ============================================================================


class TestSearchEngineProvider:
    """😐 Testing search engine discovery. Finding what Google knows."""

    @pytest.fixture
    def provider(self) -> SearchEngineProvider:
        return SearchEngineProvider(
            provider_id="test-google",
            engine_name="Google",
        )

    @pytest.fixture
    async def ready_provider(self, provider: SearchEngineProvider) -> SearchEngineProvider:
        await provider.initialize()
        return provider

    async def test_initialization(self, provider: SearchEngineProvider) -> None:
        assert provider.status == ProviderStatus.UNINITIALIZED
        success = await provider.initialize()
        assert success
        assert provider.status == ProviderStatus.READY

    async def test_initialize_with_api_key(self, provider: SearchEngineProvider) -> None:
        success = await provider.initialize({"api_key": "test-key", "search_engine_id": "cx-123"})
        assert success

    async def test_health_check(self, ready_provider: SearchEngineProvider) -> None:
        health = await ready_provider.health_check()
        assert health.is_healthy
        assert health.status == ProviderStatus.READY

    async def test_search_returns_results(self, ready_provider: SearchEngineProvider) -> None:
        ready_provider.set_simulated_results(
            [
                SearchResult(
                    provider_id="test-google",
                    source_url="https://twitter.com/harold",
                    source_platform="twitter",
                    content_type="profile",
                    content_preview="Harold's Twitter profile",
                ),
            ]
        )
        results = await ready_provider.search("harold@example.com", search_type="email")
        assert len(results) == 1
        assert results[0].source_platform == "twitter"
        assert results[0].metadata["search_type"] == "email"
        assert results[0].metadata["engine"] == "Google"

    async def test_search_max_results(self, ready_provider: SearchEngineProvider) -> None:
        ready_provider.set_simulated_results(
            [
                SearchResult(
                    provider_id="test-google",
                    source_url=f"https://example.com/{i}",
                    source_platform="web",
                    content_type="page",
                )
                for i in range(20)
            ]
        )
        results = await ready_provider.search("harold", max_results=5)
        assert len(results) == 5

    async def test_search_increments_count(self, ready_provider: SearchEngineProvider) -> None:
        assert ready_provider.search_count == 0
        await ready_provider.search("test")
        assert ready_provider.search_count == 1
        await ready_provider.search("test2")
        assert ready_provider.search_count == 2

    async def test_search_uninitialized_returns_empty(self, provider: SearchEngineProvider) -> None:
        results = await provider.search("test")
        assert results == []

    def test_capabilities(self, provider: SearchEngineProvider) -> None:
        assert provider.has_capability(ProviderCapability.SEARCH_BY_EMAIL)
        assert provider.has_capability(ProviderCapability.SEARCH_BY_USERNAME)
        assert provider.has_capability(ProviderCapability.SEARCH_BY_REAL_NAME)
        assert provider.has_capability(ProviderCapability.SEARCH_CACHED_CONTENT)
        assert not provider.has_capability(ProviderCapability.SCRUB_GDPR_REQUEST)

    def test_build_query_email(self, provider: SearchEngineProvider) -> None:
        q = provider._build_query("test@example.com", "email")
        assert '"test@example.com"' in q
        assert "email" in q.lower() or "profile" in q.lower()

    def test_build_query_username(self, provider: SearchEngineProvider) -> None:
        q = provider._build_query("dark_harold", "username")
        assert '"dark_harold"' in q
        assert "site:" in q

    def test_build_query_real_name(self, provider: SearchEngineProvider) -> None:
        q = provider._build_query("Harold Smith", "real_name")
        assert '"Harold Smith"' in q

    def test_build_query_general(self, provider: SearchEngineProvider) -> None:
        q = provider._build_query("freeform query", "general")
        assert q == "freeform query"

    def test_build_query_phone(self, provider: SearchEngineProvider) -> None:
        q = provider._build_query("+1-555-0100", "phone")
        assert '"+1-555-0100"' in q

    async def test_search_by_email_convenience(self, ready_provider: SearchEngineProvider) -> None:
        results = await ready_provider.search_by_email("test@example.com")
        assert isinstance(results, list)

    async def test_search_by_username_convenience(
        self, ready_provider: SearchEngineProvider
    ) -> None:
        results = await ready_provider.search_by_username("dark_harold")
        assert isinstance(results, list)


# ============================================================================
# Data Broker Search Provider Tests
# ============================================================================


class TestDataBrokerSearchProvider:
    """😐 Testing data broker discovery. Finding where your data is sold."""

    @pytest.fixture
    def provider(self) -> DataBrokerSearchProvider:
        return DataBrokerSearchProvider()

    @pytest.fixture
    async def ready_provider(self, provider: DataBrokerSearchProvider) -> DataBrokerSearchProvider:
        await provider.initialize()
        return provider

    async def test_initialization(self, provider: DataBrokerSearchProvider) -> None:
        success = await provider.initialize()
        assert success
        assert provider.is_ready

    async def test_health_check(self, ready_provider: DataBrokerSearchProvider) -> None:
        health = await ready_provider.health_check()
        assert health.is_healthy

    async def test_search_returns_simulated(self, ready_provider: DataBrokerSearchProvider) -> None:
        ready_provider.set_simulated_findings(
            [
                SearchResult(
                    provider_id="data-broker-search",
                    source_url="https://spokeo.com/Harold-Smith",
                    source_platform="spokeo",
                    content_type="profile",
                    content_preview="Harold Smith, age 35",
                    removal_difficulty="moderate",
                ),
            ]
        )
        results = await ready_provider.search("Harold Smith", search_type="real_name")
        assert len(results) == 1
        assert results[0].metadata["scan_type"] == "data_broker"

    async def test_search_uninitialized(self, provider: DataBrokerSearchProvider) -> None:
        results = await provider.search("test")
        assert results == []

    async def test_scan_count(self, ready_provider: DataBrokerSearchProvider) -> None:
        assert ready_provider.scan_count == 0
        await ready_provider.search("test")
        assert ready_provider.scan_count == 1

    def test_broker_info(self, provider: DataBrokerSearchProvider) -> None:
        brokers = provider.get_broker_info()
        assert len(brokers) >= 5
        names = [b.name for b in brokers]
        assert "Spokeo" in names
        assert "BeenVerified" in names

    def test_broker_opt_out_urls(self, provider: DataBrokerSearchProvider) -> None:
        brokers = provider.get_broker_info()
        for broker in brokers:
            assert broker.opt_out_url.startswith("https://")
            assert broker.opt_out_difficulty >= 1
            assert broker.opt_out_difficulty <= 5

    def test_capabilities(self, provider: DataBrokerSearchProvider) -> None:
        assert provider.has_capability(ProviderCapability.SEARCH_BY_EMAIL)
        assert provider.has_capability(ProviderCapability.SEARCH_BY_PHONE)
        assert provider.has_capability(ProviderCapability.SEARCH_BY_REAL_NAME)


# ============================================================================
# Social Media Search Provider Tests
# ============================================================================


class TestSocialMediaSearchProvider:
    """😐 Testing social media discovery. Finding all your accounts."""

    @pytest.fixture
    def provider(self) -> SocialMediaSearchProvider:
        return SocialMediaSearchProvider()

    @pytest.fixture
    async def ready_provider(
        self, provider: SocialMediaSearchProvider
    ) -> SocialMediaSearchProvider:
        await provider.initialize()
        return provider

    async def test_initialization(self, provider: SocialMediaSearchProvider) -> None:
        success = await provider.initialize()
        assert success
        assert provider.is_ready

    async def test_search_returns_results(self, ready_provider: SocialMediaSearchProvider) -> None:
        ready_provider.set_simulated_results(
            [
                SearchResult(
                    provider_id="social-media-search",
                    source_url="https://twitter.com/dark_harold",
                    source_platform="twitter",
                    content_type="profile",
                    confidence=0.95,
                ),
                SearchResult(
                    provider_id="social-media-search",
                    source_url="https://github.com/dark-harold",
                    source_platform="github",
                    content_type="profile",
                    confidence=0.9,
                ),
            ]
        )
        results = await ready_provider.search("dark_harold", search_type="username")
        assert len(results) == 2
        platforms = {r.source_platform for r in results}
        assert "twitter" in platforms
        assert "github" in platforms

    async def test_search_with_platform_filter(
        self, ready_provider: SocialMediaSearchProvider
    ) -> None:
        ready_provider.set_simulated_results(
            [
                SearchResult(
                    provider_id="social-media-search",
                    source_url="https://twitter.com/harold",
                    source_platform="twitter",
                    content_type="profile",
                ),
            ]
        )
        results = await ready_provider.search(
            "harold",
            metadata={"platforms": ["twitter", "github"]},
        )
        assert isinstance(results, list)

    async def test_platforms_checked_counter(
        self, ready_provider: SocialMediaSearchProvider
    ) -> None:
        assert ready_provider.platforms_checked == 0
        await ready_provider.search("test")
        # Should check all 9 supported platforms
        assert ready_provider.platforms_checked == 9

    def test_supported_platforms(self, provider: SocialMediaSearchProvider) -> None:
        platforms = provider.SUPPORTED_PLATFORMS
        assert "twitter" in platforms
        assert "github" in platforms
        assert "linkedin" in platforms
        assert len(platforms) >= 9


# ============================================================================
# Cache/Archive Search Provider Tests
# ============================================================================


class TestCacheArchiveSearchProvider:
    """🌑 Testing the discovery of content that should be dead but isn't."""

    @pytest.fixture
    def provider(self) -> CacheArchiveSearchProvider:
        return CacheArchiveSearchProvider()

    @pytest.fixture
    async def ready_provider(
        self, provider: CacheArchiveSearchProvider
    ) -> CacheArchiveSearchProvider:
        await provider.initialize()
        return provider

    async def test_initialization(self, provider: CacheArchiveSearchProvider) -> None:
        success = await provider.initialize()
        assert success

    async def test_search_cached(self, ready_provider: CacheArchiveSearchProvider) -> None:
        ready_provider.set_simulated_results(
            [
                SearchResult(
                    provider_id="cache-archive-search",
                    source_url="https://webcache.googleusercontent.com/search?q=cache:example.com",
                    source_platform="google_cache",
                    content_type="cached_page",
                    removal_difficulty="moderate",
                ),
            ]
        )
        results = await ready_provider.search(
            "https://example.com/harold",
            search_type="cached",
        )
        assert len(results) == 1
        assert results[0].metadata["scan_type"] == "cache_archive"

    async def test_search_with_source_filter(
        self, ready_provider: CacheArchiveSearchProvider
    ) -> None:
        results = await ready_provider.search(
            "test",
            metadata={"sources": ["wayback_machine"]},
        )
        assert isinstance(results, list)

    async def test_checks_counter(self, ready_provider: CacheArchiveSearchProvider) -> None:
        assert ready_provider.checks_performed == 0
        await ready_provider.search("test")
        assert ready_provider.checks_performed == 1

    def test_capabilities(self, provider: CacheArchiveSearchProvider) -> None:
        assert provider.has_capability(ProviderCapability.SEARCH_CACHED_CONTENT)
        assert provider.has_capability(ProviderCapability.SEARCH_ARCHIVED_CONTENT)
        assert not provider.has_capability(ProviderCapability.SEARCH_BY_EMAIL)


# ============================================================================
# Factory Tests
# ============================================================================


class TestCreateDefaultProviders:
    """😐 Testing the provider factory."""

    def test_creates_all_providers(self) -> None:
        providers = create_default_search_providers()
        assert len(providers) == 5

    def test_provider_types(self) -> None:
        providers = create_default_search_providers()
        provider_ids = {p.provider_id for p in providers}
        assert "google-search" in provider_ids
        assert "bing-search" in provider_ids
        assert "data-broker-search" in provider_ids
        assert "social-media-search" in provider_ids
        assert "cache-archive-search" in provider_ids

    def test_all_are_search_providers(self) -> None:
        from eraserhead.providers.base import SearchProvider

        providers = create_default_search_providers()
        for p in providers:
            assert isinstance(p, SearchProvider)

    async def test_all_can_initialize(self) -> None:
        providers = create_default_search_providers()
        for p in providers:
            success = await p.initialize()
            assert success, f"Failed to initialize {p.provider_id}"


# ============================================================================
# Integration with Registry
# ============================================================================


class TestSearchProviderRegistryIntegration:
    """😐 Testing search providers registered in the provider registry."""

    async def test_register_all_search_providers(self) -> None:
        from eraserhead.providers.registry import ProviderRegistry

        registry = ProviderRegistry()
        providers = create_default_search_providers()

        for p in providers:
            await p.initialize()
            registry.register(p)

        assert registry.provider_count == 5

        # Query by capability
        email_providers = registry.get_by_capability(ProviderCapability.SEARCH_BY_EMAIL)
        assert len(email_providers) >= 3  # Google, Bing, DataBroker, Social

        # Get search providers
        search_providers = registry.get_search_providers()
        assert len(search_providers) == 5

    async def test_registry_summary_with_search_providers(self) -> None:
        from eraserhead.providers.registry import ProviderRegistry

        registry = ProviderRegistry()
        for p in create_default_search_providers():
            await p.initialize()
            registry.register(p)

        summary = registry.summary()
        assert summary["total_providers"] == 5
        assert summary["by_type"]["search"] == 5
        assert len(summary["capabilities_available"]) >= 4
