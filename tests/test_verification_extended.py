"""
😐 Extended tests for verification service.

Testing REAPPEARED status paths, multi-adapter verification,
concurrent scan behavior, and timing-sensitive checks.

🌑 Verification is Harold's last defense against phantom deletions.
"""

from __future__ import annotations

import pytest

from eraserhead.adapters import PlatformAdapter, RateLimitConfig
from eraserhead.adapters.platforms import (
    FacebookAdapter,
    InstagramAdapter,
    SimulatedPlatformData,
    TwitterAdapter,
)
from eraserhead.models import (
    DeletionTask,
    Platform,
    PlatformCredentials,
    ResourceType,
    TaskStatus,
    VerificationStatus,
)
from eraserhead.verification import VerificationResult, VerificationService


# ============================================================================
# Helpers
# ============================================================================


class ReappearingAdapter(PlatformAdapter):
    """
    😐 Adapter that simulates content reappearing after deletion.

    🌑 This happens in the real world: CDN caches, database replicas,
    or platforms silently undoing deletions.
    """

    def __init__(self) -> None:
        super().__init__(
            platform=Platform.TWITTER,
            rate_limit=RateLimitConfig(requests_per_minute=60),
        )
        self._verify_count = 0

    @property
    def is_authenticated(self) -> bool:
        return True

    def _get_supported_types(self) -> set[ResourceType]:
        return {ResourceType.POST}

    async def _do_authenticate(self, credentials: PlatformCredentials) -> bool:
        return True

    async def _do_delete(self, task: DeletionTask):
        pass

    async def _do_verify(self, task: DeletionTask) -> VerificationStatus:
        self._verify_count += 1
        # First verification: confirmed. Second: reappeared!
        if self._verify_count <= 1:
            return VerificationStatus.CONFIRMED
        return VerificationStatus.REAPPEARED

    async def _do_list_resources(self, resource_type):
        return []


def _make_task(
    task_id: str = "task-1",
    resource_id: str = "res-1",
    platform: Platform = Platform.TWITTER,
    status: TaskStatus = TaskStatus.COMPLETED,
) -> DeletionTask:
    task = DeletionTask(
        task_id=task_id,
        platform=platform,
        resource_type=ResourceType.POST,
        resource_id=resource_id,
    )
    task.status = status
    return task


# ============================================================================
# REAPPEARED Status Tests
# ============================================================================


class TestVerificationReappeared:
    """🌑 Content that comes back from the dead."""

    async def test_reappeared_status_tracked(self) -> None:
        """REAPPEARED status should be recorded in history."""
        adapter = ReappearingAdapter()
        service = VerificationService()
        service.register_adapter(adapter)

        task = _make_task()

        # First verify: CONFIRMED
        result1 = await service.verify(task)
        assert result1.status == VerificationStatus.CONFIRMED

        # Second verify: REAPPEARED (simulating content coming back)
        task.status = TaskStatus.COMPLETED  # Reset for re-verification
        result2 = await service.verify(task)
        assert result2.status == VerificationStatus.REAPPEARED

    async def test_reappeared_in_stats(self) -> None:
        """Stats should track REAPPEARED count."""
        adapter = ReappearingAdapter()
        service = VerificationService()
        service.register_adapter(adapter)

        task = _make_task()
        await service.verify(task)  # CONFIRMED
        task.status = TaskStatus.COMPLETED
        await service.verify(task)  # REAPPEARED

        stats = service.get_stats()
        assert stats["reappeared"] == 1
        assert stats["confirmed"] == 1
        assert stats["total"] == 2


# ============================================================================
# Multi-Adapter Verification
# ============================================================================


class TestMultiAdapterVerification:
    """😐 Verification across multiple platforms simultaneously."""

    async def test_verify_different_platforms(self) -> None:
        """Should use correct adapter for each platform."""
        twitter_data = SimulatedPlatformData()
        fb_data = SimulatedPlatformData()
        fb_data.add_resource(ResourceType.POST, "fb-post-1")

        twitter = TwitterAdapter(twitter_data)
        facebook = FacebookAdapter(fb_data)
        await twitter.authenticate(
            PlatformCredentials(platform=Platform.TWITTER, username="h", auth_token="tok")
        )
        await facebook.authenticate(
            PlatformCredentials(platform=Platform.FACEBOOK, username="h", auth_token="tok")
        )

        service = VerificationService()
        service.register_adapter(twitter)
        service.register_adapter(facebook)

        # Twitter task: resource doesn't exist → CONFIRMED
        twitter_task = _make_task(
            task_id="tw-1", resource_id="deleted-tweet", platform=Platform.TWITTER
        )
        result_tw = await service.verify(twitter_task)
        assert result_tw.status == VerificationStatus.CONFIRMED

        # Facebook task: resource exists → FAILED
        fb_task = _make_task(task_id="fb-1", resource_id="fb-post-1", platform=Platform.FACEBOOK)
        result_fb = await service.verify(fb_task)
        assert result_fb.status == VerificationStatus.FAILED

    async def test_scan_across_platforms(self) -> None:
        """Batch scan should handle tasks for different platforms."""
        twitter_data = SimulatedPlatformData()
        ig_data = SimulatedPlatformData()
        ig_data.add_resource(ResourceType.PHOTO, "ig-photo-1")

        twitter = TwitterAdapter(twitter_data)
        instagram = InstagramAdapter(ig_data)
        await twitter.authenticate(
            PlatformCredentials(platform=Platform.TWITTER, username="h", auth_token="t")
        )
        await instagram.authenticate(
            PlatformCredentials(platform=Platform.INSTAGRAM, username="h", auth_token="t")
        )

        service = VerificationService()
        service.register_adapter(twitter)
        service.register_adapter(instagram)

        tasks = [
            _make_task("tw-del", "deleted", Platform.TWITTER),
            _make_task("ig-exists", "ig-photo-1", Platform.INSTAGRAM),
        ]
        # Fix resource type for Instagram
        tasks[1] = DeletionTask(
            task_id="ig-exists",
            platform=Platform.INSTAGRAM,
            resource_type=ResourceType.PHOTO,
            resource_id="ig-photo-1",
        )
        tasks[1].status = TaskStatus.COMPLETED

        results = await service.scan(tasks)
        assert len(results) == 2
        statuses = {r.task_id: r.status for r in results}
        assert statuses["tw-del"] == VerificationStatus.CONFIRMED
        assert statuses["ig-exists"] == VerificationStatus.FAILED


# ============================================================================
# Verification Service Configuration
# ============================================================================


class TestVerificationConfig:
    """😐 Testing service configuration options."""

    def test_custom_max_attempts(self) -> None:
        service = VerificationService(max_attempts=5)
        assert service._max_attempts == 5

    def test_default_max_attempts(self) -> None:
        service = VerificationService()
        assert service._max_attempts == 3

    def test_history_is_copy(self) -> None:
        """history property should return a copy."""
        service = VerificationService()
        history = service.history
        history.append(VerificationResult(task_id="fake", status=VerificationStatus.CONFIRMED))
        assert len(service.history) == 0  # Original unchanged


# ============================================================================
# Verification Result Dataclass
# ============================================================================


class TestVerificationResult:
    """😐 Testing the result dataclass."""

    def test_result_fields(self) -> None:
        result = VerificationResult(
            task_id="test-1",
            status=VerificationStatus.CONFIRMED,
            attempt=2,
            error=None,
        )
        assert result.task_id == "test-1"
        assert result.status == VerificationStatus.CONFIRMED
        assert result.attempt == 2
        assert result.error is None
        assert result.checked_at > 0

    def test_result_with_error(self) -> None:
        result = VerificationResult(
            task_id="err-1",
            status=VerificationStatus.NOT_VERIFIED,
            error="Connection refused",
        )
        assert result.error == "Connection refused"


# ============================================================================
# Adapter Registration Edge Cases
# ============================================================================


class TestAdapterRegistration:
    """😐 Edge cases in adapter registration."""

    def test_register_overwrite_same_platform(self) -> None:
        """Registering a second adapter for same platform overwrites."""
        service = VerificationService()
        adapter1 = TwitterAdapter()
        adapter2 = TwitterAdapter()

        service.register_adapter(adapter1)
        service.register_adapter(adapter2)

        # Should use the latest adapter
        assert service._adapters[Platform.TWITTER] is adapter2

    async def test_no_adapter_error_message(self) -> None:
        """Missing adapter should include platform name in error."""
        service = VerificationService()
        task = _make_task(platform=Platform.FACEBOOK)
        result = await service.verify(task)
        assert "No adapter" in result.error
        assert "facebook" in result.error.lower()
