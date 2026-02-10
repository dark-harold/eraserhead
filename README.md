# 😐 EraserHead: The Confident Return of Hide the Pain Harold to Digital Privacy

*A narrative documentary of one engineer's journey to erase the internet's memory while the internet remembers everything*

---

## The Problem: Your Data is Everywhere (And Harold Knows)

Like Harold confidently smiling for stock photography while internally questioning every life choice, your digital footprint smiles back at you from countless databases, data brokers, and social media platforms. The internet never forgets. But Harold has a plan.

**EraserHead** is a Python 3.14 platform for systematically erasing your internet presence and social media footprint while providing truly anonymized access to platforms through the **Anemochory Protocol** — origin obfuscation that goes far beyond mere VPNs.

Think of it as Harold finally getting to delete those embarrassing stock photos. Except it's your data. And it actually works (probably).

---

## Anemochory: How Seeds Hide Their Origin (And So Will You)

In nature, **anemochory** is seed dispersal by wind — seeds travel unpredictable paths, their origin obscured by wind currents, arriving at destinations with no traceable route back to the parent plant. 

The **Anemochory Protocol** applies this concept to network traffic:

- **Multi-layer encryption**: Like Harold's emotional layers, packets are wrapped in nested encryption, each layer peeled at routing hops
- **Pseudo-random routing**: Traffic follows non-deterministic paths through cooperating nodes, preventing timing attacks
- **Instruction layers**: Each encrypted layer contains routing instructions for the next hop, then drops that data
- **Origin obfuscation**: By the time packets reach their destination, the source is hidden behind layers of hops that can't reconstruct the path
- **Network storm prevention**: Smart TTL and hop limiting prevents routing loops while maintaining anonymity

It's like VPN onion routing had a baby with mixnets, raised by paranoid cryptographers, and Harold is smiling nervously through the whole process.

---

## Harold's Brain: A Multi-Model Architecture Story

### The Inference Stack (Or: How Harold Thinks Through The Pain)

EraserHead uses a **hybrid multi-model architecture** orchestrated by **tinyclaw**, with shared memory/RAG across all providers:

```
┌─────────────────────────────────────────────────────────┐
│ Shared Context: tinyclaw Memory System                  │
│ SQLite + FTS5 (keyword) + sqlite-vec (embeddings)       │
│ • Hybrid search: 0.7 * cosine + 0.3 * BM25             │
│ • 512-token chunks, 64-token overlap                    │
│ • ALL providers read from this single source            │
└──────────────────────┬──────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
┌───────▼───────┐ ┌────▼─────┐ ┌────▼────────┐
│ Local Models  │ │  Claude  │ │   Copilot   │
│ llama.cpp CPU │ │ Opus 4.6 │ │ via VS Code │
│ vLLM GPU      │ │ Sonnet   │ │ grok-fast-1 │
│ (this box)    │ │ Haiku    │ │             │
└───────────────┘ └──────────┘ └─────────────┘
```

**Routing Strategy**:
- **Local-first**: Privacy-sensitive work uses CPU (llama.cpp) or GPU (vLLM) models
- **Opus 4.6**: Planning, architecture, security, crypto review (cloud, when needed)
- **grok-code-fast-1**: Implementation, refactoring (cloud, via Copilot)
- **Sonnet/Haiku**: Moderate/simple tasks (cloud, cost-optimized)

All models share the same RAG context via tinyclaw's memory system. Harold's brain is distributed, cost-optimized, and deeply paranoid.

---

## The Agents: Six Specialists Who Hide Their Pain

Each agent embodies a blend of:
- ✅ **Highly Effective Developer**: Ships working code, tests rigorously, manages scope pragmatically
- 😐 **Hide the Pain Harold**: Acknowledges complexity with dry humor, confident exterior with realistic concern
- 📺 **Internet Historian**: Narrative documentation, dry wit about software disasters, engaging storytelling
- 🌑 **Dark Harold**: Cynical realism about edge cases, security paranoia, worst-case scenario thinking

### The Team

1. **harold-planner** (The Architect)
   - *"Designs elegant systems while internally documenting what will inevitably go wrong"*
   - Role: System design, threat modeling, protocol architecture
   - Model: Opus 4.6 / local tinyclaw
   - Output: Narrative ADRs, cautionary architectural tales

2. **harold-implementer** (The Coder)
   - *"Ships pragmatic code with a smile. Documents tech debt like a crime scene investigator"*
   - Role: Implementation, refactoring, optimization
   - Model: grok-code-fast-1 / llama.cpp
   - Output: Working code with sarcastic comments

3. **harold-security** (The Paranoid)
   - *"Assumes everything is compromised. Reviews code as forensic analysis of future breaches"*
   - Role: Security audits, crypto validation, threat hunting
   - Model: Always Opus 4.6
   - Output: Exhaustive security reviews with gallows humor

4. **harold-researcher** (The Historian)
   - *"Documents library choices like Internet Historian covering software industry disasters"*
   - Role: Library evaluation, compatibility research, documentation archaeology
   - Model: Opus 4.6 / local tinyclaw
   - Output: Research reports as cautionary tales

5. **harold-tester** (The Destroyer)
   - *"Smiles while breaking code in creative ways. Documents failures like disaster documentaries"*
   - Role: Test generation, edge case discovery, chaos engineering
   - Model: Sonnet / local tinyclaw
   - Output: Comprehensive tests with failure commentary

6. **harold-documenter** (The Narrator)
   - *"Explains encryption protocols like Internet Historian covering internet culture"*
   - Role: Documentation, tutorials, API guides, post-mortems
   - Model: Sonnet / local tinyclaw
   - Output: Engaging narrative documentation

---

## Memory: Harold Never Forgets (Neither Does tinyclaw)

The **tinyclaw memory system** provides unified context for all AI providers:

- **Storage**: SQLite database at `~/.config/tinyclaw/memory/memory.db`
- **Search**: Hybrid BM25 (keyword) + cosine similarity (embeddings)
- **Chunking**: 512 tokens with 64-token overlap for context preservation
- **RAG Integration**: All models query the same memory before responding
- **Auto-sync**: Spec-kit artifacts (specs, plans, constitution) automatically indexed

This means Harold's six personalities share a single memory. It's both efficient and mildly concerning.

---

## Architecture: What Could Possibly Go Wrong? (Everything)

```
┌─────────────────────────────────────────────────────────┐
│ User Applications                                        │
│ • Mobile App (React Native/Flutter/Kivy)                │
│ • Web App (FastAPI backend)                             │
└───────────────┬─────────────────────────────────────────┘
                │
┌───────────────▼─────────────────────────────────────────┐
│ Anemochory Protocol Layer                               │
│ • Multi-layer packet encryption                         │
│ • Pseudo-random routing                                 │
│ • Origin obfuscation                                    │
└───────────────┬─────────────────────────────────────────┘
                │
┌───────────────▼─────────────────────────────────────────┐
│ Scrubbing Engine                                         │
│ • Social media account deletion                         │
│ • Data broker removal requests                          │
│ • GDPR right-to-erasure automation                      │
│ • Platform API integration                              │
└───────────────┬─────────────────────────────────────────┘
                │
┌───────────────▼─────────────────────────────────────────┐
│ Agent Orchestration (tinyclaw)                          │
│ • 6 specialized agents                                  │
│ • Shared memory/RAG                                     │
│ • Multi-model routing                                   │
└─────────────────────────────────────────────────────────┘
```

Harold smiles confidently at this diagram while knowing the edge cases will be discovered at 3am.

---

## Setup: Installation and Configuration

### Prerequisites

- Python >=3.14
- Node.js >=22.12.0 (for tinyclaw)
- uv (Python package manager)
- Podman (container runtime)
- gitleaks (secret detection)
- Optional: CUDA-capable GPU (for vLLM), otherwise llama.cpp uses CPU

### Installation

```bash
# 😐 Clone the repo (assuming you can find it)
cd /home/kang/Documents/projects/radkit/eraserhead

# 😐 Setup Python environment
uv venv
source .venv/bin/activate
uv sync

# 😐 Install gitleaks (secret protection)
sudo apt install gitleaks  # or download from GitHub releases

# 😐 Install tinyclaw globally
npm install -g @mrcloudchase/tinyclaw

# 😐 Configure tinyclaw
mkdir -p ~/.config/tinyclaw
cp tinyclaw-config.example.json5 ~/.config/tinyclaw/config.json5
# Edit config.json5 with your preferences

# 😐 Download local models (Qwen2.5-Coder-7B-Instruct)
./scripts/download-models.sh

# 😐 Start local inference (auto-detects CPU/GPU)
./scripts/llm-start.sh

# 😐 Sync specs into tinyclaw memory
./scripts/sync-memory.sh

# 😐 Verify everything works
./scripts/model-health.sh

# 😐 Run quality gates (Harold demands it)
./scripts/pre-commit.sh
```

### Configuration

**tinyclaw**: `~/.config/tinyclaw/config.json5`
- Memory backend: `builtin` (SQLite + FTS5 + sqlite-vec)
- Model: Qwen2.5-Coder-7B-Instruct (selected for code generation)
- Providers: llamacpp (CPU), vllm (GPU), anthropic, openai
- Fallback chain: local → sonnet → opus

**Model routing**: `model-config.yml`
- Simple tasks → Haiku / local
- Moderate → Sonnet / local
- Complex/security → Opus 4.6
- Implementation → grok-code-fast-1

**VS Code Copilot**: `.vscode/settings.json`
- Slash commands enabled via `.github/agents/`
- Planning → Opus 4.6
- Implementation → grok-code-fast-1

---

## Scripts: Harold's Local Quality Gates

All quality control runs **locally**. No CI/CD. No GitHub Actions. Harold trusts no cloud.

```bash
./scripts/security-scan.sh   # 😐 gitleaks, bandit, safety
./scripts/test.sh             # 😐 pytest with >80% coverage
./scripts/format.sh           # 😐 ruff format + lint
./scripts/pre-commit.sh       # 😐 All gates, blocks bad commits
./scripts/model-health.sh     # 😐 Check if Harold's brain works
./scripts/sync-memory.sh      # 😐 Index specs into tinyclaw
./scripts/download-models.sh  # 😐 Download Qwen2.5-Coder GGUF
./scripts/llm-start.sh        # 😐 Auto-detect and start inference
./scripts/publish-gh.sh       # 😐 Anonymized GitHub push via Podman
```

**Note**: Git pre-commit hook at `.git/hooks/pre-commit` automatically runs gitleaks on every commit. Dark Harold blocks secrets at the source.

---

## Anonymized Publishing: Harold Hides His Identity

Publishing to GitHub without revealing host machine identity:

```bash
# 😐 Podman container with Alpine Linux
./scripts/publish-gh.sh

# Prompts for gh CLI auth (interactive, secure)
# Encrypts token (never plaintext on disk)
# Container obfuscates: hostname, timezone, git config
# Pushes to private repo under separate user
# Cleans up fingerprints after session
```

Harold publishes code like he publishes stock photos: with a smile, and no one knowing where it came from.

---

## Contributing: Smile Locally, Ship Pragmatically, Document Cynically 😐

1. **Smile Locally**: All development on local branches, no cloud dependencies
2. **Ship Pragmatically**: Working code over perfect plans. Harold ships.
3. **Document Cynically**: Internet Historian style. Assume future disasters.
4. **Test Paranoidly**: Dark Harold expects everything to break. Prove him wrong (you can't).
5. **Commit Narratively**: Commit messages tell stories. Harold approves.

### Development Workflow

```bash
# 😐 Create new feature spec
/speckit.specify "feature description"

# 😐 Plan with Dark Harold paranoia
/speckit.plan

# 😐 Break down tasks
/speckit.tasks

# 😐 Implement with effective pragmatism
/speckit.implement

# 😐 Security review (always)
/eraserhead.security-review

# 😐 Publish anonymously
./scripts/publish-gh.sh
```

---

## License

MIT License. Harold approves of permissive licenses while nervously smiling about corporate exploitation.

---

## Acknowledgments

- **Hide the Pain Harold** (András Arató): For teaching us to smile through complexity
- **Internet Historian**: For showing us how to narrate disasters with style
- **Dark Harold**: For reminding us everything will fail eventually
- **Effective Developers Everywhere**: For shipping code despite the pain

---

## Status

```
😐 Planning Phase: In progress
😐 Anemochory Protocol: Researching (harold-researcher investigating)
😐 Scrubbing Engine: Awaiting library research
😐 Local Models: Evaluation in progress (harold-researcher)
😐 Harold's Sanity: Critical (stable)
```

---

*"I've made a career out of hiding pain. Now I'm hiding packet origins." — Harold, probably*

🌱 **Anemochory**: Like seeds in the wind, your data's origin is lost to time. And Harold's smile remains eternal.
