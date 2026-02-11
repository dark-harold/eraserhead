"""
😐 Scrubbing Engine: Verification Service

Post-deletion verification to confirm resources are truly gone.
Tracks verification state and detects reappearance.

🌑 Dark Harold: Deletion without verification is an act of faith.
   Harold does not do faith. Harold does verification scans.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from eraserhead.adapters import PlatformAdapter
from eraserhead.models import (
    DeletionTask,
    Platform,
    TaskStatus,
    VerificationStatus,
)


logger = logging.getLogger(__name__)


# ============================================================================
# Verification Result
# ============================================================================


@dataclass
class VerificationResult:
    """Result of a single verification check."""

    task_id: str
    status: VerificationStatus
    checked_at: float = field(default_factory=time.time)
    attempt: int = 1
    error: str | None = None


# ============================================================================
# Verification Service
# ============================================================================


class VerificationService:
    """
    😐 Post-deletion verification service.

    Verifies that deleted resources are actually gone.
    Can run single checks or batch verification scans.

    Usage:
        service = VerificationService()
        service.register_adapter(twitter_adapter)
        result = await service.verify(task)
        report = await service.scan(completed_tasks)

    🌑 "Deleted" doesn't mean "gone." Platforms cache, CDNs cache,
    and Harold has trust issues about all of it.
    """

    def __init__(self, max_attempts: int = 3) -> None:
        self._adapters: dict[Platform, PlatformAdapter] = {}
        self._max_attempts = max_attempts
        self._history: list[VerificationResult] = []

    @property
    def history(self) -> list[VerificationResult]:
        """All verification results."""
        return list(self._history)

    def register_adapter(self, adapter: PlatformAdapter) -> None:
        """Register an adapter for verification."""
        self._adapters[adapter.platform] = adapter

    async def verify(self, task: DeletionTask) -> VerificationResult:
        """
        Verify a single deletion task.

        Returns verification result.
        """
        adapter = self._adapters.get(task.platform)
        if adapter is None:
            result = VerificationResult(
                task_id=task.task_id,
                status=VerificationStatus.NOT_VERIFIED,
                error=f"No adapter for {task.platform}",
            )
            self._history.append(result)
            return result

        if not adapter.is_authenticated:
            result = VerificationResult(
                task_id=task.task_id,
                status=VerificationStatus.NOT_VERIFIED,
                error="Adapter not authenticated",
            )
            self._history.append(result)
            return result

        try:
            status = await adapter.verify_deletion(task)
        except Exception as e:
            status = VerificationStatus.NOT_VERIFIED
            result = VerificationResult(
                task_id=task.task_id,
                status=status,
                error=str(e),
            )
            self._history.append(result)
            return result

        result = VerificationResult(
            task_id=task.task_id,
            status=status,
        )
        self._history.append(result)

        # Update task status
        if status == VerificationStatus.CONFIRMED:
            task.mark_verified()

        return result

    async def scan(self, tasks: list[DeletionTask]) -> list[VerificationResult]:
        """
        Batch verification scan.

        Verifies all provided tasks and returns results.
        Only verifies tasks that are COMPLETED (not already verified).
        """
        results = []
        for task in tasks:
            if task.status not in (TaskStatus.COMPLETED, TaskStatus.VERIFIED):
                continue
            result = await self.verify(task)
            results.append(result)
        return results

    def get_stats(self) -> dict[str, int]:
        """
        Verification statistics.

        Returns counts of each verification status.
        """
        stats: dict[str, int] = {
            "total": 0,
            "confirmed": 0,
            "failed": 0,
            "reappeared": 0,
            "not_verified": 0,
        }
        for r in self._history:
            stats["total"] += 1
            match r.status:
                case VerificationStatus.CONFIRMED:
                    stats["confirmed"] += 1
                case VerificationStatus.FAILED:
                    stats["failed"] += 1
                case VerificationStatus.REAPPEARED:
                    stats["reappeared"] += 1
                case VerificationStatus.NOT_VERIFIED:
                    stats["not_verified"] += 1
        return stats
