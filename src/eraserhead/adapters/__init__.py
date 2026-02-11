"""
😐 Scrubbing Engine: Platform Adapter Base Class

Abstract interface for platform-specific deletion operations.
Each platform implements authenticate, delete, verify, and list_resources.

🌑 Dark Harold: Every platform's API is a unique snowflake of pain.
   The adapter pattern hides this behind a uniform interface,
   because Harold believes in consistent suffering.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum

from eraserhead.models import (
    DeletionResult,
    DeletionTask,
    Platform,
    PlatformCredentials,
    ResourceType,
    VerificationStatus,
)


# ============================================================================
# Adapter Status
# ============================================================================


class AdapterStatus(StrEnum):
    """Current state of a platform adapter."""

    DISCONNECTED = "disconnected"
    AUTHENTICATED = "authenticated"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"


# ============================================================================
# Adapter Stats
# ============================================================================


@dataclass
class AdapterStats:
    """Adapter operational statistics."""

    total_requests: int = 0
    successful_deletions: int = 0
    failed_deletions: int = 0
    verifications: int = 0
    rate_limit_hits: int = 0
    last_request_time: float = 0.0

    @property
    def success_rate(self) -> float:
        """Deletion success rate (0.0-1.0)."""
        total = self.successful_deletions + self.failed_deletions
        if total == 0:
            return 0.0
        return self.successful_deletions / total


# ============================================================================
# Rate Limiter
# ============================================================================


@dataclass
class RateLimitConfig:
    """Rate limiting configuration per platform."""

    requests_per_minute: int = 30
    burst_size: int = 5
    cooldown_seconds: float = 60.0


class RateLimiter:
    """
    😐 Token bucket rate limiter.

    Prevents Harold from getting banned by overzealous scrubbing.
    """

    def __init__(self, config: RateLimitConfig) -> None:
        self._config = config
        self._tokens = float(config.burst_size)
        self._last_refill = time.monotonic()

    def can_proceed(self) -> bool:
        """Check if a request is allowed."""
        self._refill()
        return self._tokens >= 1.0

    def consume(self) -> bool:
        """
        Try to consume a token. Returns True if allowed.
        """
        self._refill()
        if self._tokens >= 1.0:
            self._tokens -= 1.0
            return True
        return False

    def time_until_available(self) -> float:
        """Seconds until next token available."""
        self._refill()
        if self._tokens >= 1.0:
            return 0.0
        tokens_needed = 1.0 - self._tokens
        rate = self._config.requests_per_minute / 60.0
        if rate == 0:
            return float("inf")
        return tokens_needed / rate

    def _refill(self) -> None:
        """Add tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        rate = self._config.requests_per_minute / 60.0
        self._tokens = min(
            float(self._config.burst_size),
            self._tokens + elapsed * rate,
        )
        self._last_refill = now


# ============================================================================
# Abstract Platform Adapter
# ============================================================================


class PlatformAdapter(ABC):
    """
    😐 Abstract base for platform-specific operations.

    Subclasses implement the actual API interactions for each platform.
    The adapter handles authentication, rate limiting, and statistics.

    Lifecycle:
        adapter = TwitterAdapter()
        await adapter.authenticate(credentials)
        result = await adapter.delete_resource(task)
        verified = await adapter.verify_deletion(task)
        await adapter.disconnect()

    🌑 Every platform has its own rate limits, error codes,
    and undocumented edge cases. Adapters absorb this pain.
    """

    def __init__(
        self,
        platform: Platform,
        rate_limit: RateLimitConfig | None = None,
    ) -> None:
        self._platform = platform
        self._status = AdapterStatus.DISCONNECTED
        self._stats = AdapterStats()
        self._rate_limiter = RateLimiter(rate_limit or RateLimitConfig())
        self._credentials: PlatformCredentials | None = None

    @property
    def platform(self) -> Platform:
        """Which platform this adapter handles."""
        return self._platform

    @property
    def status(self) -> AdapterStatus:
        """Current adapter status."""
        return self._status

    @property
    def stats(self) -> AdapterStats:
        """Adapter statistics."""
        return self._stats

    @property
    def is_authenticated(self) -> bool:
        """Check if adapter is authenticated."""
        return self._status == AdapterStatus.AUTHENTICATED

    @property
    def supported_resource_types(self) -> set[ResourceType]:
        """Resource types this adapter can handle."""
        return self._get_supported_types()

    # ========================================================================
    # Public API
    # ========================================================================

    async def authenticate(self, credentials: PlatformCredentials) -> bool:
        """
        Authenticate with the platform.

        Returns True on success.
        """
        if credentials.platform != self._platform:
            return False

        self._credentials = credentials
        success = await self._do_authenticate(credentials)

        if success:
            self._status = AdapterStatus.AUTHENTICATED
        else:
            self._status = AdapterStatus.ERROR

        return success

    async def delete_resource(self, task: DeletionTask) -> DeletionResult:
        """
        Delete a resource on the platform.

        Handles rate limiting and statistics tracking.
        """
        if not self.is_authenticated:
            return DeletionResult(
                task_id=task.task_id,
                success=False,
                error_message="Adapter not authenticated",
            )

        if not self._rate_limiter.consume():
            self._stats.rate_limit_hits += 1
            self._status = AdapterStatus.RATE_LIMITED
            return DeletionResult(
                task_id=task.task_id,
                success=False,
                error_message="Rate limited",
            )

        self._stats.total_requests += 1
        self._stats.last_request_time = time.time()

        start = time.monotonic()
        try:
            result = await self._do_delete(task)
        except Exception as e:
            # 🌑 Never let an adapter crash the engine
            result = DeletionResult(
                task_id=task.task_id,
                success=False,
                error_message=f"Adapter error: {e}",
            )

        result.duration_seconds = time.monotonic() - start

        if result.success:
            self._stats.successful_deletions += 1
            self._status = AdapterStatus.AUTHENTICATED  # Clear rate limit
        else:
            self._stats.failed_deletions += 1

        return result

    async def verify_deletion(self, task: DeletionTask) -> VerificationStatus:
        """
        Verify that a deletion actually occurred.

        Returns verification status.
        """
        if not self.is_authenticated:
            return VerificationStatus.NOT_VERIFIED

        self._stats.verifications += 1
        try:
            return await self._do_verify(task)
        except Exception:
            return VerificationStatus.NOT_VERIFIED

    async def list_resources(
        self, resource_type: ResourceType
    ) -> list[dict[str, str]]:
        """
        List resources of a given type on the platform.

        Returns list of resource metadata dicts.
        """
        if not self.is_authenticated:
            return []

        return await self._do_list_resources(resource_type)

    async def disconnect(self) -> None:
        """Disconnect from the platform."""
        await self._do_disconnect()
        self._status = AdapterStatus.DISCONNECTED
        self._credentials = None

    # ========================================================================
    # Abstract Methods (subclasses implement these)
    # ========================================================================

    @abstractmethod
    async def _do_authenticate(
        self, credentials: PlatformCredentials
    ) -> bool:
        """Platform-specific authentication."""
        ...

    @abstractmethod
    async def _do_delete(self, task: DeletionTask) -> DeletionResult:
        """Platform-specific deletion."""
        ...

    @abstractmethod
    async def _do_verify(self, task: DeletionTask) -> VerificationStatus:
        """Platform-specific verification."""
        ...

    @abstractmethod
    async def _do_list_resources(
        self, resource_type: ResourceType
    ) -> list[dict[str, str]]:
        """Platform-specific resource listing."""
        ...

    @abstractmethod
    def _get_supported_types(self) -> set[ResourceType]:
        """Return supported resource types for this platform."""
        ...

    async def _do_disconnect(self) -> None:
        """Platform-specific cleanup. Override if needed."""
        # 😐 Default no-op — override if your adapter needs cleanup
