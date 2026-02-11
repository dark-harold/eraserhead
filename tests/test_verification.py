"""
😐 Tests for verification service.
Because "trust but verify" is Harold's relationship with the internet.
"""

from __future__ import annotations

import pytest

from eraserhead.adapters.platforms import SimulatedPlatformData, TwitterAdapter
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
# Fixtures
# ============================================================================


@pytest.fixture
def twitter_verified():
    """Twitter adapter with some resources deleted, some remaining."""
    data = SimulatedPlatformData()
    data.add_resource(ResourceType.POST, "still-here")
    # "deleted-tweet" not in data = simulates successful deletion
    adapter = TwitterAdapter(data)
    creds = PlatformCredentials(platform=Platform.TWITTER, username="harold", auth_token="tok")
    return adapter, creds


@pytest.fixture
def make_completed_task():
    """Factory for completed deletion tasks."""

    def _make(
        task_id: str = "task-1",
        resource_id: str = "deleted-tweet",
        platform: Platform = Platform.TWITTER,
    ) -> DeletionTask:
        task = DeletionTask(
            task_id=task_id,
            platform=platform,
            resource_type=ResourceType.POST,
            resource_id=resource_id,
        )
        task.status = TaskStatus.COMPLETED
        return task

    return _make


# ============================================================================
# Single Verification
# ============================================================================


class TestVerifySingle:
    """🌑 One check at a time."""

    async def test_verify_confirmed(self, twitter_verified, make_completed_task) -> None:
        adapter, creds = twitter_verified
        await adapter.authenticate(creds)

        service = VerificationService()
        service.register_adapter(adapter)

        task = make_completed_task(resource_id="deleted-tweet")
        result = await service.verify(task)
        assert result.status == VerificationStatus.CONFIRMED
        assert task.status == TaskStatus.VERIFIED

    async def test_verify_still_exists(self, twitter_verified, make_completed_task) -> None:
        adapter, creds = twitter_verified
        await adapter.authenticate(creds)

        service = VerificationService()
        service.register_adapter(adapter)

        task = make_completed_task(resource_id="still-here")
        result = await service.verify(task)
        assert result.status == VerificationStatus.FAILED

    async def test_verify_no_adapter(self, make_completed_task) -> None:
        service = VerificationService()
        task = make_completed_task()
        result = await service.verify(task)
        assert result.status == VerificationStatus.NOT_VERIFIED
        assert "No adapter" in result.error

    async def test_verify_unauthenticated(self, twitter_verified, make_completed_task) -> None:
        adapter, _ = twitter_verified
        # Don't authenticate
        service = VerificationService()
        service.register_adapter(adapter)

        task = make_completed_task()
        result = await service.verify(task)
        assert result.status == VerificationStatus.NOT_VERIFIED


# ============================================================================
# Batch Scan
# ============================================================================


class TestBatchScan:
    """😐 Bulk verification for the thorough."""

    async def test_scan_completed_tasks(self, twitter_verified, make_completed_task) -> None:
        adapter, creds = twitter_verified
        await adapter.authenticate(creds)

        service = VerificationService()
        service.register_adapter(adapter)

        tasks = [
            make_completed_task("t1", "deleted-tweet"),
            make_completed_task("t2", "still-here"),
        ]

        results = await service.scan(tasks)
        assert len(results) == 2
        confirmed = [r for r in results if r.status == VerificationStatus.CONFIRMED]
        failed = [r for r in results if r.status == VerificationStatus.FAILED]
        assert len(confirmed) == 1
        assert len(failed) == 1

    async def test_scan_skips_pending_tasks(self, twitter_verified, make_completed_task) -> None:
        adapter, creds = twitter_verified
        await adapter.authenticate(creds)

        service = VerificationService()
        service.register_adapter(adapter)

        pending_task = DeletionTask(
            task_id="pending",
            platform=Platform.TWITTER,
            resource_type=ResourceType.POST,
            resource_id="x",
        )
        # Status is PENDING by default

        results = await service.scan([pending_task])
        assert len(results) == 0


# ============================================================================
# Statistics
# ============================================================================


class TestVerificationStats:
    """😐 Metrics for Harold's verification anxiety."""

    async def test_stats_after_scans(self, twitter_verified, make_completed_task) -> None:
        adapter, creds = twitter_verified
        await adapter.authenticate(creds)

        service = VerificationService()
        service.register_adapter(adapter)

        await service.verify(make_completed_task("t1", "deleted-tweet"))
        await service.verify(make_completed_task("t2", "still-here"))

        stats = service.get_stats()
        assert stats["total"] == 2
        assert stats["confirmed"] == 1
        assert stats["failed"] == 1

    async def test_history_tracked(self, twitter_verified, make_completed_task) -> None:
        adapter, creds = twitter_verified
        await adapter.authenticate(creds)

        service = VerificationService()
        service.register_adapter(adapter)

        await service.verify(make_completed_task())
        assert len(service.history) == 1


# ============================================================================
# Edge Cases
# ============================================================================


class TestVerificationEdgeCases:
    """🌑 The weird paths through verification."""

    async def test_scan_re_verifies_already_verified(
        self, twitter_verified, make_completed_task
    ) -> None:
        """VERIFIED tasks should also be re-scanned."""
        adapter, creds = twitter_verified
        await adapter.authenticate(creds)

        service = VerificationService()
        service.register_adapter(adapter)

        task = make_completed_task(resource_id="deleted-tweet")
        task.status = TaskStatus.VERIFIED

        results = await service.scan([task])
        assert len(results) == 1
        assert results[0].status == VerificationStatus.CONFIRMED

    async def test_verify_exception_in_adapter(self, make_completed_task) -> None:
        """Adapter that raises during verify should be handled gracefully.

        The adapter's verify_deletion catches all exceptions and returns
        NOT_VERIFIED. The error detail is swallowed at the adapter layer.
        """
        from eraserhead.adapters import PlatformAdapter, RateLimitConfig

        class BrokenAdapter(PlatformAdapter):
            def __init__(self):
                super().__init__(
                    platform=Platform.TWITTER,
                    rate_limit=RateLimitConfig(requests_per_minute=60),
                )
                self._authenticated = True

            @property
            def is_authenticated(self) -> bool:
                return True

            def _get_supported_types(self) -> set[ResourceType]:
                return {ResourceType.POST}

            async def _do_authenticate(self, credentials) -> bool:
                return True

            async def _do_delete(self, task):
                pass

            async def _do_verify(self, task):
                raise ConnectionError("💥 Network exploded")

            async def _do_list_resources(self, resource_type):
                return []

        service = VerificationService()
        service.register_adapter(BrokenAdapter())

        task = make_completed_task()
        result = await service.verify(task)
        # Adapter catches exception → returns NOT_VERIFIED status
        assert result.status == VerificationStatus.NOT_VERIFIED

    async def test_stats_empty(self) -> None:
        """Stats on fresh service should be all zeros."""
        service = VerificationService()
        stats = service.get_stats()
        assert stats["total"] == 0
        assert stats["confirmed"] == 0
        assert stats["failed"] == 0

    async def test_scan_mixed_statuses(self, twitter_verified, make_completed_task) -> None:
        """Scan skips PENDING, RUNNING, FAILED, CANCELLED tasks."""
        adapter, creds = twitter_verified
        await adapter.authenticate(creds)

        service = VerificationService()
        service.register_adapter(adapter)

        tasks = []
        for status_val in [
            TaskStatus.PENDING,
            TaskStatus.RUNNING,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        ]:
            t = DeletionTask(
                task_id=f"task-{status_val}",
                platform=Platform.TWITTER,
                resource_type=ResourceType.POST,
                resource_id="x",
            )
            t.status = status_val
            tasks.append(t)

        # Add one completed task that should be scanned
        tasks.append(make_completed_task("should-scan", "deleted-tweet"))

        results = await service.scan(tasks)
        assert len(results) == 1
        assert results[0].task_id == "should-scan"
