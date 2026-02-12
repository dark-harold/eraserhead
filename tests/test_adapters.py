"""
😐 Tests for platform adapter base class and mock implementations.
Testing the interface that hides platform-specific pain.
"""

from __future__ import annotations

import pytest

from eraserhead.adapters import (
    AdapterStatus,
    RateLimitConfig,
    RateLimiter,
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
# Fixtures
# ============================================================================


@pytest.fixture
def twitter_data() -> SimulatedPlatformData:
    """Pre-populated Twitter data."""
    data = SimulatedPlatformData()
    data.add_resource(ResourceType.POST, "tweet-1", {"text": "Hello world"})
    data.add_resource(ResourceType.POST, "tweet-2", {"text": "Harold smiles"})
    data.add_resource(ResourceType.COMMENT, "reply-1", {"text": "Nice"})
    return data


@pytest.fixture
def twitter_creds() -> PlatformCredentials:
    return PlatformCredentials(
        platform=Platform.TWITTER,
        username="dark_harold",
        auth_token="bearer-test-token",
    )


@pytest.fixture
def make_task():
    """Factory for deletion tasks."""

    def _make(
        platform: Platform = Platform.TWITTER,
        resource_type: ResourceType = ResourceType.POST,
        resource_id: str = "tweet-1",
    ) -> DeletionTask:
        return DeletionTask(
            task_id=f"task-{resource_id}",
            platform=platform,
            resource_type=resource_type,
            resource_id=resource_id,
        )

    return _make


# ============================================================================
# Adapter Lifecycle
# ============================================================================


class TestAdapterLifecycle:
    """😐 Authentication and status management."""

    async def test_starts_disconnected(self, twitter_data) -> None:
        adapter = TwitterAdapter(twitter_data)
        assert adapter.status == AdapterStatus.DISCONNECTED
        assert not adapter.is_authenticated

    async def test_authenticate_success(self, twitter_data, twitter_creds) -> None:
        adapter = TwitterAdapter(twitter_data)
        result = await adapter.authenticate(twitter_creds)
        assert result is True
        assert adapter.is_authenticated
        assert adapter.status == AdapterStatus.AUTHENTICATED

    async def test_authenticate_wrong_platform(self, twitter_data) -> None:
        adapter = TwitterAdapter(twitter_data)
        fb_creds = PlatformCredentials(
            platform=Platform.FACEBOOK,
            username="harold",
            auth_token="token",
        )
        result = await adapter.authenticate(fb_creds)
        assert result is False

    async def test_authenticate_empty_token(self, twitter_data) -> None:
        adapter = TwitterAdapter(twitter_data)
        creds = PlatformCredentials(
            platform=Platform.TWITTER,
            username="harold",
            auth_token="",
        )
        result = await adapter.authenticate(creds)
        assert result is False
        assert adapter.status == AdapterStatus.ERROR

    async def test_disconnect(self, twitter_data, twitter_creds) -> None:
        adapter = TwitterAdapter(twitter_data)
        await adapter.authenticate(twitter_creds)
        await adapter.disconnect()
        assert adapter.status == AdapterStatus.DISCONNECTED


# ============================================================================
# Deletion Operations
# ============================================================================


class TestDeletion:
    """😐 Delete all the things (with permission)."""

    async def test_delete_existing_resource(self, twitter_data, twitter_creds, make_task) -> None:
        adapter = TwitterAdapter(twitter_data)
        await adapter.authenticate(twitter_creds)

        task = make_task(resource_id="tweet-1")
        result = await adapter.delete_resource(task)
        assert result.success is True
        assert result.proof is not None
        assert result.duration_seconds > 0

    async def test_delete_nonexistent_resource(
        self, twitter_data, twitter_creds, make_task
    ) -> None:
        adapter = TwitterAdapter(twitter_data)
        await adapter.authenticate(twitter_creds)

        task = make_task(resource_id="ghost-tweet")
        result = await adapter.delete_resource(task)
        assert result.success is False

    async def test_delete_unauthenticated(self, twitter_data, make_task) -> None:
        adapter = TwitterAdapter(twitter_data)
        task = make_task()
        result = await adapter.delete_resource(task)
        assert result.success is False
        assert "not authenticated" in result.error_message.lower()

    async def test_delete_updates_stats(self, twitter_data, twitter_creds, make_task) -> None:
        adapter = TwitterAdapter(twitter_data)
        await adapter.authenticate(twitter_creds)

        await adapter.delete_resource(make_task(resource_id="tweet-1"))
        await adapter.delete_resource(make_task(resource_id="ghost"))

        assert adapter.stats.total_requests == 2
        assert adapter.stats.successful_deletions == 1
        assert adapter.stats.failed_deletions == 1


# ============================================================================
# Verification
# ============================================================================


class TestVerification:
    """🌑 Trust, but verify. Then verify again."""

    async def test_verify_deleted_resource(self, twitter_data, twitter_creds, make_task) -> None:
        adapter = TwitterAdapter(twitter_data)
        await adapter.authenticate(twitter_creds)

        task = make_task(resource_id="tweet-1")
        await adapter.delete_resource(task)

        status = await adapter.verify_deletion(task)
        assert status == VerificationStatus.CONFIRMED

    async def test_verify_existing_resource(self, twitter_data, twitter_creds, make_task) -> None:
        adapter = TwitterAdapter(twitter_data)
        await adapter.authenticate(twitter_creds)

        task = make_task(resource_id="tweet-1")
        status = await adapter.verify_deletion(task)
        assert status == VerificationStatus.FAILED

    async def test_verify_unauthenticated(self, twitter_data, make_task) -> None:
        adapter = TwitterAdapter(twitter_data)
        status = await adapter.verify_deletion(make_task())
        assert status == VerificationStatus.NOT_VERIFIED


# ============================================================================
# Resource Listing
# ============================================================================


class TestListResources:
    """😐 Cataloguing Harold's digital footprint."""

    async def test_list_resources(self, twitter_data, twitter_creds) -> None:
        adapter = TwitterAdapter(twitter_data)
        await adapter.authenticate(twitter_creds)

        posts = await adapter.list_resources(ResourceType.POST)
        assert len(posts) == 2

    async def test_list_empty_type(self, twitter_data, twitter_creds) -> None:
        adapter = TwitterAdapter(twitter_data)
        await adapter.authenticate(twitter_creds)

        likes = await adapter.list_resources(ResourceType.LIKE)
        assert likes == []

    async def test_list_unauthenticated(self, twitter_data) -> None:
        adapter = TwitterAdapter(twitter_data)
        result = await adapter.list_resources(ResourceType.POST)
        assert result == []


# ============================================================================
# Rate Limiter
# ============================================================================


class TestRateLimiter:
    """😐 Slow down Harold. The API can only take so much."""

    def test_initial_burst(self) -> None:
        limiter = RateLimiter(RateLimitConfig(burst_size=3))
        assert limiter.consume() is True
        assert limiter.consume() is True
        assert limiter.consume() is True
        assert limiter.consume() is False

    def test_time_until_available(self) -> None:
        config = RateLimitConfig(requests_per_minute=60, burst_size=1)
        limiter = RateLimiter(config)
        limiter.consume()
        wait = limiter.time_until_available()
        assert wait > 0
        assert wait <= 2.0  # 1 req/sec, should be ~1s

    def test_can_proceed_check(self) -> None:
        limiter = RateLimiter(RateLimitConfig(burst_size=1))
        assert limiter.can_proceed() is True
        limiter.consume()
        assert limiter.can_proceed() is False


# ============================================================================
# Platform-Specific Adapters
# ============================================================================


class TestPlatformAdapters:
    """😐 Each platform is a unique flavor of API pain."""

    async def test_facebook_supported_types(self) -> None:
        adapter = FacebookAdapter()
        types = adapter.supported_resource_types
        assert ResourceType.POST in types
        assert ResourceType.PHOTO in types
        assert ResourceType.VIDEO in types

    async def test_instagram_supported_types(self) -> None:
        adapter = InstagramAdapter()
        types = adapter.supported_resource_types
        assert ResourceType.POST in types
        assert ResourceType.PHOTO in types
        assert ResourceType.FRIEND not in types

    async def test_twitter_supported_types(self) -> None:
        adapter = TwitterAdapter()
        types = adapter.supported_resource_types
        assert ResourceType.POST in types
        assert ResourceType.FRIEND in types
        assert ResourceType.PHOTO not in types

    async def test_facebook_delete_flow(self) -> None:
        data = SimulatedPlatformData()
        data.add_resource(ResourceType.POST, "fb-post-1")
        adapter = FacebookAdapter(data)

        creds = PlatformCredentials(platform=Platform.FACEBOOK, username="harold", auth_token="tok")
        await adapter.authenticate(creds)

        task = DeletionTask(
            task_id="t1",
            platform=Platform.FACEBOOK,
            resource_type=ResourceType.POST,
            resource_id="fb-post-1",
        )
        result = await adapter.delete_resource(task)
        assert result.success is True

    async def test_instagram_delete_flow(self) -> None:
        data = SimulatedPlatformData()
        data.add_resource(ResourceType.PHOTO, "ig-photo-1")
        adapter = InstagramAdapter(data)

        creds = PlatformCredentials(
            platform=Platform.INSTAGRAM, username="harold", auth_token="tok"
        )
        await adapter.authenticate(creds)

        task = DeletionTask(
            task_id="t1",
            platform=Platform.INSTAGRAM,
            resource_type=ResourceType.PHOTO,
            resource_id="ig-photo-1",
        )
        result = await adapter.delete_resource(task)
        assert result.success is True


# ============================================================================
# Adapter Factory
# ============================================================================


class TestAdapterFactory:
    """😐 Getting the right adapter for the right mess."""

    def test_get_twitter(self) -> None:
        adapter = get_adapter(Platform.TWITTER)
        assert isinstance(adapter, TwitterAdapter)

    def test_get_facebook(self) -> None:
        adapter = get_adapter(Platform.FACEBOOK)
        assert isinstance(adapter, FacebookAdapter)

    def test_get_instagram(self) -> None:
        adapter = get_adapter(Platform.INSTAGRAM)
        assert isinstance(adapter, InstagramAdapter)

    def test_unsupported_platform(self) -> None:
        with pytest.raises(KeyError):
            get_adapter(Platform.LINKEDIN)

    def test_registry_has_three_platforms(self) -> None:
        assert len(ADAPTER_REGISTRY) == 3
