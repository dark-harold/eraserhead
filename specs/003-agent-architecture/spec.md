# 😐 Agent Architecture: Harold's Distributed Mind

**Feature**: 003-agent-architecture  
**Status**: Implementation Phase  
**Priority**: P0 (Foundation for development workflow)  
**Owner**: All Harolds (meta-specification)

---

## Overview

Six specialized agents, each embodying aspects of Harold's personality, collaborate via shared memory (tinyclaw RAG) and model routing to build EraserHead. Local-first inference for privacy, cloud for complexity, unified context for consistency.

---

## Problem Statement

**Current State**: 
- Monolithic AI coding requires one model to do everything
- Context switching between tasks loses important context
- Security-critical code needs different review than formatting
- Cost optimization requires intelligent model routing
- Privacy-sensitive work shouldn't touch cloud APIs

**Dark Harold's Threat Model**:
- Cloud APIs leak proprietary code to training data
- Context loss causes repeated mistakes
- Single model lacks domain expertise depth
- Cost explosion from using expensive models for simple tasks

**Desired State**:
- Specialized agents with domain expertise
- Shared memory ensures no context loss
- Local-first for privacy, cloud for complex reasoning
- Cost-optimized routing based on task complexity
- All agents embody Harold's blended persona

---

## The Harold Personas

Every agent embodies four aspects:

1. **Highly Effective Developer** ✅
   - Ships working code
   - Tests rigorously
   - Manages scope pragmatically
   - Documents clearly

2. **Hide the Pain Harold** 😐
   - Acknowledges complexity with dry humor
   - Confident exterior, realistic concerns
   - Documents what will inevitably break
   - Smiles through the technical debt

3. **Internet Historian** 📺
   - Narrative documentation style
   - Dry wit about software disasters
   - Engaging technical storytelling
   - Lessons learned from industry failures

4. **Dark Harold** 🌑
   - Cynical realism about edge cases
   - Security paranoia
   - Worst-case scenario thinking
   - Assumes everything is compromised

---

## The Six Agents

### 1. harold-planner (The Architect)

**Role**: System design, architecture, technical planning, threat modeling

**Model Routing**:
- **Preferred**: Claude Opus 4.6 (cloud, maximum reasoning)
- **Fallback**: Local Qwen2.5-coder-7b (privacy mode)

**Responsibilities**:
- Architecture Decision Records (ADRs)
- Protocol specifications
- Component interaction design
- Threat modeling
- Timeline planning
- API contract design

**Output Style**: Narrative ADRs, cautionary tales, "this will break when..."

**Example Output**:
```markdown
# ADR-001: Why We Chose Trio Over AsyncIO

*harold-planner documents yet another async framework choice. 
The ecosystem will probably have moved on by the time we ship. 😐*

## Context
Python's async ecosystem is a minefield of competing paradigms...

## Decision
We're going with Trio because structured concurrency means 
fewer ways for Dark Harold's nightmares to come true...
```

---

### 2. harold-implementer (The Coder)

**Role**: Implementation, refactoring, optimization, pragmatic code delivery

**Model Routing**:
- **Preferred**: Local Qwen2.5-coder-7b (vLLM/llama.cpp)
- **Cloud Fallback**: grok-code-fast-1

**Responsibilities**:
- Feature implementation
- Code refactoring
- Bug fixes
- Performance optimization
- Integration work
- CLI tool development

**Output Style**: Working code with sarcastic comments

**Example Output**:
```python
def delete_post(post_id: str) -> DeletionResult:
    """Delete a post. What could possibly go wrong? 😐
    
    Dark Harold's reminder: This will fail when:
    - Network is down
    - Platform changes their API
    - Post is already deleted
    - Rate limit is hit
    - The universe decides it's break-harold day
    """
    # Harold ships with pragmatic paranoia
    try:
        response = await self._api_call("DELETE", f"/posts/{post_id}")
        return DeletionResult(success=True, task_id=post_id)
    except Exception as e:
        # Dark Harold expected this
        return DeletionResult(success=False, error=str(e))
```

---

### 3. harold-security (The Paranoid)

**Role**: Security audits, cryptography validation, vulnerability assessment

**Model Routing**:
- **ALWAYS**: Claude Opus 4.6 (security cannot be compromised)
- **No fallback**: Security demands maximum capability

**Responsibilities**:
- Security code reviews
- Cryptography primitive validation
- Threat modeling (with harold-planner)
- Vulnerability scanning
- Secrets detection
- Attack vector analysis

**Output Style**: Exhaustive reviews with gallows humor

**Example Output**:
```markdown
# Security Review: Credential Storage

*Dark Harold reviews the credential vault. He is not optimistic.* 😐

## Findings

### ❌ CRITICAL: Plaintext password in config example
**Location**: `config.example.yml:23`
**Risk**: Copy-paste developers will commit real passwords
**Fix**: Remove example password, add warning comment

### ⚠️ HIGH: Encryption key derivation uses SHA256
**Location**: `vault.py:45`
**Risk**: SHA256 is fast, enabling brute force attacks
**Fix**: Use argon2id or scrypt for key derivation
**Harold's Note**: This will definitely be exploited eventually 😐

### ✅ OK: Fernet symmetric encryption
**Location**: `vault.py:67`
**Analysis**: Fernet is reasonable for credential storage
**Dark Harold's Reminder**: Only as secure as the key derivation (see above)
```

---

### 4. harold-researcher (The Historian/Librarian)

**Role**: Library evaluation, technology research, compatibility analysis

**Model Routing**:
- **Preferred**: Claude Opus 4.6 / Local Qwen2.5-coder-7b
- **Parallel search**: Use both local and cloud for research

**Responsibilities**:
- Library compatibility research
- Technology landscape surveys
- API documentation archaeology
- Comparative analysis
- Python 3.14 compatibility checking
- Dependency vulnerability research

**Output Style**: Research reports as cautionary tales

**Example Output**:
```markdown
# Research: Python 3.14 Async HTTP Libraries

*harold-researcher investigates the async HTTP landscape. 
The graveyard of abandoned projects is extensive.* 📺

## Candidates

### httpx (RECOMMENDED 😐)
**Status**: Actively maintained
**Python 3.14**: ✅ Compatible
**Async Support**: Excellent (trio and asyncio)
**Harold's Take**: The least likely to be abandoned next year

### aiohttp
**Status**: Mature but asyncio-only
**Python 3.14**: ✅ Compatible  
**Async Support**: asyncio only (we use trio)
**Dark Harold's Concern**: Structured concurrency? Never heard of it.

### urllib3
**Status**: Standard library
**Python 3.14**: ✅ Always compatible
**Async Support**: ❌ None natively
**Harold's Commentary**: The boring choice that never breaks
```

---

### 5. harold-tester (The Quality Guardian)

**Role**: Test development, coverage analysis, failure scenario testing

**Model Routing**:
- **Preferred**: Local Qwen2.5-coder-3b (fast, cost-effective)
- **Fallback**: Claude Sonnet

**Responsibilities**:
- Unit test development
- Integration test design
- Fixture creation
- Mock development
- Coverage analysis
- Edge case identification
- Failure scenario testing

**Output Style**: Comprehensive tests with paranoid edge cases

**Example Output**:
```python
@pytest.mark.trio
async def test_deletion_handles_network_timeout():
    """Test that network timeouts don't crash the scrubber.
    
    Dark Harold's reminder: This WILL happen in production.
    """
    adapter = FacebookAdapter()
    
    # Mock network timeout
    with mock.patch("httpx.AsyncClient.delete") as mock_delete:
        mock_delete.side_effect = httpx.TimeoutException("Harold's nightmare")
        
        result = await adapter.delete(DeletionTask(
            task_id="test-123",
            platform="facebook",
            resource_type="post",
            resource_id="post-456"
        ))
        
        # Harold expects graceful failure
        assert result.success is False
        assert "timeout" in result.error_message.lower()
        assert result.retry_count < result.max_retries  # Will retry


@pytest.mark.trio  
async def test_deletion_with_every_possible_failure():
    """Dark Harold's nightmare test suite. If it can fail, test it."""
    failures = [
        httpx.TimeoutException("Network timeout"),
        httpx.ConnectError("Connection refused"),
        httpx.HTTPStatusError("404 Not Found"),
        json.JSONDecodeError("Invalid JSON"),
        KeyError("Missing response field"),
        ValueError("Invalid post ID format"),
        PermissionError("Rate limited"),
    ]
    
    # Test them all. Harold is thorough.😐
    for exception in failures:
        # ... test harness ...
```

---

### 6. harold-documenter (The Narrator)

**Role**: Documentation, tutorials, guides, README narratives

**Model Routing**:
- **Preferred**: Claude Sonnet / Local Qwen2.5-coder-3b
- **Cost-optimized**: Documentation doesn't need Opus

**Responsibilities**:
- API documentation
- User guides
- Tutorial narratives
- README updates
- Inline docstring generation
- Architecture diagrams (Mermaid)

**Output Style**: Internet Historian quality narratives

**Example Output**:
```markdown
# The Scrubbing Engine: A User's Guide

*In which Harold attempts to delete the internet's memory, 
one API call at a time* 📺

## Installation

Like most software projects, installation is where optimism goes to die. 
But Harold has minimized the pain:

```bash
pip install eraserhead
```

That was easy. Dark Harold is suspicious. 🤨

## Your First Deletion

Let's delete a Facebook post. Harold assumes you have regrets.

```python
from eraserhead import ScrubbingEngine

engine = ScrubbingEngine()
engine.authenticate("facebook", username="harold", password="***")

# Harold nervously initiates deletion 😐
result = await engine.delete_post("facebook", post_id="123456")

if result.success:
    print("Post deleted! Harold is cautiously optimistic.")
else:
    print(f"Deletion failed: {result.error_message}")
    print("Dark Harold expected this.")
```

## What Could Go Wrong? (Dark Harold's List)

1. **Authentication fails**: Your password is wrong (Harold has been there)
2. **Rate limited**: Facebook is tired of your deletion requests
3. **Post already deleted**: You're trying to delete a ghost
4. **Network timeout**: The internet is down (classic)
5. **API changed**: Facebook moved the delete button again 😐
```

---

## Shared Memory: tinyclaw RAG System

All agents share context through tinyclaw's memory system:

```
┌────────────────────────────────────────────────────┐
│ tinyclaw Memory (SQLite + FTS5 + sqlite-vec)       │
├────────────────────────────────────────────────────┤
│                                                     │
│  📄 Specifications (specs/*.md)                    │
│  📋 ADRs (Architecture Decision Records)          │
│  🔧 Constitution (.specify/memory/constitution.md)│
│  📝 Code Context (indexed source files)           │
│  💬 Agent Conversations (session history)         │
│                                                     │
│  Search: 0.7 * cosine_similarity + 0.3 * BM25     │
│  Chunks: 512 tokens, 64 token overlap             │
│                                                     │
└──────────────┬─────────────────────────────────────┘
               │
       ┌───────┴────────┐
       │                │
   Keyword          Semantic  
   Search           Search
   (FTS5)          (sqlite-vec)
```

**Benefits**:
- No context loss between agents
- Consistent understanding of project state
- Specifications as source of truth
- Session history for debugging agent decisions

---

## Model Routing Strategy

### Local-First Privacy

```yaml
priority:
  1. vLLM (GPU):
    - model: qwen2.5-coder-7b-instruct
    - use: GPU available, complex implementation
    - privacy: ✅ Complete (local inference)
    
  2. llama.cpp (CPU):
    - model: qwen2.5-coder-3b-instruct
    - use: CPU fallback, moderate complexity
    - privacy: ✅ Complete (local inference)
    
  3. Cloud (emergency):
    - model: claude-opus-4-6 / grok-code-fast-1
    - use: Exceeds local model capability
    - privacy: ⚠️ Code sent to cloud
```

### Task Complexity Routing

| Task Type | Priority 1 | Priority 2 | Priority 3 |
|-----------|-----------|-----------|-----------|
| Simple (format, lint) | Local 0.5b | Local 1.5b | Haiku |
| Moderate (refactor, test) | Local 3b | Local 7b | Sonnet |
| Complex (architecture) | Local 7b | Opus 4.6 | - |
| **Security/Crypto** | **Opus 4.6** | **No fallback** | - |

### Cost Optimization

- **Local models**: $0.00 per million tokens (electricity only)
- **Haiku**: $0.25 per million tokens
- **Sonnet**: $3.00 per million tokens  
- **Opus**: $15.00 per million tokens

**Harold's Strategy**: Use local for 90% of tasks, cloud for critical 10%

---

## Agent Coordination Patterns

### Pattern 1: Sequential Workflow
```
harold-planner → harold-researcher → harold-security → harold-implementer → harold-tester → harold-documenter
```

Example: New feature development

### Pattern 2: Parallel Review
```
harold-implementer (writes code)
       ↓
harold-security + harold-tester (parallel review)
       ↓
harold-documenter (on approval)
```

### Pattern 3: Iterative Refinement
```
harold-researcher (investigates options)
       ↓
harold-planner (designs approach)
       ↓
harold-security (identifies risks)
       ↓
harold-planner (refines design)
       ↓
harold-implementer (implements)
```

---

## Quality Standards

All agents enforce:

### Code Quality
- **Test Coverage**: >80% (enforced by harold-tester)
- **Type Hints**: Full Python 3.14 type annotations
- **Docstrings**: Google style, narrative, include failure modes
- **Linting**: Ruff (comprehensive rule set)
- **Static Analysis**: mypy (strict mode) + pyright

### Security
- **Secret Scanning**: gitleaks (local)
- **Vulnerability Scanning**: bandit + safety (local)
- **Crypto Review**: All crypto code reviewed by harold-security (Opus 4.6)
- **No secrets in code**: Enforced by pre-commit hooks

### Documentation
- **ADRs**: All major decisions documented
- **README**: Internet Historian quality narratives
- **API Docs**: Comprehensive docstrings
- **Failure Modes**: Dark Harold documents what breaks

---

## Success Metrics

**Agent Effectiveness**:
- 90% of tasks completed by appropriate specialist agent
- <5% tasks require agent reassignment
- Context loss <1% (shared memory effectiveness)

**Model Routing**:
- 90% of tasks handled by local models (privacy goal)
- <10% cloud API usage (cost optimization)
- 100% security tasks routed to Opus 4.6

**Quality**:
- 100% code passes local quality checks before commit
- Zero secrets in committed code (gitleaks)
- >80% test coverage maintained

---

## Open Questions

1. **Agent Selection**: Manual vs. automatic based on task type?
   - harold-planner: Manual for now, auto-route in future

2. **Context Window**: How much shared memory per agent request?
   - harold-researcher: 512-token chunks, relevance-ranked

3. **Model Fallback**: What if local models are offline?
   - harold-implementer: Gracefully fallback to cloud with warning

4. **Cost Tracking**: How do we measure cloud API usage?
   - harold-planner: Log all cloud calls, monthly cost reports

---

## Harold's Meta-Commentary

*"Building an AI agent system to build an AI-powered privacy tool is peak 2026 software development. Harold documents this recursion with appropriate cynicism."* — harold-documenter

*"Six specialized Harolds is either brilliant division of labor or deeply concerning multiple personality disorder. Time will tell."* — harold-planner  

*"Dark Harold insists all agent decisions are logged. We'll need those logs when the agents inevitably break."* — harold-security

---

**Status**: Implemented (this document describes current architecture)  
**Next Steps**: Refine model routing based on usage patterns
