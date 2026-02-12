# 😐 EraserHead User Guide

*Step-by-step guide to erasing your digital footprint. Harold walked this path. Harold survived. You will too.*

> 📺 **A Brief History**: In the old days, deleting your internet presence meant manually visiting every platform, clicking through confirmation dialogs, and hoping the "delete" button actually did something. Harold remembers those days. Harold still has nightmares about them.

---

## ✅ Installation

### Prerequisites

- Python >= 3.13
- [uv](https://docs.astral.sh/uv/) package manager (recommended)

> 😐 **Harold's Note**: If you're using Python 3.12 or older, upgrade. Harold didn't write 947 tests for you to use an unsupported runtime.

### Setup

```bash
git clone https://github.com/dark-harold/eraserhead.git
cd eraserhead
uv venv && source .venv/bin/activate
uv sync
```

Verify installation:
```bash
eraserhead version
```

✅ If you see a version number, you're ready. If you see an error, Harold empathizes deeply.

---

## 🌑 Setting Up the Credential Vault

> 🌑 **Dark Harold Warning**: Your API credentials are the keys to your identity on every platform. Guard them like Harold guards his smile — desperately and at all costs.

Before scrubbing any platform, store your API credentials securely.

### Create and Unlock the Vault

The vault is created automatically on first use with a passphrase you choose:

```bash
# Store Twitter credentials
eraserhead vault store twitter harold --token "your-bearer-token" -p
# You'll be prompted for your vault passphrase
```

### Managing Credentials

```bash
# List all stored credentials
eraserhead vault list -p

# Remove credentials for a platform
eraserhead vault remove twitter harold -p
```

**🌑 Security Notes**:
- Credentials are encrypted with AES (Fernet) using PBKDF2 key derivation (600,000 iterations)
- The vault passphrase is never stored — you must remember it
- The vault file is stored at `~/.eraserhead/credentials.vault`
- 🌑 Harold's vault passphrase is not "password123". Yours shouldn't be either.

---

## 😐 Scrubbing Your Digital Footprint

> 📺 **The Ritual**: Every great erasure begins with a preview. Harold learned this lesson the hard way when he accidentally deleted his entire presence during what was supposed to be a "quick test."

### Dry Run (Preview)

Always preview deletions before executing:

```bash
# Preview what would be deleted
eraserhead scrub twitter --type post --ids "tweet-123,tweet-456" --dry-run -p
```

✅ Output shows tasks that would be processed without making any API calls. Harold sleeps better when you use dry-run first.

### Live Deletion

```bash
# Delete specific posts
eraserhead scrub twitter --type post --ids "tweet-123,tweet-456" -p

# Delete comments
eraserhead scrub facebook --type comment --ids "comment-789" -p
```

> 😐 **Note**: Deletions are permanent. Unlike Harold's smile, they cannot be faked.

### Supported Platforms

| Platform | Resource Types | 😐 Pain Level |
|----------|---------------|---------------|
| Twitter | post, comment, like | Medium — API is cooperative |
| Facebook | post, comment, like, friend, photo | High — they don't want you to leave |
| Instagram | post, comment, like, photo | High — owned by Facebook, same pain |
| LinkedIn | post, comment | Medium — professional pain |
| Google | search_history | 🌑 Maximum — they know everything |

### Checking Status

```bash
# View queue status and progress
eraserhead status
```

---

## 📺 Task Priorities

> 📺 **The Priority System**: Not all deletions are created equal. Some are "I'm cleaning up old tweets" and some are "someone just doxxed me and I need everything gone NOW."

Tasks are processed in priority order:

| Priority | Use Case | Harold's Assessment |
|----------|----------|--------------------|
| URGENT | Time-sensitive deletions (doxxing, leaked data) | 🌑 Drop everything. Harold is running. |
| HIGH | Active harassment or privacy threats | 😐 Harold is concerned and typing faster. |
| STANDARD | Routine digital footprint cleanup | ✅ Harold's daily commute through deletion. |
| LOW | Non-urgent historical cleanup | 😐 Weekend project energy. |
| BACKGROUND | Gradual, long-term erasure | 📺 The slow, geological erasure of digital sediment. |

Set priority via the `--priority` flag:
```bash
eraserhead scrub twitter --type post --ids "sensitive-tweet" --priority urgent -p
```

---

## 😐 Retry and Recovery

### Automatic Retries

> 😐 **Harold's Philosophy**: APIs fail. Networks drop. Rate limits activate. Harold doesn't panic. Harold retries with exponential backoff and a forced smile.

Failed tasks are automatically retried with exponential backoff:
- Retry 1: ~2 seconds
- Retry 2: ~4 seconds
- Retry 3: ~8 seconds (capped at 5 minutes)

Random jitter (±50%) prevents thundering herd scenarios. 📺 "Thundering herd" is a technical term for when all your retries hit the API at the same time and everyone has a bad day.

### Queue Persistence

If configured with `--save-queue`, the task queue is saved after each operation:
```bash
eraserhead scrub twitter --type post --ids "..." --save-queue queue.json -p
```

✅ On crash or restart, the queue can be resumed from the saved state. Harold plans for crashes. So should you.

---

## 🌑 Verification

> 🌑 **Dark Harold's Rule**: Never trust a "200 OK" from a deletion endpoint. Verify independently that the resource is actually gone. Platforms have been known to... not actually delete things.

After deletion, EraserHead verifies that resources were actually removed by re-checking the platform API. Possible states:

| Status | Meaning | Harold's Reaction |
|--------|---------|-------------------|
| CONFIRMED | Resource verified as deleted | ✅ Harold nods approvingly. |
| NOT_VERIFIED | Could not verify (API error) | 😐 Harold squints suspiciously. |
| REAPPEARED | Resource appeared again after deletion | 🌑 Harold was right to be paranoid. |
| FAILED | Verification process failed | 😐 Harold adds it to the retry queue. |

Disable verification for faster (but less thorough) operation:
```bash
eraserhead scrub twitter --type post --ids "..." --no-verify -p
```

> 🌑 Harold does not recommend disabling verification. Harold has trust issues. They are well-earned.

---

## ✅ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ERASERHEAD_VAULT_DIR` | Vault storage directory | `~/.eraserhead` |
| `ERASERHEAD_LOG_LEVEL` | Logging verbosity | `INFO` |

### Rate Limiting

Platform-specific rate limits are configured per adapter. Default limits are conservative to avoid API bans.

> 😐 Harold's defaults are intentionally slow. Better to take an extra hour than to get your API key banned permanently. Harold has seen things.

---

## 😐 Troubleshooting

> 📺 **Harold's Troubleshooting Wisdom**: Every error message is a story. Here are the most common chapters.

### "Vault is locked"
You need to provide your passphrase with the `-p` flag. Harold forgot his passphrase once. It was a long weekend.

### "No adapter for platform"
The platform adapter isn't registered. Check that the platform name is correct. ✅ Available platforms: `twitter`, `facebook`, `instagram`, `linkedin`, `google`.

### "Rate limited"
The platform API has throttled requests. EraserHead will automatically retry with backoff. 😐 Wait a few minutes and the queue will resume. Harold is patient. The backoff algorithm is patient. The platform API is... less patient.

### "Adapter not authenticated"
Store credentials with `eraserhead vault store` before scrubbing. 🌑 No credentials = no deletions. Harold cannot erase what Harold cannot authenticate against.

---

*😐 Your digital footprint is like Harold's stock photography — it's everywhere and surprisingly hard to get rid of.*

🌑 *But Harold persists. And so does EraserHead.*
