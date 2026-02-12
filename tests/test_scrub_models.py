"""
😐 Tests for scrubbing engine data models.

Tests task lifecycle, serialization, progress tracking,
and enum definitions.
"""

from __future__ import annotations

import time

from eraserhead.models import (
    DeletionResult,
    DeletionTask,
    Platform,
    PlatformCredentials,
    ResourceType,
    ScrubProfile,
    ScrubProgress,
    TaskPriority,
    TaskStatus,
)


class TestDeletionTask:
    """😐 Testing deletion task lifecycle."""

    def test_default_creation(self) -> None:
        """Task has sensible defaults."""
        task = DeletionTask()
        assert len(task.task_id) == 16  # hex(8) = 16 chars
        assert task.status == TaskStatus.PENDING
        assert task.priority == TaskPriority.STANDARD
        assert task.retry_count == 0

    def test_can_retry(self) -> None:
        """Retry check respects max_retries."""
        task = DeletionTask(max_retries=3)
        assert task.can_retry()
        task.retry_count = 3
        assert not task.can_retry()

    def test_mark_retry(self) -> None:
        """mark_retry increments counter and updates status."""
        task = DeletionTask()
        task.mark_retry()
        assert task.retry_count == 1
        assert task.status == TaskStatus.RETRYING

    def test_mark_completed(self) -> None:
        """mark_completed updates status."""
        task = DeletionTask()
        task.mark_completed()
        assert task.status == TaskStatus.COMPLETED

    def test_mark_failed(self) -> None:
        """mark_failed stores error message."""
        task = DeletionTask()
        task.mark_failed("API rate limited")
        assert task.status == TaskStatus.FAILED
        assert task.error_message == "API rate limited"

    def test_mark_verified(self) -> None:
        """mark_verified updates status."""
        task = DeletionTask()
        task.mark_verified()
        assert task.status == TaskStatus.VERIFIED

    def test_serialization_roundtrip(self) -> None:
        """Serialize and deserialize preserves all fields."""
        task = DeletionTask(
            platform=Platform.FACEBOOK,
            resource_type=ResourceType.POST,
            resource_id="post_12345",
            priority=TaskPriority.URGENT,
            metadata={"url": "https://facebook.com/post/12345"},
        )
        data = task.to_dict()
        restored = DeletionTask.from_dict(data)

        assert restored.task_id == task.task_id
        assert restored.platform == Platform.FACEBOOK
        assert restored.resource_type == ResourceType.POST
        assert restored.resource_id == "post_12345"
        assert restored.priority == TaskPriority.URGENT
        assert restored.metadata == {"url": "https://facebook.com/post/12345"}

    def test_updated_at_changes(self) -> None:
        """Actions update the timestamp."""
        task = DeletionTask()
        original = task.updated_at
        time.sleep(0.01)
        task.mark_completed()
        assert task.updated_at >= original


class TestDeletionResult:
    """Tests for deletion results."""

    def test_success_result(self) -> None:
        """Successful result."""
        result = DeletionResult(
            task_id="abc123",
            success=True,
            proof={"api_response": "200 OK"},
        )
        assert result.success
        assert result.proof["api_response"] == "200 OK"

    def test_failure_result(self) -> None:
        """Failed result with error."""
        result = DeletionResult(
            task_id="abc123",
            success=False,
            error_message="Rate limited",
        )
        assert not result.success
        assert result.error_message == "Rate limited"

    def test_serialization(self) -> None:
        """Result serializes to dict."""
        result = DeletionResult(task_id="abc", success=True)
        data = result.to_dict()
        assert data["task_id"] == "abc"
        assert data["success"] is True


class TestPlatformCredentials:
    """🌑 Testing credential handling. Carefully."""

    def test_credential_creation(self) -> None:
        """Create credentials with all fields."""
        creds = PlatformCredentials(
            platform=Platform.TWITTER,
            username="harold",
            auth_token="secret_token",
            api_key="key123",
        )
        assert creds.platform == Platform.TWITTER
        assert creds.username == "harold"

    def test_credential_roundtrip(self) -> None:
        """Serialize and deserialize credentials."""
        creds = PlatformCredentials(
            platform=Platform.INSTAGRAM,
            username="real_harold",
            auth_token="bearer_xyz",
        )
        data = creds.to_dict()
        restored = PlatformCredentials.from_dict(data)
        assert restored.platform == Platform.INSTAGRAM
        assert restored.auth_token == "bearer_xyz"


class TestScrubProgress:
    """Tests for progress tracking."""

    def test_percent_complete(self) -> None:
        """Percentage calculation."""
        progress = ScrubProgress(
            platform=Platform.FACEBOOK,
            total_tasks=100,
            completed=50,
            verified=20,
        )
        assert progress.percent_complete == 70.0

    def test_percent_complete_empty(self) -> None:
        """Zero tasks = 0%."""
        progress = ScrubProgress(platform=Platform.TWITTER, total_tasks=0)
        assert progress.percent_complete == 0.0

    def test_is_done(self) -> None:
        """Done when all tasks completed or failed."""
        progress = ScrubProgress(
            platform=Platform.GOOGLE,
            total_tasks=10,
            completed=7,
            failed=3,
        )
        assert progress.is_done

    def test_not_done(self) -> None:
        """Not done when tasks remain."""
        progress = ScrubProgress(
            platform=Platform.LINKEDIN,
            total_tasks=10,
            completed=5,
            failed=2,
        )
        assert not progress.is_done


class TestEnums:
    """Verify enum values are sensible."""

    def test_platforms(self) -> None:
        """All expected platforms defined."""
        assert len(Platform) >= 5

    def test_resource_types(self) -> None:
        """Core resource types exist."""
        assert ResourceType.POST in ResourceType
        assert ResourceType.COMMENT in ResourceType
        assert ResourceType.ACCOUNT in ResourceType

    def test_priority_ordering(self) -> None:
        """Lower number = higher priority."""
        assert TaskPriority.URGENT < TaskPriority.STANDARD
        assert TaskPriority.STANDARD < TaskPriority.BACKGROUND

    def test_profile_defaults(self) -> None:
        """ScrubProfile has sensible defaults."""
        profile = ScrubProfile(name="Harold")
        assert profile.name == "Harold"
        assert ResourceType.POST in profile.resource_types
        assert not profile.dry_run
