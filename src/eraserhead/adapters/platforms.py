"""
😐 Platform Adapters: Twitter, Facebook, Instagram

Mock implementations for MVP. These simulate API interactions
without making real network calls.

🌑 Dark Harold: Real platform APIs are worse. These mocks are
   the best-case scenario. Production will be pain.

📺 In a future where these become real adapters, all requests
   will route through Anemochory for anonymization. For now,
   we verify the interface works.
"""

from __future__ import annotations

import time

from eraserhead.adapters import (
    PlatformAdapter,
    RateLimitConfig,
)
from eraserhead.models import (
    DeletionResult,
    DeletionTask,
    Platform,
    PlatformCredentials,
    ResourceType,
    VerificationStatus,
)


# ============================================================================
# Simulated Data Store (shared across test adapters)
# ============================================================================


class SimulatedPlatformData:
    """
    😐 In-memory data store simulating a platform's backend.

    Resources exist here until deleted. Verification checks
    whether the resource still exists.
    """

    def __init__(self) -> None:
        # Mapping of resource_type -> resource_id -> metadata
        self._resources: dict[ResourceType, dict[str, dict[str, str]]] = {}

    def add_resource(
        self, resource_type: ResourceType, resource_id: str, metadata: dict[str, str] | None = None
    ) -> None:
        """Simulate a resource existing on the platform."""
        if resource_type not in self._resources:
            self._resources[resource_type] = {}
        self._resources[resource_type][resource_id] = metadata or {
            "id": resource_id,
            "created_at": str(time.time()),
        }

    def has_resource(self, resource_type: ResourceType, resource_id: str) -> bool:
        """Check if resource exists."""
        return resource_id in self._resources.get(resource_type, {})

    def delete_resource(self, resource_type: ResourceType, resource_id: str) -> bool:
        """Delete a resource. Returns True if it existed."""
        resources = self._resources.get(resource_type, {})
        if resource_id in resources:
            del resources[resource_id]
            return True
        return False

    def list_resources(self, resource_type: ResourceType) -> list[dict[str, str]]:
        """List all resources of a type."""
        return list(self._resources.get(resource_type, {}).values())


# ============================================================================
# Twitter Adapter
# ============================================================================


class TwitterAdapter(PlatformAdapter):
    """
    😐 Twitter/X adapter. Simulates API v2 interactions.

    📺 Twitter's API has been through more rewrites than Harold's
    smile during a photoshoot. This adapter abstracts the chaos.

    Supported: POST, COMMENT, LIKE, FRIEND (follow)
    """

    def __init__(
        self,
        simulated_data: SimulatedPlatformData | None = None,
        rate_limit: RateLimitConfig | None = None,
    ) -> None:
        super().__init__(
            platform=Platform.TWITTER,
            rate_limit=rate_limit or RateLimitConfig(requests_per_minute=60),
        )
        self._data = simulated_data or SimulatedPlatformData()

    def _get_supported_types(self) -> set[ResourceType]:
        return {
            ResourceType.POST,
            ResourceType.COMMENT,
            ResourceType.LIKE,
            ResourceType.FRIEND,
        }

    async def _do_authenticate(self, credentials: PlatformCredentials) -> bool:
        # 😐 Simulate auth — check that token is non-empty
        return bool(credentials.auth_token)

    async def _do_delete(self, task: DeletionTask) -> DeletionResult:
        if task.resource_type not in self.supported_resource_types:
            return DeletionResult(
                task_id=task.task_id,
                success=False,
                error_message=f"Unsupported resource type: {task.resource_type}",
            )

        deleted = self._data.delete_resource(task.resource_type, task.resource_id)
        if deleted:
            return DeletionResult(
                task_id=task.task_id,
                success=True,
                proof=f"tweet_deleted:{task.resource_id}",
            )
        return DeletionResult(
            task_id=task.task_id,
            success=False,
            error_message=f"Resource not found: {task.resource_id}",
        )

    async def _do_verify(self, task: DeletionTask) -> VerificationStatus:
        exists = self._data.has_resource(task.resource_type, task.resource_id)
        if not exists:
            return VerificationStatus.CONFIRMED
        return VerificationStatus.FAILED

    async def _do_list_resources(self, resource_type: ResourceType) -> list[dict[str, str]]:
        return self._data.list_resources(resource_type)


# ============================================================================
# Facebook Adapter
# ============================================================================


class FacebookAdapter(PlatformAdapter):
    """
    😐 Facebook adapter. Simulates Graph API interactions.

    📺 Facebook's data model is a social graph of regret.
    Every node is a potential deletion target.

    Supported: POST, COMMENT, LIKE, FRIEND, PHOTO, VIDEO
    """

    def __init__(
        self,
        simulated_data: SimulatedPlatformData | None = None,
        rate_limit: RateLimitConfig | None = None,
    ) -> None:
        super().__init__(
            platform=Platform.FACEBOOK,
            rate_limit=rate_limit or RateLimitConfig(requests_per_minute=30),
        )
        self._data = simulated_data or SimulatedPlatformData()

    def _get_supported_types(self) -> set[ResourceType]:
        return {
            ResourceType.POST,
            ResourceType.COMMENT,
            ResourceType.LIKE,
            ResourceType.FRIEND,
            ResourceType.PHOTO,
            ResourceType.VIDEO,
        }

    async def _do_authenticate(self, credentials: PlatformCredentials) -> bool:
        return bool(credentials.auth_token)

    async def _do_delete(self, task: DeletionTask) -> DeletionResult:
        if task.resource_type not in self.supported_resource_types:
            return DeletionResult(
                task_id=task.task_id,
                success=False,
                error_message=f"Unsupported: {task.resource_type}",
            )

        deleted = self._data.delete_resource(task.resource_type, task.resource_id)
        if deleted:
            return DeletionResult(
                task_id=task.task_id,
                success=True,
                proof=f"fb_deleted:{task.resource_id}",
            )
        return DeletionResult(
            task_id=task.task_id,
            success=False,
            error_message=f"Not found: {task.resource_id}",
        )

    async def _do_verify(self, task: DeletionTask) -> VerificationStatus:
        exists = self._data.has_resource(task.resource_type, task.resource_id)
        return VerificationStatus.CONFIRMED if not exists else VerificationStatus.FAILED

    async def _do_list_resources(self, resource_type: ResourceType) -> list[dict[str, str]]:
        return self._data.list_resources(resource_type)


# ============================================================================
# Instagram Adapter
# ============================================================================


class InstagramAdapter(PlatformAdapter):
    """
    😐 Instagram adapter. Simulates Basic Display + Graph API.

    📺 Instagram: where your photographic evidence of poor
    decisions lives forever. Until Harold deletes it.

    Supported: POST, COMMENT, LIKE, PHOTO, VIDEO
    """

    def __init__(
        self,
        simulated_data: SimulatedPlatformData | None = None,
        rate_limit: RateLimitConfig | None = None,
    ) -> None:
        super().__init__(
            platform=Platform.INSTAGRAM,
            rate_limit=rate_limit or RateLimitConfig(requests_per_minute=20),
        )
        self._data = simulated_data or SimulatedPlatformData()

    def _get_supported_types(self) -> set[ResourceType]:
        return {
            ResourceType.POST,
            ResourceType.COMMENT,
            ResourceType.LIKE,
            ResourceType.PHOTO,
            ResourceType.VIDEO,
        }

    async def _do_authenticate(self, credentials: PlatformCredentials) -> bool:
        return bool(credentials.auth_token)

    async def _do_delete(self, task: DeletionTask) -> DeletionResult:
        if task.resource_type not in self.supported_resource_types:
            return DeletionResult(
                task_id=task.task_id,
                success=False,
                error_message=f"Unsupported: {task.resource_type}",
            )

        deleted = self._data.delete_resource(task.resource_type, task.resource_id)
        if deleted:
            return DeletionResult(
                task_id=task.task_id,
                success=True,
                proof=f"ig_deleted:{task.resource_id}",
            )
        return DeletionResult(
            task_id=task.task_id,
            success=False,
            error_message=f"Not found: {task.resource_id}",
        )

    async def _do_verify(self, task: DeletionTask) -> VerificationStatus:
        exists = self._data.has_resource(task.resource_type, task.resource_id)
        return VerificationStatus.CONFIRMED if not exists else VerificationStatus.FAILED

    async def _do_list_resources(self, resource_type: ResourceType) -> list[dict[str, str]]:
        return self._data.list_resources(resource_type)


# ============================================================================
# Adapter Registry
# ============================================================================

ADAPTER_REGISTRY: dict[Platform, type[PlatformAdapter]] = {
    Platform.TWITTER: TwitterAdapter,
    Platform.FACEBOOK: FacebookAdapter,
    Platform.INSTAGRAM: InstagramAdapter,
}


def get_adapter(
    platform: Platform,
    simulated_data: SimulatedPlatformData | None = None,
) -> PlatformAdapter:
    """
    Factory for platform adapters.

    😐 Returns the right adapter or raises KeyError.
    """
    adapter_cls = ADAPTER_REGISTRY.get(platform)
    if adapter_cls is None:
        raise KeyError(f"No adapter for platform: {platform}")
    return adapter_cls(simulated_data=simulated_data)  # type: ignore[call-arg]
