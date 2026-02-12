# <img src="memes/harold/emoji/harold-standard-24.png" height="24" alt="harold-standard"> Adapter Development Guide

*How to teach EraserHead to delete things from new platforms. Every platform API is a unique snowflake of documentation pain.*

> <img src="memes/harold/emoji/harold-historian-20.png" height="20" alt="harold-historian"> **The Adapter Origin Story**: In the early days, every platform deletion was hand-coded. Then Harold realized there would be *many* platforms. And each one would have its own authentication dance, its own rate limits, its own creative interpretation of "DELETE." The Adapter Pattern was born from Harold's exhaustion.

---

## <img src="memes/harold/emoji/harold-shipper-24.png" height="24" alt="harold-shipper"> Overview

EraserHead uses the **Adapter Pattern** to support multiple platforms. Each adapter implements the `PlatformAdapter` abstract base class, handling platform-specific API interactions while the engine manages orchestration, retries, and verification.

> <img src="memes/harold/emoji/harold-standard-20.png" height="20" alt="harold-standard"> The engine handles the hard parts (queuing, retries, crash recovery). Your adapter handles the *painful* parts (platform APIs).

---

## <img src="memes/harold/emoji/harold-historian-24.png" height="24" alt="harold-historian"> Creating a New Adapter

> <img src="memes/harold/emoji/harold-historian-20.png" height="20" alt="harold-historian"> **Harold's Adapter Development Arc**: Step 1 — Read the platform's API docs. Step 2 — Realize they're incomplete. Step 3 — Reverse-engineer what "delete" actually does. Step 4 — Handle the 17 error codes they don't document. Step 5 — Ship it with a smile.

### Step 1: Subclass `PlatformAdapter`

```python
"""😐 My custom platform adapter — another API, another adventure."""

from eraserhead.adapters import PlatformAdapter, RateLimitConfig
from eraserhead.models import (
    DeletionResult,
    DeletionTask,
    Platform,
    PlatformCredentials,
    ResourceType,
    VerificationStatus,
)


class MyPlatformAdapter(PlatformAdapter):
    """Adapter for MyPlatform API.
    
    📺 Every adapter is a love letter to a platform's API documentation.
    Some love letters are more... strained than others.
    """

    def __init__(self) -> None:
        super().__init__(
            platform=Platform.TWITTER,  # Use existing or extend Platform enum
            rate_limit=RateLimitConfig(
                requests_per_minute=30,
                burst_size=5,
                cooldown_seconds=60.0,
            ),
        )
        self._api_client = None

    async def _do_authenticate(self, credentials: PlatformCredentials) -> bool:
        """
        Connect to the platform's API.

        Args:
            credentials: Contains auth_token, api_key, api_secret, etc.

        Returns:
            True if authentication succeeded.
            
        🌑 Failure modes: Token expired, API key revoked, platform 
        is down, platform changed their auth flow without telling anyone.
        """
        try:
            self._api_client = MyPlatformAPI(
                token=credentials.auth_token,
                key=credentials.api_key,
            )
            return await self._api_client.verify_token()
        except Exception:
            return False  # 😐 Harold logs and moves on

    async def _do_disconnect(self) -> None:
        """Clean up API connections. ✅ Always clean up after yourself."""
        if self._api_client:
            await self._api_client.close()
            self._api_client = None

    async def _do_delete(self, task: DeletionTask) -> DeletionResult:
        """
        Delete a single resource.

        Args:
            task: Contains resource_id, resource_type, metadata

        Returns:
            DeletionResult with success/failure and proof
            
        😐 The platform will find creative ways to fail. Handle them all.
        """
        try:
            response = await self._api_client.delete(
                resource_type=task.resource_type,
                resource_id=task.resource_id,
            )
            return DeletionResult(
                task_id=task.task_id,
                success=True,
                proof={"api_response": response.status_code},
            )
        except RateLimitError:
            # 😐 The platform is asking us to slow down. Harold complies.
            return DeletionResult(
                task_id=task.task_id,
                success=False,
                error_message="Rate limited by platform",
            )
        except NotFoundError:
            # ✅ Resource already deleted — treat as success
            return DeletionResult(
                task_id=task.task_id,
                success=True,
                proof={"note": "Already deleted (404)"},
            )
        except Exception as e:
            # 🌑 Unknown failure. Log everything.
            return DeletionResult(
                task_id=task.task_id,
                success=False,
                error_message=f"API error: {e}",
            )

    async def _do_verify(self, task: DeletionTask) -> VerificationStatus:
        """
        Verify that the deletion actually occurred.

        Called after successful deletion if verify_after_delete=True.
        
        🌑 Dark Harold insists: never trust a deletion response.
        Always verify independently.
        """
        try:
            exists = await self._api_client.resource_exists(
                task.resource_type, task.resource_id
            )
            if not exists:
                return VerificationStatus.CONFIRMED
            return VerificationStatus.REAPPEARED  # 🌑 It's still there.
        except Exception:
            return VerificationStatus.NOT_VERIFIED

    async def _do_list_resources(
        self, resource_type: ResourceType
    ) -> list[dict[str, str]]:
        """List all resources of a given type for discovery."""
        results = await self._api_client.list_resources(resource_type)
        return [{"id": r.id, "content": r.preview} for r in results]

    def _get_supported_types(self) -> set[ResourceType]:
        """Declare which resource types this adapter handles."""
        return {
            ResourceType.POST,
            ResourceType.COMMENT,
            ResourceType.LIKE,
        }
```

### Step 2: Register with the Engine

```python
from eraserhead.engine import ScrubEngine, EngineConfig

engine = ScrubEngine(EngineConfig())
adapter = MyPlatformAdapter()
engine.register_adapter(adapter)
# ✅ Adapter registered. Harold nods approvingly.
```

### Step 3: Authenticate

```python
from eraserhead.models import PlatformCredentials, Platform

creds = PlatformCredentials(
    platform=Platform.TWITTER,
    username="harold",
    auth_token="your-bearer-token",
)
await adapter.authenticate(creds)
# 🌑 Credentials should come from the vault, not hardcoded. Harold is watching.
```

---

## <img src="memes/harold/emoji/harold-standard-24.png" height="24" alt="harold-standard"> Built-in Rate Limiting

> <img src="memes/harold/emoji/harold-standard-20.png" height="20" alt="harold-standard"> Rate limits exist because platforms don't want you deleting 10,000 posts per second. Harold respects this. Harold also finds it ironic that platforms make it hard to delete data they collected without asking.

The base class provides token bucket rate limiting. Configure per-platform:

```python
RateLimitConfig(
    requests_per_minute=30,   # Sustained rate
    burst_size=5,             # Allow short bursts
    cooldown_seconds=60.0,    # Cooldown after rate limit hit
)
```

When rate limited, `delete_resource()` returns a failed `DeletionResult` with "Rate limited" error. The engine's retry logic handles re-queuing with exponential backoff.

> <img src="memes/harold/emoji/harold-shipper-20.png" height="20" alt="harold-shipper"> **Best Practice**: Set conservative rate limits. A temporarily slow deletion is better than a permanently banned API key.

---

## <img src="memes/harold/emoji/harold-standard-24.png" height="24" alt="harold-standard"> Testing Your Adapter

> <img src="memes/harold/emoji/harold-historian-20.png" height="20" alt="harold-historian"> **Harold's Testing Philosophy**: Every platform API call should be mockable. Harold-tester generates edge cases. You implement the mocks.

```python
import pytest
from eraserhead.models import DeletionTask, Platform, ResourceType

class TestMyAdapter:
    """😐 Breaking platform adapters with a smile."""

    async def test_delete_success(self):
        """✅ The happy path — resource deleted successfully."""
        adapter = MyPlatformAdapter()
        adapter._api_client = MockAPIClient(success=True)
        adapter._status = AdapterStatus.AUTHENTICATED

        task = DeletionTask(
            platform=Platform.TWITTER,
            resource_type=ResourceType.POST,
            resource_id="test-123",
        )
        result = await adapter.delete_resource(task)
        assert result.success

    async def test_delete_not_found(self):
        """✅ 404 = already deleted. Harold considers this a win."""
        adapter = MyPlatformAdapter()
        adapter._api_client = MockAPIClient(raises=NotFoundError)
        adapter._status = AdapterStatus.AUTHENTICATED

        task = DeletionTask(...)
        result = await adapter.delete_resource(task)
        assert result.success  # 404 = already deleted

    async def test_delete_rate_limited(self):
        """😐 The platform pushed back. Harold waits patiently."""
        adapter = MyPlatformAdapter()
        adapter._api_client = MockAPIClient(raises=RateLimitError)
        adapter._status = AdapterStatus.AUTHENTICATED

        task = DeletionTask(...)
        result = await adapter.delete_resource(task)
        assert not result.success
        # 🌑 The engine will retry with backoff
```

---

## <img src="memes/harold/emoji/harold-historian-24.png" height="24" alt="harold-historian"> Adapter Statistics

The base class tracks operational stats automatically:

```python
stats = adapter.stats
print(f"Total requests: {stats.total_requests}")
print(f"Success rate: {stats.success_rate:.1%}")
print(f"Rate limit hits: {stats.rate_limit_hits}")
# 😐 If success_rate < 90%, something is wrong with the platform. Or with your adapter.
# 🌑 Harold recommends investigating before the rate_limit_hits pile up.
```

---

## <img src="memes/harold/emoji/harold-shipper-24.png" height="24" alt="harold-shipper"> Best Practices

> <img src="memes/harold/emoji/harold-historian-20.png" height="20" alt="harold-historian"> Harold has built adapters for five platforms. Here's what he learned, condensed into wisdom earned through suffering.

1. **<img src="memes/harold/emoji/harold-shipper-20.png" height="20" alt="harold-shipper"> Handle 404 as success**: If a resource is already deleted, return `success=True`. Don't retry the already-gone.
2. **<img src="memes/harold/emoji/harold-shipper-20.png" height="20" alt="harold-shipper"> Include proof**: Store API response codes or deletion confirmation IDs. <img src="memes/harold/emoji/harold-dark-20.png" height="20" alt="harold-dark"> You may need evidence later.
3. **<img src="memes/harold/emoji/harold-standard-20.png" height="20" alt="harold-standard"> Respect rate limits**: Set conservative `RateLimitConfig` values. Better slow than banned.
4. **<img src="memes/harold/emoji/harold-dark-20.png" height="20" alt="harold-dark"> Test error paths**: Rate limits, network errors, auth failures, unexpected JSON responses, the platform changing their API without notice on a Friday afternoon.
5. **<img src="memes/harold/emoji/harold-shipper-20.png" height="20" alt="harold-shipper"> Clean disconnection**: Release API connections in `_do_disconnect()`. Leaked connections are Harold's least favorite kind of leak (after credential leaks).
6. **<img src="memes/harold/emoji/harold-standard-20.png" height="20" alt="harold-standard"> Metadata support**: Use `task.metadata` for platform-specific parameters that don't fit the standard model.

---

*<img src="memes/harold/emoji/harold-standard-20.png" height="20" alt="harold-standard"> Every platform API is a unique snowflake of documentation pain. Adapters absorb this suffering so the engine doesn't have to.*

<img src="memes/harold/emoji/harold-dark-20.png" height="20" alt="harold-dark"> *Harold has been through five platform APIs. Harold has the scars. Harold documented them so you don't have to earn your own.*
