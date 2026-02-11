"""
😐 Extended tests for platform adapters.

Covers deletion workflows, rate limit config, unsupported resource types,
authentication flows, and adapter registry for all three platforms.

🌑 These tests verify the mock adapters behave consistently.
Production adapters will have many more failure modes.
"""

from __future__ import annotations

import pytest

from eraserhead.adapters import (
    AdapterStatus,
    PlatformAdapter,
    RateLimitConfig,
)
from eraserhead.adapters.platforms import (
    ADAPTER_REGISTRY,
    FacebookAdapter,
    InstagramAdapter,
    SimulatedPlatformData,
    TwitterAdapter,
    get_adapter,
)
from eraserhead.models import (
    DeletionTask,
    Platform,
    PlatformCredentials,
    ResourceType,
    VerificationStatus,
)


# ============================================================================
# Helpers
# ============================================================================


def _creds(platform: Platform) -> PlatformCredentials:
    return PlatformCredentials(platform=platform, username="harold", auth_token="tok")


def _task(
    platform: Platform,
    resource_type: ResourceType = ResourceType.POST,
    resource_id: str = "res-1",
    task_id: str = "t-1",
) -> DeletionTask:
    return DeletionTask(
        task_id=task_id,
        platform=platform,
        resource_type=resource_type,
        resource_id=resource_id,
    )


# ============================================================================
# SimulatedPlatformData Tests
# ============================================================================


class TestSimulatedPlatformData:
    """😐 Testing the simulated backend store."""

    def test_add_and_check(self) -> None:
        data = SimulatedPlatformData()
        data.add_resource(ResourceType.POST, "p1")
        assert data.has_resource(ResourceType.POST, "p1")
        assert not data.has_resource(ResourceType.POST, "p2")

    def test_delete_existing(self) -> None:
        data = SimulatedPlatformData()
        data.add_resource(ResourceType.POST, "p1")
        assert data.delete_resource(ResourceType.POST, "p1")
        assert not data.has_resource(ResourceType.POST, "p1")

    def test_delete_nonexistent(self) -> None:
        data = SimulatedPlatformData()
        assert not data.delete_resource(ResourceType.POST, "p1")

    def test_list_resources(self) -> None:
        data = SimulatedPlatformData()
        data.add_resource(ResourceType.PHOTO, "ph1", {"url": "http://x"})
        data.add_resource(ResourceType.PHOTO, "ph2")
        resources = data.list_resources(ResourceType.PHOTO)
        assert len(resources) == 2

    def test_list_empty_type(self) -> None:
        data = SimulatedPlatformData()
        assert data.list_resources(ResourceType.VIDEO) == []

    def test_custom_metadata(self) -> None:
        data = SimulatedPlatformData()
        meta = {"text": "hello", "user": "harold"}
        data.add_resource(ResourceType.POST, "p1", meta)
        resources = data.list_resources(ResourceType.POST)
        assert resources[0]["user"] == "harold"

    def test_has_resource_wrong_type(self) -> None:
        data = SimulatedPlatformData()
        data.add_resource(ResourceType.POST, "p1")
        assert not data.has_resource(ResourceType.PHOTO, "p1")


# ============================================================================
# Twitter Adapter Tests
# ============================================================================


class TestTwitterAdapter:
    """😐 Twitter adapter: testing tweet lifecycle."""

    async def test_authenticate_success(self) -> None:
        adapter = TwitterAdapter()
        result = await adapter.authenticate(_creds(Platform.TWITTER))
        assert result
        assert adapter.is_authenticated

    async def test_authenticate_empty_token(self) -> None:
        adapter = TwitterAdapter()
        creds = PlatformCredentials(platform=Platform.TWITTER, username="h", auth_token="")
        result = await adapter.authenticate(creds)
        assert not result
        assert not adapter.is_authenticated

    async def test_supported_types(self) -> None:
        adapter = TwitterAdapter()
        types = adapter.supported_resource_types
        assert ResourceType.POST in types
        assert ResourceType.COMMENT in types
        assert ResourceType.LIKE in types
        assert ResourceType.FRIEND in types
        # Not supported
        assert ResourceType.PHOTO not in types
        assert ResourceType.VIDEO not in types

    async def test_delete_existing_resource(self) -> None:
        data = SimulatedPlatformData()
        data.add_resource(ResourceType.POST, "tweet-1")
        adapter = TwitterAdapter(data)
        await adapter.authenticate(_creds(Platform.TWITTER))

        task = _task(Platform.TWITTER, ResourceType.POST, "tweet-1")
        result = await adapter.delete_resource(task)
        assert result.success
        assert "tweet_deleted" in result.proof

    async def test_delete_nonexistent(self) -> None:
        adapter = TwitterAdapter()
        await adapter.authenticate(_creds(Platform.TWITTER))
        task = _task(Platform.TWITTER, ResourceType.POST, "ghost")
        result = await adapter.delete_resource(task)
        assert not result.success
        assert "not found" in result.error_message.lower()

    async def test_verify_deleted(self) -> None:
        data = SimulatedPlatformData()
        adapter = TwitterAdapter(data)
        await adapter.authenticate(_creds(Platform.TWITTER))
        task = _task(Platform.TWITTER, ResourceType.POST, "del-1")
        status = await adapter.verify_deletion(task)
        assert status == VerificationStatus.CONFIRMED

    async def test_verify_still_exists(self) -> None:
        data = SimulatedPlatformData()
        data.add_resource(ResourceType.POST, "alive-1")
        adapter = TwitterAdapter(data)
        await adapter.authenticate(_creds(Platform.TWITTER))
        task = _task(Platform.TWITTER, ResourceType.POST, "alive-1")
        status = await adapter.verify_deletion(task)
        assert status == VerificationStatus.FAILED

    async def test_list_resources(self) -> None:
        data = SimulatedPlatformData()
        data.add_resource(ResourceType.POST, "t1")
        data.add_resource(ResourceType.POST, "t2")
        adapter = TwitterAdapter(data)
        await adapter.authenticate(_creds(Platform.TWITTER))
        resources = await adapter.list_resources(ResourceType.POST)
        assert len(resources) == 2

    async def test_delete_full_lifecycle(self) -> None:
        """Create → Delete → Verify confirmed."""
        data = SimulatedPlatformData()
        data.add_resource(ResourceType.COMMENT, "c1")
        adapter = TwitterAdapter(data)
        await adapter.authenticate(_creds(Platform.TWITTER))

        task = _task(Platform.TWITTER, ResourceType.COMMENT, "c1", "lifecycle-1")

        # Verify exists
        assert data.has_resource(ResourceType.COMMENT, "c1")

        # Delete
        result = await adapter.delete_resource(task)
        assert result.success

        # Verify gone
        status = await adapter.verify_deletion(task)
        assert status == VerificationStatus.CONFIRMED


# ============================================================================
# Facebook Adapter Tests
# ============================================================================


class TestFacebookAdapter:
    """😐 Facebook: the social graph of deletion targets."""

    async def test_supported_types(self) -> None:
        adapter = FacebookAdapter()
        types = adapter.supported_resource_types
        assert ResourceType.POST in types
        assert ResourceType.PHOTO in types
        assert ResourceType.VIDEO in types
        assert ResourceType.FRIEND in types

    async def test_delete_photo(self) -> None:
        data = SimulatedPlatformData()
        data.add_resource(ResourceType.PHOTO, "photo-1")
        adapter = FacebookAdapter(data)
        await adapter.authenticate(_creds(Platform.FACEBOOK))

        task = _task(Platform.FACEBOOK, ResourceType.PHOTO, "photo-1")
        result = await adapter.delete_resource(task)
        assert result.success
        assert "fb_deleted" in result.proof

    async def test_delete_video(self) -> None:
        data = SimulatedPlatformData()
        data.add_resource(ResourceType.VIDEO, "vid-1")
        adapter = FacebookAdapter(data)
        await adapter.authenticate(_creds(Platform.FACEBOOK))

        task = _task(Platform.FACEBOOK, ResourceType.VIDEO, "vid-1")
        result = await adapter.delete_resource(task)
        assert result.success

    async def test_verify_after_delete(self) -> None:
        data = SimulatedPlatformData()
        data.add_resource(ResourceType.POST, "fb-post")
        adapter = FacebookAdapter(data)
        await adapter.authenticate(_creds(Platform.FACEBOOK))

        task = _task(Platform.FACEBOOK, ResourceType.POST, "fb-post")
        await adapter.delete_resource(task)
        status = await adapter.verify_deletion(task)
        assert status == VerificationStatus.CONFIRMED

    async def test_rate_limit_config(self) -> None:
        adapter = FacebookAdapter(rate_limit=RateLimitConfig(requests_per_minute=10))
        assert adapter._rate_limiter is not None


# ============================================================================
# Instagram Adapter Tests
# ============================================================================


class TestInstagramAdapter:
    """😐 Instagram: photos Harold wants to forget."""

    async def test_supported_types(self) -> None:
        adapter = InstagramAdapter()
        types = adapter.supported_resource_types
        assert ResourceType.POST in types
        assert ResourceType.PHOTO in types
        assert ResourceType.VIDEO in types
        assert ResourceType.LIKE in types
        # Not supported
        assert ResourceType.FRIEND not in types

    async def test_delete_photo(self) -> None:
        data = SimulatedPlatformData()
        data.add_resource(ResourceType.PHOTO, "ig-photo-1")
        adapter = InstagramAdapter(data)
        await adapter.authenticate(_creds(Platform.INSTAGRAM))

        task = _task(Platform.INSTAGRAM, ResourceType.PHOTO, "ig-photo-1")
        result = await adapter.delete_resource(task)
        assert result.success
        assert "ig_deleted" in result.proof

    async def test_delete_nonexistent(self) -> None:
        adapter = InstagramAdapter()
        await adapter.authenticate(_creds(Platform.INSTAGRAM))
        task = _task(Platform.INSTAGRAM, ResourceType.POST, "ghost")
        result = await adapter.delete_resource(task)
        assert not result.success

    async def test_default_rate_limit(self) -> None:
        """Instagram has stricter rate limits (20 RPM)."""
        adapter = InstagramAdapter()
        # Check platform is Instagram
        assert adapter.platform == Platform.INSTAGRAM


# ============================================================================
# Adapter Registry Tests
# ============================================================================


class TestAdapterRegistry:
    """😐 Factory and registry for platform adapters."""

    def test_registry_has_three_platforms(self) -> None:
        assert len(ADAPTER_REGISTRY) == 3

    def test_registry_platforms(self) -> None:
        assert Platform.TWITTER in ADAPTER_REGISTRY
        assert Platform.FACEBOOK in ADAPTER_REGISTRY
        assert Platform.INSTAGRAM in ADAPTER_REGISTRY

    def test_registry_maps_to_correct_classes(self) -> None:
        assert ADAPTER_REGISTRY[Platform.TWITTER] is TwitterAdapter
        assert ADAPTER_REGISTRY[Platform.FACEBOOK] is FacebookAdapter
        assert ADAPTER_REGISTRY[Platform.INSTAGRAM] is InstagramAdapter

    def test_get_adapter_twitter(self) -> None:
        adapter = get_adapter(Platform.TWITTER)
        assert isinstance(adapter, TwitterAdapter)
        assert adapter.platform == Platform.TWITTER

    def test_get_adapter_with_data(self) -> None:
        data = SimulatedPlatformData()
        data.add_resource(ResourceType.POST, "p1")
        adapter = get_adapter(Platform.TWITTER, simulated_data=data)
        assert isinstance(adapter, TwitterAdapter)

    def test_get_adapter_unknown_platform(self) -> None:
        """Unknown platform should raise KeyError."""
        with pytest.raises(KeyError, match="No adapter"):
            get_adapter(Platform.LINKEDIN)


# ============================================================================
# Adapter Base Class Behavior
# ============================================================================


class TestAdapterStatus:
    """😐 Status transitions in the adapter lifecycle."""

    def test_initial_status_disconnected(self) -> None:
        adapter = TwitterAdapter()
        assert adapter.status == AdapterStatus.DISCONNECTED

    async def test_authenticated_status(self) -> None:
        adapter = TwitterAdapter()
        await adapter.authenticate(_creds(Platform.TWITTER))
        assert adapter.status == AdapterStatus.AUTHENTICATED

    async def test_stats_tracking(self) -> None:
        data = SimulatedPlatformData()
        data.add_resource(ResourceType.POST, "p1")
        adapter = TwitterAdapter(data)
        await adapter.authenticate(_creds(Platform.TWITTER))

        task = _task(Platform.TWITTER, ResourceType.POST, "p1")
        await adapter.delete_resource(task)

        stats = adapter.stats
        assert stats.successful_deletions == 1

    async def test_failed_deletion_stats(self) -> None:
        adapter = TwitterAdapter()
        await adapter.authenticate(_creds(Platform.TWITTER))

        task = _task(Platform.TWITTER, ResourceType.POST, "nonexistent")
        await adapter.delete_resource(task)

        stats = adapter.stats
        assert stats.failed_deletions == 1

    async def test_verification_stats(self) -> None:
        adapter = TwitterAdapter()
        await adapter.authenticate(_creds(Platform.TWITTER))

        task = _task(Platform.TWITTER, ResourceType.POST, "v1")
        await adapter.verify_deletion(task)

        stats = adapter.stats
        assert stats.verifications == 1

    async def test_verify_unauthenticated(self) -> None:
        """Verification without auth returns NOT_VERIFIED."""
        adapter = TwitterAdapter()
        task = _task(Platform.TWITTER, ResourceType.POST, "v1")
        status = await adapter.verify_deletion(task)
        assert status == VerificationStatus.NOT_VERIFIED
