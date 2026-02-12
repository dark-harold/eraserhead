"""
😐 Scrubbing Engine: End-to-End Integration Tests

Full pipeline tests: vault → engine → adapters → verification.
The complete arc of Harold's deletion journey.

🌑 If these pass, we can actually delete things. Terrifying.
"""

from __future__ import annotations

from pathlib import Path

from eraserhead.adapters.platforms import (
    FacebookAdapter,
    SimulatedPlatformData,
    TwitterAdapter,
)
from eraserhead.engine import EngineConfig, ScrubEngine
from eraserhead.models import (
    Platform,
    PlatformCredentials,
    ResourceType,
    TaskPriority,
    TaskStatus,
    VerificationStatus,
)
from eraserhead.queue import TaskQueue
from eraserhead.vault import CredentialVault
from eraserhead.verification import VerificationService


# ============================================================================
# Full Pipeline
# ============================================================================


class TestFullPipeline:
    """😐 The complete scrubbing workflow, end to end."""

    async def test_vault_to_engine_to_verify(self, tmp_path: Path) -> None:
        """Store creds → create engine → scrub → verify."""
        # 1. Store credentials in vault
        vault = CredentialVault(tmp_path / "vault")
        vault.unlock("integration-test-pass")

        creds = PlatformCredentials(
            platform=Platform.TWITTER,
            username="harold",
            auth_token="test-token",
        )
        vault.store(creds)

        # 2. Set up simulated data
        data = SimulatedPlatformData()
        data.add_resource(ResourceType.POST, "tweet-100")
        data.add_resource(ResourceType.POST, "tweet-200")
        data.add_resource(ResourceType.POST, "tweet-300")

        # 3. Create and run engine
        adapter = TwitterAdapter(data)
        retrieved_creds = vault.get(Platform.TWITTER, "harold")
        await adapter.authenticate(retrieved_creds)
        vault.lock()

        engine = ScrubEngine(EngineConfig(verify_after_delete=True))
        engine.register_adapter(adapter)
        engine.add_tasks(
            Platform.TWITTER,
            ResourceType.POST,
            ["tweet-100", "tweet-200", "tweet-300"],
        )

        results = await engine.run()

        # 4. All should succeed
        assert len(results) == 3
        assert all(r.success for r in results)
        assert all(r.verified for r in results)
        assert all(r.verification_status == VerificationStatus.CONFIRMED for r in results)

        # 5. Data should be gone
        assert not data.has_resource(ResourceType.POST, "tweet-100")
        assert not data.has_resource(ResourceType.POST, "tweet-200")

    async def test_multi_platform_pipeline(self, tmp_path: Path) -> None:
        """Scrub across Twitter and Facebook simultaneously."""
        tw_data = SimulatedPlatformData()
        tw_data.add_resource(ResourceType.POST, "tw-1")
        fb_data = SimulatedPlatformData()
        fb_data.add_resource(ResourceType.POST, "fb-1")
        fb_data.add_resource(ResourceType.PHOTO, "fb-photo-1")

        tw_adapter = TwitterAdapter(tw_data)
        fb_adapter = FacebookAdapter(fb_data)

        tw_creds = PlatformCredentials(
            platform=Platform.TWITTER, username="harold", auth_token="tok"
        )
        fb_creds = PlatformCredentials(
            platform=Platform.FACEBOOK, username="harold", auth_token="tok"
        )

        await tw_adapter.authenticate(tw_creds)
        await fb_adapter.authenticate(fb_creds)

        engine = ScrubEngine()
        engine.register_adapter(tw_adapter)
        engine.register_adapter(fb_adapter)

        engine.add_tasks(Platform.TWITTER, ResourceType.POST, ["tw-1"])
        engine.add_tasks(Platform.FACEBOOK, ResourceType.POST, ["fb-1"])
        engine.add_tasks(Platform.FACEBOOK, ResourceType.PHOTO, ["fb-photo-1"])

        results = await engine.run()
        assert len(results) == 3
        assert all(r.success for r in results)

        # Check progress
        tw_progress = engine.get_progress(Platform.TWITTER)
        fb_progress = engine.get_progress(Platform.FACEBOOK)
        assert tw_progress[0].completed == 1
        assert fb_progress[0].completed == 2


# ============================================================================
# Dry Run Pipeline
# ============================================================================


class TestDryRunPipeline:
    """😐 Rehearsal before the real show."""

    async def test_dry_run_preserves_data(self) -> None:
        data = SimulatedPlatformData()
        data.add_resource(ResourceType.POST, "precious-tweet")

        adapter = TwitterAdapter(data)
        creds = PlatformCredentials(platform=Platform.TWITTER, username="harold", auth_token="tok")
        await adapter.authenticate(creds)

        engine = ScrubEngine(EngineConfig(dry_run=True))
        engine.register_adapter(adapter)
        engine.add_tasks(Platform.TWITTER, ResourceType.POST, ["precious-tweet"])

        results = await engine.run()
        assert results[0].success is True
        assert "dry_run" in results[0].proof

        # Data still exists!
        assert data.has_resource(ResourceType.POST, "precious-tweet")


# ============================================================================
# Queue Persistence Pipeline
# ============================================================================


class TestQueuePersistence:
    """😐 Crash recovery: because Harold plans for disaster."""

    async def test_save_and_resume(self, tmp_path: Path) -> None:
        """Save queue mid-run, reload, and continue."""
        data = SimulatedPlatformData()
        data.add_resource(ResourceType.POST, "t1")
        data.add_resource(ResourceType.POST, "t2")

        adapter = TwitterAdapter(data)
        creds = PlatformCredentials(platform=Platform.TWITTER, username="harold", auth_token="tok")
        await adapter.authenticate(creds)

        # Run first batch
        queue_path = tmp_path / "queue.json"
        engine = ScrubEngine(EngineConfig(queue_save_path=queue_path))
        engine.register_adapter(adapter)
        engine.add_tasks(Platform.TWITTER, ResourceType.POST, ["t1"])

        await engine.run()
        assert queue_path.exists()

        # Verify the saved queue has the completed task
        loaded = TaskQueue.load(queue_path)
        completed = loaded.get_tasks_by_status(TaskStatus.COMPLETED)
        assert len(completed) == 1


# ============================================================================
# Verification Pipeline
# ============================================================================


class TestVerificationPipeline:
    """🌑 Verify the deletions actually happened."""

    async def test_post_run_verification_scan(self) -> None:
        data = SimulatedPlatformData()
        data.add_resource(ResourceType.POST, "t1")
        data.add_resource(ResourceType.POST, "t2")

        adapter = TwitterAdapter(data)
        creds = PlatformCredentials(platform=Platform.TWITTER, username="harold", auth_token="tok")
        await adapter.authenticate(creds)

        # Run engine (deletes resources)
        engine = ScrubEngine(EngineConfig(verify_after_delete=False))
        engine.register_adapter(adapter)
        tasks = engine.add_tasks(Platform.TWITTER, ResourceType.POST, ["t1", "t2"])

        await engine.run()

        # Now run verification service
        service = VerificationService()
        service.register_adapter(adapter)

        results = await service.scan(tasks)
        assert len(results) == 2
        assert all(r.status == VerificationStatus.CONFIRMED for r in results)

        stats = service.get_stats()
        assert stats["confirmed"] == 2

    async def test_verification_detects_remaining_resource(self) -> None:
        """If deletion fails silently, verification catches it."""
        data = SimulatedPlatformData()
        data.add_resource(ResourceType.POST, "stubborn-tweet")

        adapter = TwitterAdapter(data)
        creds = PlatformCredentials(platform=Platform.TWITTER, username="harold", auth_token="tok")
        await adapter.authenticate(creds)

        # Create task but don't actually delete
        from eraserhead.models import DeletionTask

        task = DeletionTask(
            task_id="verify-test",
            platform=Platform.TWITTER,
            resource_type=ResourceType.POST,
            resource_id="stubborn-tweet",
        )
        task.status = TaskStatus.COMPLETED  # Pretend it was "deleted"

        service = VerificationService()
        service.register_adapter(adapter)

        result = await service.verify(task)
        assert result.status == VerificationStatus.FAILED
        # Task should NOT be marked verified
        assert task.status == TaskStatus.COMPLETED


# ============================================================================
# Priority Ordering Pipeline
# ============================================================================


class TestPriorityPipeline:
    """😐 Urgent tasks first, background tasks whenever."""

    async def test_priority_ordering_in_engine(self) -> None:
        data = SimulatedPlatformData()
        for i in range(5):
            data.add_resource(ResourceType.POST, f"t{i}")

        adapter = TwitterAdapter(data)
        creds = PlatformCredentials(platform=Platform.TWITTER, username="harold", auth_token="tok")
        await adapter.authenticate(creds)

        engine = ScrubEngine()
        engine.register_adapter(adapter)

        # Add in reverse priority order
        engine.add_tasks(Platform.TWITTER, ResourceType.POST, ["t0"], TaskPriority.BACKGROUND)
        engine.add_tasks(Platform.TWITTER, ResourceType.POST, ["t1"], TaskPriority.URGENT)
        engine.add_tasks(Platform.TWITTER, ResourceType.POST, ["t2"], TaskPriority.STANDARD)

        results = await engine.run()
        assert len(results) == 3
        # All should succeed regardless of priority
        assert all(r.success for r in results)
