# <img src="memes/harold/emoji/harold-standard-24.png" height="24" alt="harold-standard"> EraserHead API Reference

*Your guide to systematic digital footprint elimination. Harold would be proud. Harold IS proud. Harold is also mildly concerned you'll misuse `secure_zero_memory`.*

> <img src="memes/harold/emoji/harold-historian-20.png" height="20" alt="harold-historian"> **Narrator**: What follows is the complete API surface of EraserHead — from the cryptographic depths of the Anemochory Protocol to the pragmatic machinery of the Scrubbing Engine. Each module has been tested, reviewed by harold-security, and blessed with appropriate paranoia.

---

## <img src="memes/harold/emoji/harold-anemochory-24.png" height="24" alt="harold-anemochory"> Anemochory Protocol (`anemochory`)

> <img src="memes/harold/emoji/harold-historian-20.png" height="20" alt="harold-historian"> In nature, anemochory is seed dispersal by wind — origins hidden, paths untraceable. In code, it's the same thing but with ChaCha20-Poly1305.

### `ChaCha20Engine`

Multi-layer onion encryption engine using ChaCha20-Poly1305.

```python
from anemochory.crypto import ChaCha20Engine

engine = ChaCha20Engine()

# 😐 Wrap payload in encryption layers (one per hop)
keys = [key1, key2, key3]  # 32-byte keys
packet = engine.wrap(payload=b"secret data", layer_keys=keys)

# Unwrap one layer at a node
plaintext = engine.unwrap(packet=encrypted_data, key=node_key)
```

**Key methods**:
- `wrap(payload: bytes, layer_keys: list[bytes]) -> bytes` — Encrypt payload with multiple layers
- `unwrap(packet: bytes, key: bytes) -> bytes` — Decrypt one encryption layer
- `encrypt(plaintext: bytes, key: bytes, nonce: bytes) -> bytes` — Single-layer AEAD encryption
- `decrypt(ciphertext: bytes, key: bytes, nonce: bytes) -> bytes` — Single-layer AEAD decryption

> <img src="memes/harold/emoji/harold-dark-20.png" height="20" alt="harold-dark"> **Security**: Each layer uses a unique nonce. Nonce reuse with ChaCha20-Poly1305 is catastrophic. Harold-security verified this is handled correctly. Harold-security still worries.

---

### `AnemochoryClient`

High-level client for sending anonymized packets through the network.

```python
from anemochory.client import AnemochoryClient

client = AnemochoryClient(node_pool=pool)
await client.send(payload=b"message", destination="exit-node-id")
```

**Key methods**:
- `send(payload, destination, hops=3)` — Send payload through onion-routed path
- `close()` — Disconnect from all nodes

> <img src="memes/harold/emoji/harold-shipper-20.png" height="20" alt="harold-shipper"> The client handles path selection, encryption wrapping, and transmission. You just call `send()`. Harold did the hard part.

---

### `PathSelector`

Weighted random path selection with diversity constraints.

```python
from anemochory.routing import PathSelector

selector = PathSelector(node_pool=pool)
path = selector.select_path(destination="exit-node-id", hop_count=5)
```

**Properties**:
- `min_hops` / `max_hops` — Configurable hop range (default: 3-7)
- Ensures geographic and network diversity across hops
- Weighted selection based on node reliability and bandwidth

> <img src="memes/harold/emoji/harold-dark-20.png" height="20" alt="harold-dark"> **Dark Harold Note**: Path diversity isn't optional — it's defense against traffic analysis. A path through three nodes in the same datacenter is worse than no anonymization at all.

---

### `SecureSession`

Establishes encrypted session with forward secrecy.

```python
from anemochory.session import SecureSession

session = SecureSession.create(
    local_private_key=my_key,
    remote_public_key=peer_key,
)
encrypted = session.encrypt(b"data")
plaintext = session.decrypt(encrypted)
```

**<img src="memes/harold/emoji/harold-dark-20.png" height="20" alt="harold-dark"> Security properties**:
- X25519 ECDH key exchange
- HKDF-SHA256 key derivation with context binding
- Automatic key rotation every 10k packets or 1 hour
- Replay protection via nonce tracking

> <img src="memes/harold/emoji/harold-dark-20.png" height="20" alt="harold-dark"> Every session generates ephemeral keys. Compromise one session, and only that session is exposed. Forward secrecy: Harold's favorite kind of secrecy (the kind that actually works).

---

### <img src="memes/harold/emoji/harold-dark-24.png" height="24" alt="harold-dark"> Secure Memory (`crypto_memory`)

```python
from anemochory.crypto_memory import secure_zero_memory, key_to_mutable

# Convert immutable key to mutable for secure wiping
mutable_key = key_to_mutable(key_bytes)

# Use the key...

# 🌑 Securely wipe key material — uses explicit_bzero on Linux
secure_zero_memory(mutable_key)
```

> <img src="memes/harold/emoji/harold-dark-20.png" height="20" alt="harold-dark"> **Dark Harold**: Key material lingering in memory is key material available to an attacker with a debugger. Wipe early, wipe often. Trust no garbage collector.

---

## <img src="memes/harold/emoji/harold-standard-24.png" height="24" alt="harold-standard"> Scrubbing Engine (`eraserhead`)

> <img src="memes/harold/emoji/harold-historian-20.png" height="20" alt="harold-historian"> The Scrubbing Engine is where Harold's pragmatism meets the messy reality of platform APIs. Each platform has its own quirks, rate limits, and creative interpretations of "deleted."

### `ScrubEngine`

Core orchestrator for deletion tasks.

```python
from eraserhead.engine import ScrubEngine, EngineConfig
from eraserhead.models import Platform, ResourceType

engine = ScrubEngine(EngineConfig(
    dry_run=False,
    max_retries=3,
    verify_after_delete=True,
))

# Register platform adapters
engine.register_adapter(twitter_adapter)

# Queue deletion tasks
engine.add_tasks(
    platform=Platform.TWITTER,
    resource_type=ResourceType.POST,
    resource_ids=["tweet-123", "tweet-456"],
)

# Execute all tasks
results = await engine.run()
for r in results:
    print(f"Task {r.task_id}: {'✅' if r.success else '😐'} {r.error_message or ''}")
```

**Configuration** (`EngineConfig`):

| Parameter | Default | Description | <img src="memes/harold/emoji/harold-standard-20.png" height="20" alt="harold-standard"> Harold's Take |
|-----------|---------|-------------|-------------------|
| `dry_run` | `False` | Preview mode — no actual deletions | Always use first. Always. |
| `max_retries` | `3` | Retry count with exponential backoff | 3 is sufficient. 30 is paranoia. |
| `verify_after_delete` | `True` | Confirm deletion via platform API | <img src="memes/harold/emoji/harold-dark-20.png" height="20" alt="harold-dark"> Never disable this. |
| `queue_save_path` | `None` | Path to persist queue for crash recovery | <img src="memes/harold/emoji/harold-shipper-20.png" height="20" alt="harold-shipper"> Set this. Harold learned the hard way. |

---

### <img src="memes/harold/emoji/harold-dark-24.png" height="24" alt="harold-dark"> `CredentialVault`

Encrypted credential storage with PBKDF2 key derivation.

```python
from eraserhead.vault import CredentialVault
from eraserhead.models import Platform, PlatformCredentials

vault = CredentialVault(vault_dir=Path("~/.eraserhead"))
vault.unlock("my-passphrase")

# Store credentials
vault.store(PlatformCredentials(
    platform=Platform.TWITTER,
    username="harold",
    auth_token="bearer-token-here",
))

# Retrieve credentials
creds = vault.get(Platform.TWITTER, "harold")

# 🌑 Lock when done (clears key from memory)
vault.lock()
```

**<img src="memes/harold/emoji/harold-dark-20.png" height="20" alt="harold-dark"> Security**:
- AES-128-CBC + HMAC-SHA256 (Fernet symmetric encryption)
- PBKDF2 with 600,000 iterations for key derivation
- Random 128-bit salt per vault
- Best-effort memory zeroing on lock

> <img src="memes/harold/emoji/harold-dark-20.png" height="20" alt="harold-dark"> 600,000 PBKDF2 iterations means brute-forcing the vault passphrase is computationally expensive. Not impossible — nothing is impossible — but expensive enough that Harold approves.

---

### `TaskQueue`

Priority-based deletion task queue with persistence.

```python
from eraserhead.queue import TaskQueue
from eraserhead.models import Platform, ResourceType, TaskPriority

queue = TaskQueue(max_retries=3)

# Add tasks with priority
task = queue.add_task(
    platform=Platform.TWITTER,
    resource_type=ResourceType.POST,
    resource_id="tweet-123",
    priority=TaskPriority.URGENT,  # 🌑 Someone is being doxxed
)

# Get next task to process
next_task = queue.next_task()  # Returns highest priority pending task

# ✅ Save/load for crash recovery
queue.save(Path("queue.json"))
restored = TaskQueue.load(Path("queue.json"))
```

**Priority levels**: `URGENT(1)` > `HIGH(3)` > `STANDARD(5)` > `LOW(7)` > `BACKGROUND(9)`

> <img src="memes/harold/emoji/harold-standard-20.png" height="20" alt="harold-standard"> The queue is a priority queue, which means URGENT tasks jump the line. Harold finds this reasonable. Harold has been URGENT before.

---

### `PlatformAdapter` (Abstract Base)

Implement custom platform adapters by subclassing:

```python
from eraserhead.adapters import PlatformAdapter
from eraserhead.models import (
    DeletionResult, DeletionTask, Platform,
    PlatformCredentials, ResourceType, VerificationStatus,
)

class MyPlatformAdapter(PlatformAdapter):
    """😐 Another platform, another API to learn."""

    def __init__(self):
        super().__init__(platform=Platform.TWITTER)

    async def _do_authenticate(self, credentials: PlatformCredentials) -> bool:
        # Connect to platform API
        return True  # 😐 Hopefully

    async def _do_delete(self, task: DeletionTask) -> DeletionResult:
        # Delete the resource
        return DeletionResult(task_id=task.task_id, success=True)

    async def _do_verify(self, task: DeletionTask) -> VerificationStatus:
        # 🌑 Verify deletion actually occurred (trust nothing)
        return VerificationStatus.CONFIRMED

    async def _do_list_resources(self, resource_type: ResourceType) -> list[dict[str, str]]:
        # List resources of given type
        return [{"id": "123", "content": "..."}]

    def _get_supported_types(self) -> set[ResourceType]:
        return {ResourceType.POST, ResourceType.COMMENT}
```

> <img src="memes/harold/emoji/harold-historian-20.png" height="20" alt="harold-historian"> For the complete adapter development guide with testing patterns and best practices, see the [Adapter Development Guide](adapter-development.md).

---

### Erasure Providers (`eraserhead.providers`)

Compliance-aware erasure with GDPR/CCPA support:

```python
from eraserhead.providers.orchestrator import ErasureOrchestrator
from eraserhead.providers.registry import ProviderRegistry

registry = ProviderRegistry()
orchestrator = ErasureOrchestrator(registry=registry)

# Orchestrate multi-provider erasure
results = await orchestrator.execute(erasure_plan)
```

> <img src="memes/harold/emoji/harold-historian-20.png" height="20" alt="harold-historian"> **The Compliance Story**: GDPR says "right to erasure." CCPA says "right to delete." Harold says "right to actually verify the data is gone and not just flagged as inactive in some database Harold cannot access."

---

## <img src="memes/harold/emoji/harold-shipper-24.png" height="24" alt="harold-shipper"> CLI Commands

```
eraserhead vault store <platform> <username>   Store credentials
eraserhead vault list                          List stored credentials
eraserhead vault remove <platform> <username>  Remove credentials
eraserhead scrub <platform> --type <type>      Execute deletion tasks
eraserhead status                              Show queue/engine status
eraserhead version                             Show version information
```

All vault commands require `-p` flag for passphrase prompt. <img src="memes/harold/emoji/harold-dark-20.png" height="20" alt="harold-dark"> Harold will not store your passphrase for you. That would defeat the purpose.

---

## <img src="memes/harold/emoji/harold-historian-24.png" height="24" alt="harold-historian"> Data Models

> <img src="memes/harold/emoji/harold-historian-20.png" height="20" alt="harold-historian"> The taxonomy of digital erasure — every enum, every status, every possible outcome Harold has contemplated at 3 AM.

### `Platform` (enum)
`FACEBOOK`, `TWITTER`, `INSTAGRAM`, `LINKEDIN`, `GOOGLE`

### `ResourceType` (enum)
`POST`, `COMMENT`, `LIKE`, `FRIEND`, `PHOTO`, `VIDEO`, `MESSAGE`, `PROFILE`, `SEARCH_HISTORY`, `ACCOUNT`

### `TaskPriority` (IntEnum)
`URGENT(1)`, `HIGH(3)`, `STANDARD(5)`, `LOW(7)`, `BACKGROUND(9)`

### `TaskStatus` (enum)
`PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, `RETRYING`, `CANCELLED`, `VERIFIED`

### `VerificationStatus` (enum)
`NOT_VERIFIED`, `PENDING`, `CONFIRMED`, `FAILED`, `REAPPEARED`

> <img src="memes/harold/emoji/harold-standard-20.png" height="20" alt="harold-standard"> If a `VerificationStatus` comes back as `REAPPEARED`, something has gone wrong at the platform level. Harold is not surprised. Harold is never surprised.

---

*<img src="memes/harold/emoji/harold-standard-20.png" height="20" alt="harold-standard"> Remember: every API call is a deletion that can't be undone. Harold tested this the hard way.*

<img src="memes/harold/emoji/harold-dark-20.png" height="20" alt="harold-dark"> *Every method documented here was reviewed by harold-security. Every edge case was imagined by harold-tester. Every explanation was narrated by harold-documenter. Harold is a team sport.*
