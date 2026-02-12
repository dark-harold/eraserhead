"""
😐 Edge case and load tests for the scrubbing engine.

Tests for network failures, rate limiting, invalid credentials,
partial deletion failures, and bulk operations.

🌑 Dark Harold's nightmares, tested systematically.
"""

from __future__ import annotations

import pytest

from eraserhead.adapters import AdapterStatus, PlatformAdapter, RateLimitConfig
from eraserhead.engine import EngineConfig, ScrubEngine
from eraserhead.models import (
    DeletionResult,
    DeletionTask,
    Platform,
    PlatformCredentials,
    ResourceType,
    TaskPriority,
    VerificationStatus,
)
from eraserhead.queue import DuplicateTaskError, TaskQueue
from eraserhead.vault import CredentialVault, VaultCorruptedError, VaultError


# ============================================================================
# Mock Adapters for Edge Cases
# ============================================================================


class FailingAdapter(PlatformAdapter):
    """Adapter that always fails deletion."""

    def __init__(self, platform: Platform = Platform.TWITTER) -> None:
        super().__init__(
            platform=platform,
            rate_limit=RateLimitConfig(
                requests_per_minute=100_000,
                burst_size=100_000,
            ),
        )
        self._status = AdapterStatus.AUTHENTICATED

    async def _do_authenticate(self, credentials) -> bool:
        return True

    async def _do_disconnect(self) -> None:
        pass

    async def _do_delete(self, task: DeletionTask) -> DeletionResult:
        return DeletionResult(
            task_id=task.task_id,
            success=False,
            error_message="API rate limit exceeded (429)",
        )

    async def _do_verify(self, task: DeletionTask) -> VerificationStatus:
        return VerificationStatus.NOT_VERIFIED

    async def _do_list_resources(self, resource_type: ResourceType) -> list[dict[str, str]]:
        return []

    def _get_supported_types(self) -> set[ResourceType]:
        return {ResourceType.POST, ResourceType.COMMENT}


class PartialFailAdapter(PlatformAdapter):
    """Adapter that fails on specific resource IDs."""

    def __init__(
        self,
        platform: Platform = Platform.TWITTER,
        fail_ids: set[str] | None = None,
    ) -> None:
        super().__init__(
            platform=platform,
            rate_limit=RateLimitConfig(
                requests_per_minute=100_000,
                burst_size=100_000,
            ),
        )
        self._status = AdapterStatus.AUTHENTICATED
        self._fail_ids = fail_ids or set()
        self.delete_count = 0

    async def _do_authenticate(self, credentials) -> bool:
        return True

    async def _do_disconnect(self) -> None:
        pass

    async def _do_delete(self, task: DeletionTask) -> DeletionResult:
        self.delete_count += 1
        if task.resource_id in self._fail_ids:
            return DeletionResult(
                task_id=task.task_id,
                success=False,
                error_message=f"Resource {task.resource_id} not found (404)",
            )
        return DeletionResult(
            task_id=task.task_id,
            success=True,
            proof=f"deleted:{task.resource_id}",
        )

    async def _do_verify(self, task: DeletionTask) -> VerificationStatus:
        if task.resource_id in self._fail_ids:
            return VerificationStatus.NOT_VERIFIED
        return VerificationStatus.CONFIRMED

    async def _do_list_resources(self, resource_type: ResourceType) -> list[dict[str, str]]:
        return []

    def _get_supported_types(self) -> set[ResourceType]:
        return {ResourceType.POST, ResourceType.COMMENT}


class SlowAdapter(PlatformAdapter):
    """Adapter that succeeds but counts operations."""

    def __init__(self, platform: Platform = Platform.FACEBOOK) -> None:
        super().__init__(
            platform=platform,
            rate_limit=RateLimitConfig(
                requests_per_minute=100_000,
                burst_size=100_000,
            ),
        )
        self._status = AdapterStatus.AUTHENTICATED
        self.operation_count = 0

    async def _do_authenticate(self, credentials) -> bool:
        return True

    async def _do_disconnect(self) -> None:
        pass

    async def _do_delete(self, task: DeletionTask) -> DeletionResult:
        self.operation_count += 1
        return DeletionResult(
            task_id=task.task_id,
            success=True,
            proof=f"deleted:{task.resource_id}",
        )

    async def _do_verify(self, task: DeletionTask) -> VerificationStatus:
        self.operation_count += 1
        return VerificationStatus.CONFIRMED

    async def _do_list_resources(self, resource_type: ResourceType) -> list[dict[str, str]]:
        return []

    def _get_supported_types(self) -> set[ResourceType]:
        return {ResourceType.POST, ResourceType.COMMENT}


# ============================================================================
# Edge Case Tests: Network Failures & Rate Limiting
# ============================================================================


class TestEngineEdgeCases:
    """😐 Testing when things go wrong — Harold's comfort zone."""

    async def test_no_adapter_registered(self) -> None:
        """Tasks for unregistered platform should fail gracefully."""
        engine = ScrubEngine(EngineConfig(verify_after_delete=False, max_retries=0))
        engine.add_tasks(Platform.TWITTER, ResourceType.POST, ["id-1", "id-2"])

        results = await engine.run()

        assert len(results) == 2
        assert all(not r.success for r in results)
        assert all("No adapter" in (r.error_message or "") for r in results)

    async def test_unauthenticated_adapter(self) -> None:
        """Unauthenticated adapter should fail tasks."""
        engine = ScrubEngine(EngineConfig(verify_after_delete=False, max_retries=0))

        adapter = FailingAdapter(Platform.TWITTER)
        adapter._status = AdapterStatus.DISCONNECTED
        engine.register_adapter(adapter)

        engine.add_tasks(Platform.TWITTER, ResourceType.POST, ["id-1"])
        results = await engine.run()

        assert len(results) == 1
        assert not results[0].success
        assert "not authenticated" in (results[0].error_message or "").lower()

    async def test_all_tasks_fail(self) -> None:
        """All tasks failing should not crash engine."""
        engine = ScrubEngine(EngineConfig(verify_after_delete=False, max_retries=0))
        engine.register_adapter(FailingAdapter(Platform.TWITTER))

        engine.add_tasks(Platform.TWITTER, ResourceType.POST, ["id-1", "id-2", "id-3"])
        results = await engine.run()

        assert len(results) == 3
        assert all(not r.success for r in results)

    async def test_partial_deletion_failure(self) -> None:
        """Mixed success/failure should report correctly."""
        adapter = PartialFailAdapter(
            Platform.TWITTER,
            fail_ids={"fail-1", "fail-2"},
        )
        engine = ScrubEngine(EngineConfig(verify_after_delete=False, max_retries=0))
        engine.register_adapter(adapter)

        ids = ["ok-1", "fail-1", "ok-2", "fail-2", "ok-3"]
        engine.add_tasks(Platform.TWITTER, ResourceType.POST, ids)

        results = await engine.run()

        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        assert len(successful) == 3
        assert len(failed) == 2

    async def test_dry_run_no_deletion(self) -> None:
        """Dry run should report success without deleting."""
        adapter = PartialFailAdapter(Platform.TWITTER)
        engine = ScrubEngine(EngineConfig(dry_run=True))
        engine.register_adapter(adapter)

        engine.add_tasks(Platform.TWITTER, ResourceType.POST, ["id-1", "id-2"])
        results = await engine.run()

        assert len(results) == 2
        assert all(r.success for r in results)
        assert all("dry_run" in (r.proof or "") for r in results)
        assert adapter.delete_count == 0  # No actual deletion

    async def test_engine_not_running_after_completion(self) -> None:
        """Engine.is_running should be False after run completes."""
        engine = ScrubEngine(EngineConfig(verify_after_delete=False))
        engine.register_adapter(PartialFailAdapter(Platform.TWITTER))
        engine.add_tasks(Platform.TWITTER, ResourceType.POST, ["id-1"])

        assert not engine.is_running
        await engine.run()
        assert not engine.is_running

    async def test_process_one_empty_queue(self) -> None:
        """process_one on empty queue returns None."""
        engine = ScrubEngine()
        result = await engine.process_one()
        assert result is None

    async def test_queue_save_path(self, tmp_path) -> None:
        """Queue state saved after each task when path configured."""
        save_path = tmp_path / "queue.json"
        engine = ScrubEngine(
            EngineConfig(
                verify_after_delete=False,
                queue_save_path=save_path,
            )
        )
        engine.register_adapter(PartialFailAdapter(Platform.TWITTER))
        engine.add_tasks(Platform.TWITTER, ResourceType.POST, ["id-1", "id-2"])

        await engine.run()

        assert save_path.exists()


# ============================================================================
# Load Tests: Bulk Operations
# ============================================================================


class TestEngineLoad:
    """😐 Bulk deletion testing. Harold processes thousands of tasks."""

    async def test_bulk_1000_tasks(self) -> None:
        """Engine handles 1000+ tasks without issues."""
        adapter = SlowAdapter(Platform.FACEBOOK)
        engine = ScrubEngine(EngineConfig(verify_after_delete=False))
        engine.register_adapter(adapter)

        # Add 1000 tasks
        ids = [f"resource-{i}" for i in range(1000)]
        engine.add_tasks(Platform.FACEBOOK, ResourceType.POST, ids)

        results = await engine.run()

        assert len(results) == 1000
        assert all(r.success for r in results)
        assert adapter.operation_count == 1000

    async def test_multi_platform_concurrent(self) -> None:
        """Multiple platforms processed in priority order."""
        twitter_adapter = SlowAdapter(Platform.TWITTER)
        fb_adapter = SlowAdapter(Platform.FACEBOOK)
        ig_adapter = SlowAdapter(Platform.INSTAGRAM)

        engine = ScrubEngine(EngineConfig(verify_after_delete=False))
        engine.register_adapter(twitter_adapter)
        engine.register_adapter(fb_adapter)
        engine.register_adapter(ig_adapter)

        # Add tasks across platforms with different priorities
        engine.add_tasks(
            Platform.TWITTER,
            ResourceType.POST,
            [f"tw-{i}" for i in range(100)],
            TaskPriority.URGENT,
        )
        engine.add_tasks(
            Platform.FACEBOOK,
            ResourceType.POST,
            [f"fb-{i}" for i in range(100)],
            TaskPriority.STANDARD,
        )
        engine.add_tasks(
            Platform.INSTAGRAM,
            ResourceType.POST,
            [f"ig-{i}" for i in range(100)],
            TaskPriority.BACKGROUND,
        )

        results = await engine.run()

        assert len(results) == 300
        assert all(r.success for r in results)

    async def test_progress_tracking(self) -> None:
        """Progress reports correct counts per platform."""
        adapter = PartialFailAdapter(
            Platform.TWITTER,
            fail_ids={"fail-1", "fail-2"},
        )
        engine = ScrubEngine(EngineConfig(verify_after_delete=False, max_retries=0))
        engine.register_adapter(adapter)

        ids = ["ok-1", "fail-1", "ok-2", "fail-2"]
        engine.add_tasks(Platform.TWITTER, ResourceType.POST, ids)
        await engine.run()

        progress = engine.get_progress(Platform.TWITTER)
        assert len(progress) == 1
        p = progress[0]
        assert p.total_tasks == 4
        assert p.completed == 2
        assert p.failed == 2


# ============================================================================
# Task Queue Edge Cases
# ============================================================================


class TestQueueEdgeCases:
    """😐 Queue behavior under stress."""

    def test_duplicate_resource_ids_rejected(self) -> None:
        """Queue should reject duplicate resource IDs."""
        queue = TaskQueue()
        queue.add_task(Platform.TWITTER, ResourceType.POST, "same-id")
        with pytest.raises(DuplicateTaskError):
            queue.add_task(Platform.TWITTER, ResourceType.POST, "same-id")

    def test_same_id_different_platforms(self) -> None:
        """Same resource ID on different platforms is OK."""
        queue = TaskQueue()
        t1 = queue.add_task(Platform.TWITTER, ResourceType.POST, "same-id")
        t2 = queue.add_task(Platform.FACEBOOK, ResourceType.POST, "same-id")
        assert t1.task_id != t2.task_id

    def test_priority_ordering(self) -> None:
        """URGENT tasks should be dequeued before STANDARD."""
        queue = TaskQueue()
        queue.add_task(
            Platform.TWITTER,
            ResourceType.POST,
            "low",
            priority=TaskPriority.BACKGROUND,
        )
        queue.add_task(
            Platform.TWITTER,
            ResourceType.POST,
            "high",
            priority=TaskPriority.URGENT,
        )
        queue.add_task(
            Platform.TWITTER,
            ResourceType.POST,
            "mid",
            priority=TaskPriority.STANDARD,
        )

        t1 = queue.next_task()
        t2 = queue.next_task()
        t3 = queue.next_task()

        assert t1.priority == TaskPriority.URGENT
        assert t2.priority == TaskPriority.STANDARD
        assert t3.priority == TaskPriority.BACKGROUND

    def test_queue_save_load_roundtrip(self, tmp_path) -> None:
        """Queue can be saved and restored."""
        queue = TaskQueue()
        queue.add_task(Platform.TWITTER, ResourceType.POST, "id-1")
        queue.add_task(Platform.FACEBOOK, ResourceType.COMMENT, "id-2")

        save_path = tmp_path / "queue.json"
        queue.save(save_path)

        loaded = TaskQueue.load(save_path)
        assert loaded.size == 2


# ============================================================================
# Vault Edge Cases
# ============================================================================


class TestVaultEdgeCases:
    """😐 Vault behavior under adversarial conditions."""

    def test_vault_lock_unlock_cycle(self, tmp_path) -> None:
        """Vault lock/unlock cycle should work cleanly."""
        vault = CredentialVault(tmp_path)
        vault.unlock("passphrase")
        assert vault.exists  # vault was created on unlock

        vault.lock()
        assert not vault.is_unlocked

    def test_vault_corrupted_file(self, tmp_path) -> None:
        """Corrupted vault file should raise on credential access."""
        vault_path = tmp_path / "credentials.vault"
        # Write enough bytes for salt + garbage encrypted data
        vault_path.write_bytes(b"x" * 32 + b"corrupted-encrypted-data")

        vault = CredentialVault(tmp_path)
        vault.unlock("any-passphrase")  # Succeeds (just derives key from garbage salt)

        # Fails when trying to decrypt the garbage
        with pytest.raises((VaultError, VaultCorruptedError)):
            vault.store(
                PlatformCredentials(
                    platform=Platform.TWITTER,
                    username="test",
                )
            )
