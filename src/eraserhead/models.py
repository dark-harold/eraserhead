"""
😐 Scrubbing Engine: Data Models

Core data types for the digital footprint erasure system.
Tasks, results, credentials, and platform definitions.

🌑 Dark Harold: These models represent your digital footprint.
   Each one is a piece of data someone shouldn't have about you.
"""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass, field
from enum import IntEnum, StrEnum
from typing import Any


# ============================================================================
# Enums
# ============================================================================


class Platform(StrEnum):
    """Supported platforms for scrubbing."""

    FACEBOOK = "facebook"
    TWITTER = "twitter"
    INSTAGRAM = "instagram"
    LINKEDIN = "linkedin"
    GOOGLE = "google"


class ResourceType(StrEnum):
    """Types of deletable resources."""

    POST = "post"
    COMMENT = "comment"
    LIKE = "like"
    FRIEND = "friend"
    PHOTO = "photo"
    VIDEO = "video"
    MESSAGE = "message"
    PROFILE = "profile"
    SEARCH_HISTORY = "search_history"
    ACCOUNT = "account"


class TaskPriority(IntEnum):
    """Task priority levels (lower = higher priority)."""

    URGENT = 1
    HIGH = 3
    STANDARD = 5
    LOW = 7
    BACKGROUND = 9


class TaskStatus(StrEnum):
    """Task lifecycle states."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"
    VERIFIED = "verified"


class VerificationStatus(StrEnum):
    """Verification states for deletion confirmation."""

    NOT_VERIFIED = "not_verified"
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    REAPPEARED = "reappeared"


# ============================================================================
# Core Models
# ============================================================================


@dataclass
class DeletionTask:
    """
    A single deletion operation targeting one resource.

    😐 Each task represents one thing to delete from one platform.
    Simple in concept, surprisingly complex in execution.
    """

    task_id: str = field(default_factory=lambda: secrets.token_hex(8))
    platform: Platform = Platform.TWITTER
    resource_type: ResourceType = ResourceType.POST
    resource_id: str = ""
    priority: TaskPriority = TaskPriority.STANDARD
    status: TaskStatus = TaskStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    error_message: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)

    def can_retry(self) -> bool:
        """Check if task has retries remaining."""
        return self.retry_count < self.max_retries

    def mark_retry(self) -> None:
        """Increment retry counter and update status."""
        self.retry_count += 1
        self.status = TaskStatus.RETRYING
        self.updated_at = time.time()

    def mark_completed(self) -> None:
        """Mark task as completed."""
        self.status = TaskStatus.COMPLETED
        self.updated_at = time.time()

    def mark_failed(self, error: str) -> None:
        """Mark task as failed with error message."""
        self.status = TaskStatus.FAILED
        self.error_message = error
        self.updated_at = time.time()

    def mark_verified(self) -> None:
        """Mark task as verified (deletion confirmed)."""
        self.status = TaskStatus.VERIFIED
        self.updated_at = time.time()

    def to_dict(self) -> dict[str, object]:
        """Serialize to dict."""
        return {
            "task_id": self.task_id,
            "platform": self.platform,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "priority": int(self.priority),
            "status": self.status,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "error_message": self.error_message,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeletionTask:
        """Deserialize from dict."""
        return cls(
            task_id=data["task_id"],
            platform=Platform(data["platform"]),
            resource_type=ResourceType(data["resource_type"]),
            resource_id=data["resource_id"],
            priority=TaskPriority(data["priority"]),
            status=TaskStatus(data["status"]),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
            created_at=data.get("created_at", 0.0),
            updated_at=data.get("updated_at", 0.0),
            error_message=data.get("error_message"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class DeletionResult:
    """
    Result of a deletion operation.

    😐 Contains success/failure, proof, and timing data.
    🌑 Proof is critical — platforms lie about deletion.
    """

    task_id: str
    success: bool
    verified: bool = False
    verification_status: VerificationStatus = VerificationStatus.NOT_VERIFIED
    error_message: str | None = None
    proof: dict[str, str] | str = field(default_factory=dict)
    duration_seconds: float = 0.0
    completed_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, object]:
        """Serialize to dict."""
        return {
            "task_id": self.task_id,
            "success": self.success,
            "verified": self.verified,
            "verification_status": self.verification_status,
            "error_message": self.error_message,
            "proof": self.proof,
            "duration_seconds": self.duration_seconds,
            "completed_at": self.completed_at,
        }


@dataclass
class PlatformCredentials:
    """
    Credentials for authenticating with a platform.

    😐 These are the keys to people's accounts.
    🌑 NEVER store in plaintext. EVER. Use the vault.
    """

    platform: Platform
    username: str
    auth_token: str = ""
    api_key: str = ""
    api_secret: str = ""
    extra: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Serialize to dict (for encrypted storage)."""
        return {
            "platform": self.platform,
            "username": self.username,
            "auth_token": self.auth_token,
            "api_key": self.api_key,
            "api_secret": self.api_secret,
            "extra": self.extra,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PlatformCredentials:
        """Deserialize from dict."""
        return cls(
            platform=Platform(data["platform"]),
            username=data["username"],
            auth_token=data.get("auth_token", ""),
            api_key=data.get("api_key", ""),
            api_secret=data.get("api_secret", ""),
            extra=data.get("extra", {}),
        )


@dataclass
class ScrubProfile:
    """
    User profile defining what to scrub across platforms.

    😐 One profile per human. Multiple platforms per human.
    """

    profile_id: str = field(default_factory=lambda: secrets.token_hex(8))
    name: str = ""
    platforms: dict[Platform, str] = field(default_factory=dict)  # platform → username
    resource_types: set[ResourceType] = field(
        default_factory=lambda: {ResourceType.POST, ResourceType.COMMENT, ResourceType.LIKE}
    )
    dry_run: bool = False
    created_at: float = field(default_factory=time.time)


@dataclass
class ScrubProgress:
    """
    Progress tracking for an active scrubbing operation.

    😐 Numbers that tell you how much of your digital footprint remains.
    """

    platform: Platform
    total_tasks: int = 0
    completed: int = 0
    failed: int = 0
    verified: int = 0
    pending: int = 0
    started_at: float = field(default_factory=time.time)

    @property
    def percent_complete(self) -> float:
        """Completion percentage."""
        if self.total_tasks == 0:
            return 0.0
        return (self.completed + self.verified) / self.total_tasks * 100

    @property
    def is_done(self) -> bool:
        """All tasks finished (completed or failed)."""
        return (self.completed + self.failed + self.verified) >= self.total_tasks
