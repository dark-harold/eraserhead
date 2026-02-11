"""
😐 Scrubbing Engine: Task Queue & Scheduling

Priority-based task queue with retry logic and exponential backoff.
Tasks are processed in priority order with configurable concurrency.

🌑 Dark Harold: A queue is just a list of things that can fail
   in creative new ways. We handle:
   - Priority inversion (high-priority tasks jump the line)
   - Retry storms (exponential backoff with jitter)
   - Duplicate detection (don't delete the same post twice)
   - Queue persistence (survive restarts)
"""

from __future__ import annotations

import json
import secrets
import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from eraserhead.models import (
    DeletionTask,
    Platform,
    ResourceType,
    TaskPriority,
    TaskStatus,
)


# ============================================================================
# Constants
# ============================================================================

MAX_RETRY_DELAY_SECONDS = 300.0  # 5 minute cap on backoff
BASE_RETRY_DELAY_SECONDS = 2.0  # Start at 2 seconds
JITTER_FACTOR = 0.5  # ±50% of delay
DEFAULT_MAX_RETRIES = 3


# ============================================================================
# Exceptions
# ============================================================================


class QueueError(Exception):
    """Base queue error."""


class DuplicateTaskError(QueueError):
    """Task with same ID or resource already queued."""


class QueueEmptyError(QueueError):
    """No tasks available for processing."""


# ============================================================================
# Queue Statistics
# ============================================================================


@dataclass
class QueueStats:
    """Current queue state summary."""

    total: int = 0
    pending: int = 0
    running: int = 0
    completed: int = 0
    failed: int = 0
    retrying: int = 0
    cancelled: int = 0

    @property
    def active(self) -> int:
        """Tasks that aren't done yet."""
        return self.pending + self.running + self.retrying


# ============================================================================
# Task Queue
# ============================================================================


class TaskQueue:
    """
    😐 Priority-based deletion task queue.

    Tasks are ordered by priority (lower number = higher priority).
    Within same priority, FIFO ordering.

    Features:
    - Priority ordering with TaskPriority enum
    - Retry with exponential backoff + jitter
    - Duplicate resource detection
    - JSON persistence for crash recovery
    - Task lifecycle management

    🌑 The queue never forgets a failure. Harold relates.
    """

    def __init__(self, max_retries: int = DEFAULT_MAX_RETRIES) -> None:
        self._tasks: dict[str, DeletionTask] = {}
        self._max_retries = max_retries
        # Track platform:resource_type:resource_id to prevent duplicates
        self._resource_index: set[str] = set()

    @property
    def size(self) -> int:
        """Total number of tasks in queue."""
        return len(self._tasks)

    def add_task(
        self,
        platform: Platform,
        resource_type: ResourceType,
        resource_id: str,
        priority: TaskPriority = TaskPriority.STANDARD,
        metadata: dict[str, str] | None = None,
    ) -> DeletionTask:
        """
        Add a new deletion task to the queue.

        Args:
            platform: Target platform
            resource_type: Type of resource to delete
            resource_id: Platform-specific resource identifier
            priority: Task priority (default: NORMAL)
            metadata: Optional extra data for the adapter

        Returns:
            Created task

        Raises:
            DuplicateTaskError: If same resource already queued
        """
        resource_key = f"{platform}:{resource_type}:{resource_id}"
        if resource_key in self._resource_index:
            raise DuplicateTaskError(f"Resource already queued: {resource_key}")

        task = DeletionTask(
            task_id=secrets.token_hex(8),
            platform=platform,
            resource_type=resource_type,
            resource_id=resource_id,
            priority=priority,
            max_retries=self._max_retries,
            metadata=metadata or {},
        )

        self._tasks[task.task_id] = task
        self._resource_index.add(resource_key)
        return task

    def add_existing_task(self, task: DeletionTask) -> None:
        """
        Add a pre-built task (e.g., from persistence).

        Raises:
            DuplicateTaskError: If task ID or resource already exists
        """
        if task.task_id in self._tasks:
            raise DuplicateTaskError(f"Task ID already exists: {task.task_id}")

        resource_key = f"{task.platform}:{task.resource_type}:{task.resource_id}"
        if resource_key in self._resource_index:
            raise DuplicateTaskError(f"Resource already queued: {resource_key}")

        self._tasks[task.task_id] = task
        self._resource_index.add(resource_key)

    def get_task(self, task_id: str) -> DeletionTask | None:
        """Get task by ID."""
        return self._tasks.get(task_id)

    def next_task(self) -> DeletionTask:
        """
        Get next task to process (highest priority pending).

        Returns:
            Next task, marked as RUNNING

        Raises:
            QueueEmptyError: If no pending tasks
        """
        pending = [
            t for t in self._tasks.values() if t.status in (TaskStatus.PENDING, TaskStatus.RETRYING)
        ]

        if not pending:
            raise QueueEmptyError("No tasks available")

        # Sort by priority (lower = higher priority), then by created_at
        pending.sort(key=lambda t: (t.priority, t.created_at))

        task = pending[0]
        task.status = TaskStatus.RUNNING
        task.updated_at = time.time()
        return task

    def complete_task(self, task_id: str) -> None:
        """Mark task as completed."""
        task = self._require_task(task_id)
        task.mark_completed()

    def fail_task(self, task_id: str, error: str) -> bool:
        """
        Mark task as failed. Retries if possible.

        Returns:
            True if task will retry, False if permanently failed
        """
        task = self._require_task(task_id)
        if task.can_retry():
            task.error_message = error
            task.mark_retry()
            return True
        task.mark_failed(error)
        return False

    def cancel_task(self, task_id: str) -> None:
        """Cancel a task."""
        task = self._require_task(task_id)
        task.status = TaskStatus.CANCELLED
        task.updated_at = time.time()

    def get_retry_delay(self, task: DeletionTask) -> float:
        """
        Calculate retry delay with exponential backoff + jitter.

        😐 Exponential backoff: because hammering a failing API
        with requests is how you get rate-limited AND banned.
        """
        base = BASE_RETRY_DELAY_SECONDS * (2 ** (task.retry_count - 1))
        capped = min(base, MAX_RETRY_DELAY_SECONDS)

        # Add jitter: ±50%
        jitter_range = capped * JITTER_FACTOR
        jitter = (secrets.randbelow(1000) / 1000.0 - 0.5) * 2 * jitter_range
        return max(0.1, float(capped + jitter))

    def get_stats(self) -> QueueStats:
        """Get current queue statistics."""
        stats = QueueStats()
        for task in self._tasks.values():
            stats.total += 1
            match task.status:
                case TaskStatus.PENDING:
                    stats.pending += 1
                case TaskStatus.RUNNING:
                    stats.running += 1
                case TaskStatus.COMPLETED:
                    stats.completed += 1
                case TaskStatus.FAILED:
                    stats.failed += 1
                case TaskStatus.RETRYING:
                    stats.retrying += 1
                case TaskStatus.CANCELLED:
                    stats.cancelled += 1
        return stats

    def get_tasks_by_platform(self, platform: Platform) -> list[DeletionTask]:
        """Get all tasks for a specific platform."""
        return [t for t in self._tasks.values() if t.platform == platform]

    def get_tasks_by_status(self, status: TaskStatus) -> list[DeletionTask]:
        """Get all tasks with a specific status."""
        return [t for t in self._tasks.values() if t.status == status]

    def iter_pending(self) -> Iterator[DeletionTask]:
        """Iterate pending tasks in priority order."""
        pending = [
            t for t in self._tasks.values() if t.status in (TaskStatus.PENDING, TaskStatus.RETRYING)
        ]
        pending.sort(key=lambda t: (t.priority, t.created_at))
        yield from pending

    # ========================================================================
    # Persistence
    # ========================================================================

    def save(self, path: Path) -> None:
        """
        Save queue state to JSON file.

        😐 Not encrypted — contains task metadata, not credentials.
        Credentials live in the vault where they belong.
        """
        data = {
            "version": 1,
            "max_retries": self._max_retries,
            "tasks": [t.to_dict() for t in self._tasks.values()],
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2))

    @classmethod
    def load(cls, path: Path) -> TaskQueue:
        """
        Load queue state from JSON file.

        Raises:
            QueueError: If file is invalid
        """
        try:
            data = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError) as e:
            raise QueueError(f"Cannot load queue: {e}") from e

        max_retries = data.get("max_retries", DEFAULT_MAX_RETRIES)
        queue = cls(max_retries=max_retries)

        for task_data in data.get("tasks", []):
            task = DeletionTask.from_dict(task_data)
            queue.add_existing_task(task)

        return queue

    # ========================================================================
    # Internal
    # ========================================================================

    def _require_task(self, task_id: str) -> DeletionTask:
        """Get task or raise."""
        task = self._tasks.get(task_id)
        if task is None:
            raise QueueError(f"Task not found: {task_id}")
        return task
