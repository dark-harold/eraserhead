# 😐 Scrubbing Engine: Systematically Erasing Harold's Digital Footprint

**Feature**: 002-scrubbing-engine  
**Status**: Planning Phase  
**Priority**: P1 (Core functionality)  
**Owner**: harold-implementer + harold-researcher  
**Depends On**: 001-anemochory-protocol (for anonymized requests)

---

## Overview

Like Harold trying to scrub embarrassing stock photos from the internet (spoiler: they're everywhere), the Scrubbing Engine provides systematic, automated deletion of user data from social media platforms, data brokers, and public databases. Powered by the Anemochory Protocol for true anonymization.

---

## Problem Statement

**Current State**: 
- Manual data deletion is tedious and incomplete
- Data brokers re-aggregate removed data
- Platforms make deletion deliberately difficult
- Tracking deletion progress is manual and error-prone
- Removal requests reveal the requester's identity

**Dark Harold's Threat Model**:
- Platforms correlate removal patterns to identify users
- Data brokers share removal requests across networks
- API rate limits prevent bulk deletion
- Incomplete deletions leave digital breadcrumbs
- Manual processes miss newly aggregated data

**Desired State**: 
- Automated, systematic data deletion across platforms
- Anonymized requests (via Anemochory) prevent tracking
- Progress tracking with verification
- Continuous monitoring for re-aggregated data
- Platform-agnostic adapters for scalability

---

## User Stories

### As a privacy-conscious user
**I want** to delete all my data from major social platforms with one command  
**So that** my digital footprint is minimized without manual effort  
**Acceptance**: Single command deletes from Facebook, Twitter, Instagram, LinkedIn

### As a data erasure requester
**I need** verification that deletion actually occurred  
**So that** I can trust the platform honored my request  
**Acceptance**: System provides proof of deletion with screenshots/API responses

### As someone fleeing digital harassment
**I want** continuous monitoring for re-aggregated data  
**So that** deleted data doesn't reappear from backups or data brokers  
**Acceptance**: System alerts when removed data reappears

### As a developer
**I need** to add new platform adapters easily  
**So that** the scrubbing engine scales with new platforms  
**Acceptance**: New platform adapter requires <200 lines of code

---

## Requirements

### Functional

**MUST HAVE**:
- **Platform Adapters**: Pluggable adapters for each platform/service
  - Social Media: Facebook, Twitter, Instagram, LinkedIn, TikTok
  - Data Brokers: Known aggregate sites (research phase)
  - Public Records: Google cache, Wayback Machine markers
- **Authentication Management**: Secure credential storage (encrypted vault)
- **Action Queue**: Task queue for deletion operations
  - Priority levels (urgent, standard, background)
  - Retry logic with exponential backoff
  - Rate limit compliance per platform
- **Verification System**: Confirm deletions actually occurred
  - Screenshot capture of deletion confirmations
  - API response logging
  - Post-deletion verification checks
- **Progress Tracking**: 
  - Per-platform status dashboards
  - Deletion success/failure metrics
  - Estimated completion times
- **Anonymized Requests**: All operations routed through Anemochory Protocol

**SHOULD HAVE**:
- **Monitoring & Alerting**: Continuous checks for re-aggregated data
  - Scheduled verification scans
  - Alert when deleted data reappears
  - Configurable scan intervals
- **Multi-account Support**: Handle multiple user accounts per platform
- **Selective Deletion**: Choose what to delete (posts, friends, likes, comments)
- **Dry-run Mode**: Preview deletions without executing
- **Export Before Delete**: Backup data before erasing (GDPR compliance)

**COULD HAVE**:
- **Obfuscation Mode**: Replace content with noise before deletion
  - Randomize profile data
  - Replace posts with lorem ipsum variants
  - Prevents deleted data recovery from backups
- **Scheduled Scrubbing**: Recurring deletion tasks
- **Collaborative Deletion**: Share scrubbing recipes/scripts
- **Platform API Mocking**: Testing without real API calls

**MUST NOT**:
- Violate platform ToS where legally enforced
- Store plaintext credentials (encrypt everything)
- Make removal requests without user confirmation (unless configured)
- Delete data we don't have permission to delete

### Non-Functional

**Performance**:
- Handle bulk operations (1000s of posts)
- Process deletion queue with <5min latency per task
- Parallel processing across platforms (up to 10 concurrent)

**Security**:
- Encrypted credential storage (Fernet or similar)
- All requests routed through Anemochory (no direct platform access)
- Audit logging of all deletion operations
- No cleartext sensitive data in logs

**Reliability**:
- Handle transient failures gracefully (retry logic)
- Resume interrupted deletion batches
- Idempotent operations (safe to retry)
- 99% task completion rate

**Usability**:
- CLI interface for power users
- Web dashboard (future) for visual progress tracking
- Clear error messages (Harold's dry humor + actionable advice)
- Progress bars for long-running operations

---

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────┐
│ Scrubbing Engine                                     │
├─────────────────────────────────────────────────────┤
│                                                       │
│  ┌──────────────┐         ┌───────────────┐         │
│  │ CLI/Web UI   │────────>│ Task Scheduler│         │
│  └──────────────┘         └───────┬───────┘         │
│                                    │                 │
│  ┌─────────────────────────────────▼──────────────┐ │
│  │          Platform Adapter Layer                 │ │
│  │  ┌─────────────────────────────────────────┐   │ │
│  │  │ Facebook │ Twitter │ Instagram │ ... │   │   │ │
│  │  └─────────────────────────────────────────┘   │ │
│  └──────────────────────┬──────────────────────────┘ │
│                         │                            │
│  ┌──────────────────────▼───────────────────┐       │
│  │      Anemochory Request Router           │       │
│  │  (Anonymize all platform API calls)      │       │
│  └──────────────────────┬───────────────────┘       │
│                         │                            │
└─────────────────────────┼────────────────────────────┘
                          │
                  ┌───────▼────────┐
                  │   Internet     │
                  │  (Platforms)   │
                  └────────────────┘
```

### Data Flow

1. **User initiates scrubbing**: CLI command or web interface
2. **Task Creation**: Scrubbing tasks added to queue (per platform)
3. **Adapter Selection**: Route task to appropriate platform adapter
4. **Anonymized Execution**: Adapter sends requests via Anemochory
5. **Verification**: Confirm deletion with follow-up checks
6. **Logging**: Record success/failure, store audit trail

### Platform Adapter Interface

All adapters must implement:

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from pydantic import BaseModel

class DeletionTask(BaseModel):
    """Represents a single deletion operation."""
    task_id: str
    platform: str
    resource_type: str  # "post", "comment", "profile", "friend"
    resource_id: str
    priority: int = 5
    retry_count: int = 0
    max_retries: int = 3

class DeletionResult(BaseModel):
    """Result of a deletion operation."""
    task_id: str
    success: bool
    verified: bool
    error_message: str | None = None
    proof: Dict[str, Any] | None = None  # Screenshots, API responses

class PlatformAdapter(ABC):
    """Base class for all platform adapters."""
    
    @abstractmethod
    async def authenticate(self, credentials: Dict[str, str]) -> bool:
        """Authenticate with the platform."""
        pass
    
    @abstractmethod
    async def delete(self, task: DeletionTask) -> DeletionResult:
        """Execute a deletion task."""
        pass
    
    @abstractmethod
    async def verify_deletion(self, task: DeletionTask) -> bool:
        """Verify deletion was successful."""
        pass
    
    @abstractmethod
    async def list_resources(self, resource_type: str) -> List[str]:
        """List all deletable resources of a type."""
        pass
```

---

## Constraints

**Technical**:
- Python 3.14 compatibility
- Async/await architecture (trio or asyncio)
- All network requests through Anemochory (no direct connections)
- Credential encryption using `cryptography` library
- Rate limit compliance (respect platform limits)

**Legal/Ethical**:
- Comply with platform ToS where legally required
- Support GDPR/CCPA data export before deletion
- No deletion of data we don't own
- User confirmation required (except when configured otherwise)

**Resource**:
- Memory: <200MB during bulk operations
- Disk: <100MB for task queue and logs
- Network: Minimize API calls (batch where possible)

---

## Success Metrics

**Functionality**:
- 95% task completion rate across all platforms
- <1% false deletion reports (claimed deleted but still exists)
- <5 minute average time per deletion task

**Coverage**:
- 5+ platform adapters at MVP (Facebook, Twitter, Instagram, LinkedIn, Google)
- 10+ data broker adapters within 6 months

**Reliability**:
- 99% uptime for scrubbing scheduler
- Zero credential leaks (encrypted storage)
- <1% data loss in task queue

---

## Open Questions

1. **Platform API Stability**: What's our strategy when platforms change APIs?
   - harold-implementer: Version adapters, auto-detect API changes

2. **Legal Risks**: How do we handle platforms that forbid automation?
   - harold-security: Document risks, user assumes liability, respect blocking

3. **Credential Storage**: Where do encrypted credentials live?
   - harold-security: SQLite with Fernet encryption, user-controlled keys

4. **Verification Timing**: How soon after deletion do we verify?
   - harold-planner: Immediate + 24h delayed + 7 day check

5. **Obfuscation Ethics**: Is replacing data with noise ethical/legal?
   - harold-researcher: Research GDPR implications, make optional

---

## Dependencies

**Research Tasks** (harold-researcher):
- Platform API research (auth flows, rate limits, deletion endpoints)
- Data broker identification and categorization
- Python async library evaluation (trio vs asyncio)
- Screenshot/proof capture libraries

**Design Tasks** (harold-planner):
- Adapter interface design
- Task queue architecture
- Verification workflow design
- Error handling strategy

**Implementation Tasks** (harold-implementer):
- Core scrubbing engine framework
- First 3 platform adapters (Facebook, Twitter, Instagram)
- Credential vault implementation
- Anemochory integration

**Security Tasks** (harold-security):
- Credential encryption review
- Audit logging design
- Platform ToS legal review
- Rate limit evasion ethics check

**Testing Tasks** (harold-tester):
- Adapter test mocks
- Integration tests
- Deletion verification tests
- Failure scenario testing

---

## Timeline

**Phase 0** (Current): Research & Specification (2 weeks)
- Platform API research (harold-researcher)
- Legal/ethical review (harold-security)
- Architecture design (harold-planner)

**Phase 1**: Core Framework (3 weeks)
- Adapter interface + base classes
- Task queue implementation
- Credential vault
- Anemochory integration

**Phase 2**: Initial Adapters (4 weeks)
- Facebook adapter
- Twitter adapter
- Instagram adapter
- Verification system

**Phase 3**: Data Broker Support (3 weeks)
- Research data broker landscape
- Implement 5 data broker adapters
- Monitoring & alerting system

**Phase 4**: Polish & Documentation (2 weeks)
- CLI refinement
- Comprehensive testing
- Narrative documentation (harold-documenter)
- User guide with Harold's commentary

---

## Harold's Commentary

*"Deleting data from the internet is like trying to un-ring a bell. By the time you realize it was a mistake, the sound has already echoed across a thousand data broker servers. But Harold tries anyway. 😐"* — harold-implementer

*"Every platform has a different flavor of 'we make deletion as annoying as possible.' Dark Harold catalogs these patterns. The scrubbing engine weaponizes that knowledge."* — harold-researcher

*"If you're not backing up data before deletion, you're trusting platforms to have actually deleted it. Harold trusts no one."* — harold-security

---

**Next Steps**: 
1. Research platform API documentation → harold-researcher
2. Design adapter interface → harold-planner
3. Implement credential vault → harold-implementer + harold-security
