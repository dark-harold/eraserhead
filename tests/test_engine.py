"""
😐 Tests for the scrubbing engine core.
Orchestrating deletion with confidence and mild existential dread.
"""

from __future__ import annotations

from pathlib import Path

import pytest

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


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def twitter_setup():
    """Authenticated Twitter adapter with test data."""
    data = SimulatedPlatformData()
    data.add_resource(ResourceType.POST, "tweet-1")
    data.add_resource(ResourceType.POST, "tweet-2")
    data.add_resource(ResourceType.POST, "tweet-3")
    data.add_resource(ResourceType.COMMENT, "reply-1")
    adapter = TwitterAdapter(data)
    creds = PlatformCredentials(platform=Platform.TWITTER, username="harold", auth_token="tok")
    return adapter, creds, data


@pytest.fixture
def facebook_setup():
    """Authenticated Facebook adapter with test data."""
    data = SimulatedPlatformData()
    data.add_resource(ResourceType.POST, "fb-1")
    data.add_resource(ResourceType.PHOTO, "fb-photo-1")
    adapter = FacebookAdapter(data)
    creds = PlatformCredentials(platform=Platform.FACEBOOK, username="harold", auth_token="tok")
    return adapter, creds, data


# ============================================================================
# Basic Engine Operations
# ============================================================================


class TestEngineBasic:
    """😐 Core engine functionality."""

    async def test_empty_engine(self) -> None:
        engine = ScrubEngine()
        results = await engine.run()
        assert results == []

    async def test_add_tasks(self, twitter_setup) -> None:
        adapter, creds, _ = twitter_setup
        engine = ScrubEngine()
        engine.register_adapter(adapter)

        tasks = engine.add_tasks(
            Platform.TWITTER,
            ResourceType.POST,
            ["tweet-1", "tweet-2"],
        )
        assert len(tasks) == 2
        assert engine.queue.size == 2

    async def test_run_deletes_resources(self, twitter_setup) -> None:
        adapter, creds, data = twitter_setup
        await adapter.authenticate(creds)

        engine = ScrubEngine()
        engine.register_adapter(adapter)
        engine.add_tasks(
            Platform.TWITTER,
            ResourceType.POST,
            ["tweet-1", "tweet-2"],
        )

        results = await engine.run()
        assert len(results) == 2
        assert all(r.success for r in results)
        assert not data.has_resource(ResourceType.POST, "tweet-1")
        assert not data.has_resource(ResourceType.POST, "tweet-2")

    async def test_no_adapter_for_platform(self) -> None:
        engine = ScrubEngine(EngineConfig(max_retries=0))
        engine.add_tasks(
            Platform.TWITTER,
            ResourceType.POST,
            ["tweet-1"],
        )
        results = await engine.run()
        assert len(results) == 1
        assert results[0].success is False
        assert "No adapter" in results[0].error_message

    async def test_unauthenticated_adapter(self, twitter_setup) -> None:
        adapter, _, _ = twitter_setup
        # Don't authenticate
        engine = ScrubEngine()
        engine.register_adapter(adapter)
        engine.add_tasks(Platform.TWITTER, ResourceType.POST, ["tweet-1"])

        results = await engine.run()
        assert results[0].success is False
        assert "not authenticated" in results[0].error_message.lower()


# ============================================================================
# Dry Run
# ============================================================================


class TestDryRun:
    """😐 Preview mode: see what would be destroyed."""

    async def test_dry_run_no_deletion(self, twitter_setup) -> None:
        adapter, creds, data = twitter_setup
        await adapter.authenticate(creds)

        config = EngineConfig(dry_run=True)
        engine = ScrubEngine(config)
        engine.register_adapter(adapter)
        engine.add_tasks(
            Platform.TWITTER,
            ResourceType.POST,
            ["tweet-1", "tweet-2"],
        )

        results = await engine.run()
        assert len(results) == 2
        assert all(r.success for r in results)
        # Resources still exist!
        assert data.has_resource(ResourceType.POST, "tweet-1")
        assert data.has_resource(ResourceType.POST, "tweet-2")
        # Proof contains "dry_run"
        assert all("dry_run" in r.proof for r in results)


# ============================================================================
# Verification
# ============================================================================


class TestVerification:
    """🌑 Trust no deletion without verification."""

    async def test_verification_after_delete(self, twitter_setup) -> None:
        adapter, creds, _ = twitter_setup
        await adapter.authenticate(creds)

        config = EngineConfig(verify_after_delete=True)
        engine = ScrubEngine(config)
        engine.register_adapter(adapter)
        engine.add_tasks(Platform.TWITTER, ResourceType.POST, ["tweet-1"])

        results = await engine.run()
        assert results[0].success is True
        assert results[0].verified is True
        assert results[0].verification_status == VerificationStatus.CONFIRMED

    async def test_no_verification(self, twitter_setup) -> None:
        adapter, creds, _ = twitter_setup
        await adapter.authenticate(creds)

        config = EngineConfig(verify_after_delete=False)
        engine = ScrubEngine(config)
        engine.register_adapter(adapter)
        engine.add_tasks(Platform.TWITTER, ResourceType.POST, ["tweet-1"])

        results = await engine.run()
        assert results[0].success is True
        assert results[0].verified is False


# ============================================================================
# Retry & Failure
# ============================================================================


class TestRetryAndFailure:
    """😐 Failures happen. Retries happen. Harold empathizes."""

    async def test_failed_deletion_retries(self, twitter_setup) -> None:
        adapter, creds, data = twitter_setup
        await adapter.authenticate(creds)

        engine = ScrubEngine(EngineConfig(max_retries=2, verify_after_delete=False))
        engine.register_adapter(adapter)
        # "ghost" doesn't exist → all attempts fail
        engine.add_tasks(Platform.TWITTER, ResourceType.POST, ["ghost"])

        results = await engine.run()
        # Should have tried multiple times
        assert len(results) >= 2  # Initial + retries
        assert all(not r.success for r in results)


# ============================================================================
# Multi-Platform
# ============================================================================


class TestMultiPlatform:
    """😐 Deleting across platforms simultaneously."""

    async def test_multi_platform_run(self, twitter_setup, facebook_setup) -> None:
        tw_adapter, tw_creds, tw_data = twitter_setup
        fb_adapter, fb_creds, fb_data = facebook_setup
        await tw_adapter.authenticate(tw_creds)
        await fb_adapter.authenticate(fb_creds)

        engine = ScrubEngine()
        engine.register_adapter(tw_adapter)
        engine.register_adapter(fb_adapter)

        engine.add_tasks(Platform.TWITTER, ResourceType.POST, ["tweet-1"])
        engine.add_tasks(Platform.FACEBOOK, ResourceType.POST, ["fb-1"])

        results = await engine.run()
        assert len(results) == 2
        assert all(r.success for r in results)


# ============================================================================
# Progress Tracking
# ============================================================================


class TestProgress:
    """😐 Quantifying Harold's scrubbing anxiety."""

    async def test_progress_after_run(self, twitter_setup) -> None:
        adapter, creds, _ = twitter_setup
        await adapter.authenticate(creds)

        engine = ScrubEngine()
        engine.register_adapter(adapter)
        engine.add_tasks(
            Platform.TWITTER,
            ResourceType.POST,
            ["tweet-1", "tweet-2", "tweet-3"],
        )

        await engine.run()
        progress = engine.get_progress(Platform.TWITTER)
        assert len(progress) == 1
        p = progress[0]
        assert p.platform == Platform.TWITTER
        assert p.total_tasks == 3
        assert p.completed == 3
        assert p.is_done is True

    async def test_progress_empty(self) -> None:
        engine = ScrubEngine()
        assert engine.get_progress() == []


# ============================================================================
# Process One
# ============================================================================


class TestProcessOne:
    """😐 One task at a time for the anxious."""

    async def test_process_one(self, twitter_setup) -> None:
        adapter, creds, _ = twitter_setup
        await adapter.authenticate(creds)

        engine = ScrubEngine()
        engine.register_adapter(adapter)
        engine.add_tasks(Platform.TWITTER, ResourceType.POST, ["tweet-1", "tweet-2"])

        r1 = await engine.process_one()
        assert r1 is not None
        assert r1.success is True

        r2 = await engine.process_one()
        assert r2 is not None

        r3 = await engine.process_one()
        assert r3 is None  # Queue empty

    async def test_process_one_empty(self) -> None:
        engine = ScrubEngine()
        assert await engine.process_one() is None


# ============================================================================
# Queue Persistence
# ============================================================================


class TestQueuePersistence:
    """😐 Surviving crashes: the Harold way."""

    async def test_saves_queue_during_run(self, twitter_setup, tmp_path) -> None:
        adapter, creds, _ = twitter_setup
        await adapter.authenticate(creds)

        save_path = tmp_path / "queue.json"
        config = EngineConfig(queue_save_path=save_path)
        engine = ScrubEngine(config)
        engine.register_adapter(adapter)
        engine.add_tasks(Platform.TWITTER, ResourceType.POST, ["tweet-1"])

        await engine.run()
        assert save_path.exists()
