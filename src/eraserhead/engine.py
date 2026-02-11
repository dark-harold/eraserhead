"""
😐 Scrubbing Engine: Core Orchestrator

Coordinates queue, adapters, and vault to process deletion tasks.
Supports dry-run mode, progress tracking, and crash recovery.

🌑 Dark Harold: This is the brain of the operation. If it fails,
   Harold's digital footprint lives forever. No pressure.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

from eraserhead.adapters import PlatformAdapter
from eraserhead.adapters.platforms import get_adapter, SimulatedPlatformData
from eraserhead.models import (
    DeletionResult,
    DeletionTask,
    Platform,
    PlatformCredentials,
    ResourceType,
    ScrubProgress,
    TaskPriority,
    TaskStatus,
)
from eraserhead.queue import TaskQueue, QueueEmptyError
from eraserhead.vault import CredentialVault


logger = logging.getLogger(__name__)


# ============================================================================
# Engine Configuration
# ============================================================================


@dataclass
class EngineConfig:
    """Scrubbing engine configuration."""

    dry_run: bool = False
    max_retries: int = 3
    verify_after_delete: bool = True
    queue_save_path: Path | None = None


# ============================================================================
# Scrubbing Engine
# ============================================================================


class ScrubEngine:
    """
    😐 The main scrubbing orchestrator.

    Coordinates:
    - TaskQueue: priority-ordered deletion queue
    - PlatformAdapters: platform-specific API interactions
    - CredentialVault: secure credential storage
    - Progress tracking: per-platform statistics

    Usage:
        engine = ScrubEngine(config)
        engine.register_adapter(twitter_adapter)
        engine.add_tasks(platform, resource_type, resource_ids)
        results = await engine.run()

    🌑 All roads lead to deletion. Or failure. Usually both.
    """

    def __init__(self, config: EngineConfig | None = None) -> None:
        self._config = config or EngineConfig()
        self._queue = TaskQueue(max_retries=self._config.max_retries)
        self._adapters: dict[Platform, PlatformAdapter] = {}
        self._results: list[DeletionResult] = []
        self._running = False

    @property
    def queue(self) -> TaskQueue:
        """Access the task queue."""
        return self._queue

    @property
    def results(self) -> list[DeletionResult]:
        """Completed deletion results."""
        return list(self._results)

    @property
    def is_running(self) -> bool:
        """Check if engine is currently processing."""
        return self._running

    # ========================================================================
    # Setup
    # ========================================================================

    def register_adapter(self, adapter: PlatformAdapter) -> None:
        """
        Register a platform adapter.

        Only one adapter per platform.
        """
        self._adapters[adapter.platform] = adapter

    def add_tasks(
        self,
        platform: Platform,
        resource_type: ResourceType,
        resource_ids: list[str],
        priority: TaskPriority = TaskPriority.STANDARD,
    ) -> list[DeletionTask]:
        """
        Batch-add deletion tasks.

        Returns list of created tasks.
        """
        tasks = []
        for rid in resource_ids:
            try:
                task = self._queue.add_task(
                    platform=platform,
                    resource_type=resource_type,
                    resource_id=rid,
                    priority=priority,
                )
                tasks.append(task)
            except Exception as e:
                logger.warning("Failed to add task %s: %s", rid, e)
        return tasks

    # ========================================================================
    # Execution
    # ========================================================================

    async def run(self) -> list[DeletionResult]:
        """
        Process all pending tasks in the queue.

        Returns list of DeletionResults.

        😐 This is where the magic happens. And by magic,
        Harold means "systematic resource elimination."
        """
        self._running = True
        self._results.clear()

        try:
            while True:
                try:
                    task = self._queue.next_task()
                except QueueEmptyError:
                    break

                result = await self._process_task(task)
                self._results.append(result)

                # Save queue state periodically
                if self._config.queue_save_path:
                    self._queue.save(self._config.queue_save_path)

        finally:
            self._running = False

        return list(self._results)

    async def process_one(self) -> DeletionResult | None:
        """
        Process a single task from the queue.

        Returns result or None if queue is empty.
        """
        try:
            task = self._queue.next_task()
        except QueueEmptyError:
            return None

        result = await self._process_task(task)
        self._results.append(result)
        return result

    async def _process_task(self, task: DeletionTask) -> DeletionResult:
        """Process a single deletion task."""
        adapter = self._adapters.get(task.platform)

        if adapter is None:
            result = DeletionResult(
                task_id=task.task_id,
                success=False,
                error_message=f"No adapter for platform: {task.platform}",
            )
            self._queue.fail_task(task.task_id, result.error_message)
            return result

        if not adapter.is_authenticated:
            result = DeletionResult(
                task_id=task.task_id,
                success=False,
                error_message=f"Adapter not authenticated: {task.platform}",
            )
            self._queue.fail_task(task.task_id, result.error_message)
            return result

        # Dry run: report what would be deleted
        if self._config.dry_run:
            result = DeletionResult(
                task_id=task.task_id,
                success=True,
                proof=f"dry_run:{task.platform}:{task.resource_type}:{task.resource_id}",
            )
            self._queue.complete_task(task.task_id)
            return result

        # Execute deletion
        result = await adapter.delete_resource(task)

        if result.success:
            # Verify if configured
            if self._config.verify_after_delete:
                verification = await adapter.verify_deletion(task)
                result.verified = True
                result.verification_status = verification

            self._queue.complete_task(task.task_id)
        else:
            will_retry = self._queue.fail_task(
                task.task_id, result.error_message or "Unknown error"
            )
            if will_retry:
                logger.info(
                    "Task %s will retry (attempt %d)",
                    task.task_id,
                    task.retry_count,
                )

        return result

    # ========================================================================
    # Progress
    # ========================================================================

    def get_progress(self, platform: Platform | None = None) -> list[ScrubProgress]:
        """
        Get progress for one or all platforms.

        Returns list of ScrubProgress objects.
        """
        platforms = [platform] if platform else list(self._adapters.keys())
        progress_list = []

        for p in platforms:
            tasks = self._queue.get_tasks_by_platform(p)
            if not tasks:
                continue

            completed = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
            failed = sum(1 for t in tasks if t.status == TaskStatus.FAILED)
            verified = sum(1 for t in tasks if t.status == TaskStatus.VERIFIED)
            pending = sum(
                1 for t in tasks
                if t.status in (TaskStatus.PENDING, TaskStatus.RETRYING, TaskStatus.RUNNING)
            )

            progress_list.append(ScrubProgress(
                platform=p,
                total_tasks=len(tasks),
                completed=completed,
                failed=failed,
                verified=verified,
                pending=pending,
            ))

        return progress_list
