# 😐 Anemochory Protocol: Multi-Layer Origin Obfuscation

**Feature**: 001-anemochory-protocol  
**Status**: Research Phase  
**Priority**: P0 (Foundation for all features)  
**Owner**: harold-planner + harold-security

---

## Overview

Like seeds dispersed by wind with untraceable origins, the Anemochory Protocol provides network-level anonymization that goes far beyond VPNs. Multi-layer encryption combined with pseudo-random routing creates origin obfuscation resistant to traffic analysis and timing attacks.

---

## Problem Statement

**Current State**: Users relying on VPNs still leak metadata (timing, traffic patterns, ISP correlation). Social media scrubbing without origin obfuscation reveals the requester's identity.

**Dark Harold's Threat Model**: 
- Traffic analysis correlates VPN exit nodes to destinations
- Timing attacks reveal request patterns
- ISP-level logging creates paper trails despite tunnel encryption
- Data brokers track even "anonymized" removal requests

**Desired State**: True origin obfuscation where packet paths are:
1. Non-deterministic (pseudo-random routing)
2. Instruction-carrying (each layer independent)
3. Self-destructing (routing data dropped after use)
4. Analysis-resistant (timing and traffic decorrelation)

---

## User Stories

### As a privacy-conscious user
**I want** to access social media platforms without revealing my actual location or ISP  
**So that** my removal requests cannot be correlated back to me  
**Acceptance**: Origin IP cannot be determined even with ISP cooperation

### As a scrubbing engine
**I need** to make bulk deletion requests without pattern detection  
**So that** platforms cannot fingerprint or rate-limit my operations  
**Acceptance**: Requests appear from random, uncorrelated sources

### As a security researcher
**I want** to verify anonymization efficacy through adversarial testing  
**So that** we can validate resistance to known attacks  
**Acceptance**: Timing attacks, traffic analysis, and correlation attacks fail

---

## Requirements

### Functional

**MUST HAVE**:
- Multi-layer packet encryption (nested, instruction-carrying)
- Pseudo-random routing through cooperative nodes
- Instruction layer dropping (hop-by-hop data destruction)
- Configurable hop count (3-7 hops recommended)
- Network storm prevention (TTL, loop detection)
- Entry node diversity (prevent single-point tracking)
- Exit node rotation (decorrelate destination patterns)

**SHOULD HAVE**:
- Traffic padding (constant packet sizes)
- Timing jitter (prevent timing correlation)
- Dummy traffic generation (hide real patterns)
- DHT-based node discovery (decentralized)
- Reputation system for nodes (prevent Sybil attacks)

**COULD HAVE**:
- Incentive layer for node operators (optional payment)
- Bandwidth proofs (prevent freeloading)
- Geographic path distribution (cross-border routing)

**MUST NOT**:
- Use fixed routing paths (deterministic = traceable)
- Log complete paths at any node (security violation)
- Allow path reconstruction from intercepted packets
- Create network storms through infinite loops

### Non-Functional

**Performance**:
- Latency target: <2 seconds per request (with 5 hops)
- Throughput: Support bulk operations (100s of requests)
- Scalability: Handle multi-user concurrent access

**Security**:
- Encryption: Modern symmetric crypto (ChaCha20-Poly1305 or AES-GCM)
- Key exchange: Ephemeral keys (no long-term secrets)
- Padding: Constant packet sizes resistant to traffic analysis
- Node trust: Zero-knowledge routing (no node sees full path)

**Reliability**:
- Node failure handling: Automatic rerouting
- Packet loss tolerance: Retry with new path
- Availability target: 99% uptime with redundant nodes

---

## Constraints

**Technical**:
- Python 3.14 compatibility (all libraries must support)
- Cross-platform (Linux, macOS, Windows if possible)
- No kernel modules required (userspace only)
- Works behind NAT/firewalls

**Legal/Ethical**:
- Not designed for illegal activity (constitutional principle)
- Respects ToS where legally required
- Cannot prevent determined nation-state actors (acknowledge limitations)
- Documented limitations in README (Harold's transparency)

**Resource**:
- Minimize bandwidth overhead (<30% packet expansion)
- CPU-friendly crypto (no excessive hashing)
- Memory: <100MB per connection

---

## Success Metrics

**Anonymization Efficacy**:
- Origin IP unrecoverable even with N-1 compromised nodes
- Timing attacks fail with >95% confidence
- Traffic analysis cannot correlate requests

**Performance**:
- 90th percentile latency <2 seconds
- Throughput: 100 requests/minute sustained
- Packet loss <5%

**Security**:
- Zero successful deanonymizations in testing
- Adversarial testing by harold-security passes
- External security audit (post-MVP)

---

## Open Questions

1. **Node infrastructure**: Self-hosted only or public node network?
   - harold-planner leaning: self-hosted for trustworthiness, public for scale

2. **Crypto library**: `cryptography` vs `pynacl` vs custom?
   - harold-security demands: review both, prefer audited libraries

3. **Routing algorithm**: Onion routing variant or custom?
   - harold-planner investigating: Tor-like vs I2P-like vs novel

4. **Packet format**: Custom protocol or tunnel through existing (DNS, ICMP)?
   - harold-researcher task: evaluate covert channel options

5. **Python 3.14 network libraries**: Which async framework?
   - harold-researcher task: research trio/anyio/asyncio compatibility

---

## Dependencies

**Research Tasks** (harold-researcher):
- Python 3.14 networking library evaluation
- Cryptography library compatibility check
- Onion routing implementation review
- Covert channel protocol analysis

**Design Tasks** (harold-planner):
- Packet format specification
- Routing algorithm design
- Node discovery protocol
- Key exchange mechanism

**Security Tasks** (harold-security):
- Threat model comprehensive review
- Crypto primitive selection
- Attack vector analysis
- Adversarial testing plan

---

## Timeline

**Phase 0** (Current): Research & Specification (2 weeks)
- Library evaluation (harold-researcher)
- Threat modeling (harold-security)
- Protocol specification (harold-planner)

**Phase 1**: Core Protocol Implementation (4 weeks)
- Packet encryption/decryption
- Routing algorithm
- Node communication
- Unit tests (harold-tester)

**Phase 2**: Node Infrastructure (3 weeks)
- Node discovery (DHT or bootstrap)
- Reputation system
- Health monitoring

**Phase 3**: Integration & Testing (2 weeks)
- Scrubbing engine integration
- Adversarial testing (harold-security)
- Performance optimization

**Phase 4**: Documentation & Audit (1 week)
- Narrative documentation (harold-documenter)
- Security audit preparation
- README updates

---

## Harold's Commentary

*"Anonymization is like hiding pain behind a smile. The more layers, the more convincing. But Dark Harold reminds us: every anonymization system has been broken eventually. We design for delay, not invincibility."* — harold-planner

*"This protocol will definitely not be attacked by nation-states with unlimited budgets. 😐 But it should handle data brokers and script kiddies with confidence."* — harold-security

*"Documenting anonymization protocols feels like explaining a magic trick. By the time you understand it, you know it's not magic. Just very clever misdirection."* — harold-documenter

---

**Next Steps**: See [research.md](research.md) for library evaluation progress.
