"""
😐 Tests for task queue & scheduling.
Testing failure modes is the most honest work Harold does.
"""

from __future__ import annotations

import pytest
from pathlib import Path

from eraserhead.models import (
    DeletionTask,
    Platform,
    ResourceType,
    TaskPriority,
    TaskStatus,
)
from eraserhead.queue import (
    TaskQueue,
    DuplicateTaskError,
    QueueEmptyError,
    QueueError,
    BASE_RETRY_DELAY_SECONDS,
    MAX_RETRY_DELAY_SECONDS,
)


# ============================================================================
# Basic Operations
# ============================================================================


class TestTaskQueueBasic:
    """😐 Core queue operations."""

    def test_add_task(self) -> None:
        q = TaskQueue()
        task = q.add_task(Platform.TWITTER, ResourceType.POST, "post-123")
        assert task.platform == Platform.TWITTER
        assert task.resource_type == ResourceType.POST
        assert task.resource_id == "post-123"
        assert task.status == TaskStatus.PENDING
        assert q.size == 1

    def test_add_duplicate_resource_rejected(self) -> None:
        q = TaskQueue()
        q.add_task(Platform.TWITTER, ResourceType.POST, "post-123")
        with pytest.raises(DuplicateTaskError):
            q.add_task(Platform.TWITTER, ResourceType.POST, "post-123")

    def test_same_resource_different_platform_ok(self) -> None:
        q = TaskQueue()
        q.add_task(Platform.TWITTER, ResourceType.POST, "post-123")
        q.add_task(Platform.FACEBOOK, ResourceType.POST, "post-123")
        assert q.size == 2

    def test_get_task_by_id(self) -> None:
        q = TaskQueue()
        task = q.add_task(Platform.TWITTER, ResourceType.POST, "p1")
        retrieved = q.get_task(task.task_id)
        assert retrieved is task

    def test_get_nonexistent_returns_none(self) -> None:
        q = TaskQueue()
        assert q.get_task("nonexistent") is None

    def test_add_with_metadata(self) -> None:
        q = TaskQueue()
        task = q.add_task(
            Platform.INSTAGRAM,
            ResourceType.PHOTO,
            "photo-456",
            metadata={"url": "https://instagram.com/p/456"},
        )
        assert task.metadata["url"] == "https://instagram.com/p/456"


# ============================================================================
# Priority Ordering
# ============================================================================


class TestPriorityOrdering:
    """😐 High priority tasks go first. Like Harold's anxiety."""

    def test_next_returns_highest_priority(self) -> None:
        q = TaskQueue()
        q.add_task(Platform.TWITTER, ResourceType.POST, "low", TaskPriority.LOW)
        q.add_task(Platform.TWITTER, ResourceType.COMMENT, "urgent", TaskPriority.URGENT)
        q.add_task(Platform.TWITTER, ResourceType.LIKE, "standard", TaskPriority.STANDARD)

        task = q.next_task()
        assert task.resource_id == "urgent"
        assert task.status == TaskStatus.RUNNING

    def test_fifo_within_same_priority(self) -> None:
        q = TaskQueue()
        q.add_task(Platform.TWITTER, ResourceType.POST, "first", TaskPriority.STANDARD)
        q.add_task(Platform.TWITTER, ResourceType.COMMENT, "second", TaskPriority.STANDARD)

        t1 = q.next_task()
        assert t1.resource_id == "first"

    def test_empty_queue_raises(self) -> None:
        q = TaskQueue()
        with pytest.raises(QueueEmptyError):
            q.next_task()

    def test_all_running_means_empty(self) -> None:
        q = TaskQueue()
        q.add_task(Platform.TWITTER, ResourceType.POST, "p1")
        q.next_task()  # Now running
        with pytest.raises(QueueEmptyError):
            q.next_task()


# ============================================================================
# Task Lifecycle
# ============================================================================


class TestTaskLifecycle:
    """😐 Tasks go through stages. Like grief, but for data."""

    def test_complete_task(self) -> None:
        q = TaskQueue()
        task = q.add_task(Platform.TWITTER, ResourceType.POST, "p1")
        q.next_task()
        q.complete_task(task.task_id)
        assert task.status == TaskStatus.COMPLETED

    def test_fail_with_retry(self) -> None:
        q = TaskQueue(max_retries=3)
        task = q.add_task(Platform.TWITTER, ResourceType.POST, "p1")
        q.next_task()
        will_retry = q.fail_task(task.task_id, "rate limited")
        assert will_retry is True
        assert task.status == TaskStatus.RETRYING
        assert task.retry_count == 1

    def test_fail_permanently(self) -> None:
        q = TaskQueue(max_retries=1)
        task = q.add_task(Platform.TWITTER, ResourceType.POST, "p1")
        q.next_task()
        q.fail_task(task.task_id, "first fail")  # retry_count=1 now
        q.next_task()  # retrying → running
        will_retry = q.fail_task(task.task_id, "second fail")
        assert will_retry is False
        assert task.status == TaskStatus.FAILED

    def test_cancel_task(self) -> None:
        q = TaskQueue()
        task = q.add_task(Platform.TWITTER, ResourceType.POST, "p1")
        q.cancel_task(task.task_id)
        assert task.status == TaskStatus.CANCELLED

    def test_fail_nonexistent_raises(self) -> None:
        q = TaskQueue()
        with pytest.raises(QueueError):
            q.fail_task("ghost", "error")

    def test_retrying_task_available_as_next(self) -> None:
        q = TaskQueue(max_retries=3)
        task = q.add_task(Platform.TWITTER, ResourceType.POST, "p1")
        q.next_task()
        q.fail_task(task.task_id, "oops")

        # Retrying task should be available
        next_task = q.next_task()
        assert next_task.task_id == task.task_id


# ============================================================================
# Retry Backoff
# ============================================================================


class TestRetryBackoff:
    """🌑 Exponential backoff prevents us from annoying APIs."""

    def test_first_retry_is_base_delay(self) -> None:
        q = TaskQueue()
        task = DeletionTask(
            task_id="t1",
            platform=Platform.TWITTER,
            resource_type=ResourceType.POST,
            resource_id="p1",
            retry_count=1,
        )
        delay = q.get_retry_delay(task)
        # Base delay ±50% jitter
        assert BASE_RETRY_DELAY_SECONDS * 0.4 <= delay <= BASE_RETRY_DELAY_SECONDS * 1.6

    def test_backoff_grows_exponentially(self) -> None:
        q = TaskQueue()
        delays = []
        for retry in range(1, 5):
            task = DeletionTask(
                task_id=f"t{retry}",
                platform=Platform.TWITTER,
                resource_type=ResourceType.POST,
                resource_id=f"p{retry}",
                retry_count=retry,
            )
            # Get multiple samples and take median
            samples = [q.get_retry_delay(task) for _ in range(20)]
            delays.append(sorted(samples)[10])

        # Each median should roughly double
        for i in range(1, len(delays)):
            assert delays[i] > delays[i - 1] * 1.2  # Allow for jitter

    def test_backoff_capped(self) -> None:
        q = TaskQueue()
        task = DeletionTask(
            task_id="t1",
            platform=Platform.TWITTER,
            resource_type=ResourceType.POST,
            resource_id="p1",
            retry_count=20,  # Very high retry count
        )
        delay = q.get_retry_delay(task)
        assert delay <= MAX_RETRY_DELAY_SECONDS * 1.6  # With jitter


# ============================================================================
# Stats & Filtering
# ============================================================================


class TestQueueStats:
    """😐 Harold needs metrics to quantify his anxiety."""

    def test_empty_stats(self) -> None:
        q = TaskQueue()
        stats = q.get_stats()
        assert stats.total == 0
        assert stats.active == 0

    def test_mixed_status_stats(self) -> None:
        q = TaskQueue(max_retries=3)
        q.add_task(Platform.TWITTER, ResourceType.POST, "p1")  # pending
        q.add_task(Platform.TWITTER, ResourceType.COMMENT, "c1")  # pending
        task = q.add_task(Platform.FACEBOOK, ResourceType.POST, "f1")  # will be running
        q.next_task()  # p1 → running... wait, priority order
        # Actually: all same priority, FIFO, so p1 runs first
        q.complete_task(q.get_tasks_by_status(TaskStatus.RUNNING)[0].task_id)

        stats = q.get_stats()
        assert stats.total == 3
        assert stats.completed == 1
        assert stats.pending == 2

    def test_filter_by_platform(self) -> None:
        q = TaskQueue()
        q.add_task(Platform.TWITTER, ResourceType.POST, "t1")
        q.add_task(Platform.TWITTER, ResourceType.COMMENT, "t2")
        q.add_task(Platform.FACEBOOK, ResourceType.POST, "f1")

        twitter_tasks = q.get_tasks_by_platform(Platform.TWITTER)
        assert len(twitter_tasks) == 2

    def test_filter_by_status(self) -> None:
        q = TaskQueue()
        q.add_task(Platform.TWITTER, ResourceType.POST, "p1")
        q.add_task(Platform.TWITTER, ResourceType.COMMENT, "c1")
        q.next_task()  # p1 → running

        running = q.get_tasks_by_status(TaskStatus.RUNNING)
        assert len(running) == 1

    def test_iter_pending(self) -> None:
        q = TaskQueue()
        q.add_task(Platform.TWITTER, ResourceType.POST, "low", TaskPriority.LOW)
        q.add_task(Platform.TWITTER, ResourceType.COMMENT, "high", TaskPriority.HIGH)

        pending = list(q.iter_pending())
        assert len(pending) == 2
        assert pending[0].resource_id == "high"  # Higher priority first


# ============================================================================
# Persistence
# ============================================================================


class TestQueuePersistence:
    """😐 Surviving restarts: because crashes are inevitable."""

    def test_save_and_load(self, tmp_path: Path) -> None:
        q = TaskQueue(max_retries=5)
        q.add_task(Platform.TWITTER, ResourceType.POST, "p1")
        q.add_task(Platform.FACEBOOK, ResourceType.COMMENT, "c1", TaskPriority.HIGH)

        save_path = tmp_path / "queue.json"
        q.save(save_path)

        loaded = TaskQueue.load(save_path)
        assert loaded.size == 2
        assert loaded._max_retries == 5

    def test_load_preserves_task_state(self, tmp_path: Path) -> None:
        q = TaskQueue()
        task = q.add_task(Platform.TWITTER, ResourceType.POST, "p1")
        q.next_task()
        q.complete_task(task.task_id)

        save_path = tmp_path / "queue.json"
        q.save(save_path)

        loaded = TaskQueue.load(save_path)
        t = loaded.get_tasks_by_status(TaskStatus.COMPLETED)
        assert len(t) == 1
        assert t[0].resource_id == "p1"

    def test_load_invalid_file(self, tmp_path: Path) -> None:
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not json")
        with pytest.raises(QueueError):
            TaskQueue.load(bad_file)

    def test_load_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(QueueError):
            TaskQueue.load(tmp_path / "missing.json")

    def test_save_creates_directory(self, tmp_path: Path) -> None:
        q = TaskQueue()
        deep_path = tmp_path / "a" / "b" / "queue.json"
        q.save(deep_path)
        assert deep_path.exists()


# ============================================================================
# Add Existing Task
# ============================================================================


class TestAddExistingTask:
    """😐 Re-adding deserialized tasks."""

    def test_add_existing(self) -> None:
        q = TaskQueue()
        task = DeletionTask(
            task_id="custom-id",
            platform=Platform.GOOGLE,
            resource_type=ResourceType.SEARCH_HISTORY,
            resource_id="history-all",
        )
        q.add_existing_task(task)
        assert q.get_task("custom-id") is task

    def test_duplicate_id_rejected(self) -> None:
        q = TaskQueue()
        task1 = DeletionTask(
            task_id="same-id",
            platform=Platform.TWITTER,
            resource_type=ResourceType.POST,
            resource_id="p1",
        )
        task2 = DeletionTask(
            task_id="same-id",
            platform=Platform.FACEBOOK,
            resource_type=ResourceType.POST,
            resource_id="p2",
        )
        q.add_existing_task(task1)
        with pytest.raises(DuplicateTaskError):
            q.add_existing_task(task2)
