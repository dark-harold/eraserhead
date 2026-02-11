# 😐 ADR-002: Packet Format Specification

**Status**: Proposed  
**Date**: February 10, 2026  
**Deciders**: harold-planner, harold-security (Dark Harold)  
**Context**: Week 4 implementation, addresses security review findings

---

## Context and Problem Statement

The Anemochory Protocol requires a nested packet format for 3-7 hop onion routing with the following requirements:

1. **Multi-layer encryption**: Each hop can only decrypt its own layer
2. **Traffic analysis resistance**: Constant packet size, randomized padding
3. **Security requirements** (from SECURITY-REVIEW-CRYPTO.md):
   - Replay protection (timestamp validation)
   - Layer binding (prevent layer stripping/confusion)
   - Forward secrecy support (ephemeral session keys)
   - Sequence number tracking
4. **Routing information**: Each hop needs to know the next destination
5. **Payload delivery**: Final destination receives actual data

**Key Constraints**:
- Fixed packet size (1024 bytes) for traffic analysis resistance
- ChaCha20-Poly1305 overhead: 16 bytes (auth tag) + 12 bytes (nonce) = 28 bytes per layer
- Must support 3-7 hops efficiently
- Must bind metadata via AEAD associated data

---

## Decision Drivers

* **Security**: Address Critical Issues #2 (replay protection) and #5 (associated data binding)
* **Efficiency**: Minimize overhead while supporting maximum path length
* **Implementability**: Clear structure for parsing and encryption
* **Forward compatibility**: Support for future protocol extensions
* **Timing jitter**: Enable protocol-level timing correlation resistance

---

## Considered Options

### Option 1: Fixed Layer Structure (Tor-like)

**Format**:
```
[Layer N Header (fixed size) | Layer N Payload (fixed size)]
[Layer N-1 Header | Layer N-1 Payload]
...
[Layer 1 Header | Layer 1 Payload]
```

**Pros**: Simple parsing, predictable offsets  
**Cons**: Wastes space with max-hop padding, complex size calculations

---

### Option 2: Nested Onion (Selected)

**Format**: Each layer wraps the previous, fixed total size

**Pros**: 
- Natural onion routing semantics
- Each hop only sees its layer + ciphertext blob
- Efficient padding strategy
- Aligns with security requirements

**Cons**: Requires careful size accounting per layer

---

## Decision Outcome

**Chosen**: **Option 2 - Nested Onion Format**

Packet structure from outermost to innermost layer:

```
TOTAL PACKET SIZE: 1024 bytes (constant)

┌─────────────────────────────────────────────────────────────┐
│ Layer N (Outermost Hop)                                     │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ Header (unencrypted)                          [8 bytes]│  │
│ │  - version: u8                                [1 byte] │  │
│ │  - hop_count: u8                              [1 byte] │  │
│ │  - layer_index: u8  (N, N-1, ..., 1)         [1 byte] │  │
│ │  - flags: u8                                  [1 byte] │  │
│ │  - timestamp: u32 (Unix epoch seconds)        [4 bytes]│  │
│ │                                                          │  │
│ │ Encrypted Payload                           [1016 bytes]│  │
│ │ ┌─────────────────────────────────────────────────────┐│  │
│ │ │ Nonce (randomized per packet)        [12 bytes]    ││  │
│ │ │                                                      ││  │
│ │ │ Layer Routing Info (plaintext after decrypt)        ││  │
│ │ │  - next_hop_address: IPv6 or Onion address[16 bytes]││  │
│ │ │  - next_hop_port: u16                     [2 bytes]││  │
│ │ │  - sequence_number: u64                   [8 bytes]││  │
│ │ │  - session_id: u128 (for key derivation)  [16 bytes]││  │
│ │ │  - padding_length: u16                    [2 bytes]││  │
│ │ │                                           [56 total] ││  │
│ │ │                                                      ││  │
│ │ │ Inner Packet (Layer N-1) or Final Payload [944 bytes]││  │
│ │ │  (recursively encrypted)                            ││  │
│ │ │                                                      ││  │
│ │ │ Random Padding (for final payload)     [variable]  ││  │
│ │ │                                                      ││  │
│ │ │ Authentication Tag (Poly1305)            [16 bytes]││  │
│ │ └─────────────────────────────────────────────────────┘│  │
│ └────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘

Associated Data (bound via AEAD, not transmitted):
  - layer_index: u8
  - hop_count: u8
  - timestamp: u32
  (prevents layer stripping and replay attacks)
```

---

## Detailed Specification

### Protocol Constants

```python
# Packet structure sizes
PACKET_SIZE = 1024                    # Total packet size (constant)
HEADER_SIZE = 8                       # Unencrypted header
NONCE_SIZE = 12                       # ChaCha20-Poly1305 nonce
AUTH_TAG_SIZE = 16                    # Poly1305 authentication tag
ROUTING_INFO_SIZE = 56                # Routing information per layer

# Derived sizes
ENCRYPTED_PAYLOAD_SIZE = PACKET_SIZE - HEADER_SIZE  # 1016 bytes
INNER_PACKET_SIZE = ENCRYPTED_PAYLOAD_SIZE - NONCE_SIZE - ROUTING_INFO_SIZE - AUTH_TAG_SIZE  # 944 bytes

# Layer overhead (encryption + routing)
LAYER_OVERHEAD = NONCE_SIZE + ROUTING_INFO_SIZE + AUTH_TAG_SIZE  # 84 bytes per layer

# Address types
ADDRESS_TYPE_IPV4 = 0x01              # IPv4 (in IPv6 mapping)
ADDRESS_TYPE_IPV6 = 0x02              # IPv6
ADDRESS_TYPE_ONION_V3 = 0x03          # Tor-like onion address
```

### Header Format (Unencrypted, 8 bytes)

```python
struct PacketHeader:
    version: u8         # Protocol version (currently 0x01)
    hop_count: u8       # Total hops in path (3-7)
    layer_index: u8     # Current layer (N, N-1, ..., 1)
    flags: u8           # Bit flags:
                        #   bit 0: is_final_payload (1 = last hop)
                        #   bit 1: requires_ack (future: reliability)
                        #   bit 2-7: reserved (must be 0)
    timestamp: u32      # Packet creation time (Unix epoch seconds, network byte order)
```

**Design Rationale**:
- **version**: Future protocol upgrades
- **hop_count**: Receiver validates against expected path length
- **layer_index**: Enables hop count verification, prevents layer confusion
- **timestamp**: Replay protection (nodes reject packets >60 seconds old)
- **flags**: Extensibility for future features

### Routing Information (Encrypted, 56 bytes)

```python
struct LayerRoutingInfo:
    next_hop_address: [u8; 16]   # IPv6 or onion address (16 bytes)
                                 # IPv4: mapped as ::ffff:0:0/96
                                 # Onion v3: truncated onion address
    next_hop_port: u16           # Destination port (network byte order)
    sequence_number: u64         # Per-session sequence (prevents reordering)
    session_id: [u8; 16]         # Session identifier (UUID v4)
                                 # Used for ephemeral key derivation
    padding_length: u16          # For final payload: length of padding
                                 # For intermediate hops: 0
```

**Design Rationale**:
- **next_hop_address**: Supports both clearnet (IPv4/IPv6) and onion routing
- **sequence_number**: Detects packet reordering attacks
- **session_id**: Enables forward secrecy via per-session key derivation
- **padding_length**: Allows variable payload sizes within fixed packet

### Encryption Process (Per Layer)

For each layer `i` (from innermost `1` to outermost `N`):

```python
def encrypt_layer(
    inner_packet: bytes,        # Previous layer's ciphertext (or final payload)
    routing_info: LayerRoutingInfo,
    layer_key: bytes,           # Derived from session_id + master_key
    layer_index: int,
    hop_count: int,
    timestamp: int
) -> bytes:
    """
    Encrypts a single layer of the onion packet.
    
    😐 Each layer wraps the previous. Like an onion, but with more crying.
    """
    # Generate random nonce (MUST be unique per encryption)
    nonce = secrets.token_bytes(NONCE_SIZE)
    
    # Serialize routing info
    routing_bytes = serialize_routing_info(routing_info)
    
    # Construct plaintext: routing_info + inner_packet
    plaintext = routing_bytes + inner_packet
    
    # Pad to exact inner packet size (944 bytes)
    if len(plaintext) < INNER_PACKET_SIZE:
        padding = secrets.token_bytes(INNER_PACKET_SIZE - len(plaintext))
        plaintext = plaintext + padding
    
    # Associated data binding (prevents layer stripping, replay)
    associated_data = struct.pack('>BBL', layer_index, hop_count, timestamp)
    
    # Encrypt with ChaCha20-Poly1305
    cipher = ChaCha20Poly1305(layer_key)
    ciphertext_with_tag = cipher.encrypt(
        nonce=nonce,
        plaintext=plaintext,
        associated_data=associated_data
    )
    
    # Construct encrypted payload: nonce + ciphertext + tag
    encrypted_payload = nonce + ciphertext_with_tag
    
    return encrypted_payload
```

### Decryption Process (Per Hop)

Each node performs:

```python
def decrypt_layer(
    packet: bytes,              # Full 1024-byte packet
    layer_key: bytes           # Derived from session_id + node's master key
) -> (LayerRoutingInfo, bytes):
    """
    Decrypts one layer, extracts routing info and inner packet.
    
    🌑 Validate EVERYTHING. Trust NOTHING. Assume nation-state adversary.
    """
    # Parse header (unencrypted)
    header = parse_header(packet[:HEADER_SIZE])
    
    # Validate timestamp (replay protection)
    current_time = time.time()
    packet_age = current_time - header.timestamp
    if packet_age > 60 or packet_age < -5:  # 60s tolerance, 5s clock skew
        raise ReplayError("Packet timestamp outside valid window")
    
    # Extract encrypted payload
    encrypted_payload = packet[HEADER_SIZE:]
    nonce = encrypted_payload[:NONCE_SIZE]
    ciphertext_with_tag = encrypted_payload[NONCE_SIZE:]
    
    # Reconstruct associated data for AEAD verification
    associated_data = struct.pack(
        '>BBL',
        header.layer_index,
        header.hop_count,
        header.timestamp
    )
    
    # Decrypt with ChaCha20-Poly1305
    cipher = ChaCha20Poly1305(layer_key)
    try:
        plaintext = cipher.decrypt(
            nonce=nonce,
            ciphertext=ciphertext_with_tag,
            associated_data=associated_data
        )
    except InvalidTag:
        raise DecryptionError("Authentication tag verification failed")
    
    # Parse routing info
    routing_info = parse_routing_info(plaintext[:ROUTING_INFO_SIZE])
    
    # Extract inner packet (next layer or final payload)
    inner_packet = plaintext[ROUTING_INFO_SIZE:]
    
    # Validate sequence number (prevent replay/reordering)
    validate_sequence_number(routing_info.session_id, routing_info.sequence_number)
    
    # Check if final hop
    if header.flags & 0x01:  # is_final_payload bit
        # Remove padding from final payload
        payload_length = INNER_PACKET_SIZE - routing_info.padding_length
        final_payload = inner_packet[:payload_length]
        return routing_info, final_payload
    else:
        # Reconstruct packet for next hop
        next_header = PacketHeader(
            version=header.version,
            hop_count=header.hop_count,
            layer_index=header.layer_index - 1,
            flags=header.flags,
            timestamp=header.timestamp  # Preserve original timestamp
        )
        next_packet = serialize_header(next_header) + inner_packet
        return routing_info, next_packet
```

---

## Security Properties

### Replay Protection (Addresses Critical Issue #2)

**Mechanism**:
1. **Timestamp validation**: Nodes reject packets >60 seconds old
2. **Sequence numbers**: Per-session monotonic counter prevents reordering
3. **Seen-nonce registry**: (Week 5) Track nonces in bloom filter

**Rationale**: Multi-layered defense. Timestamp prevents long-term replay, sequence numbers prevent reordering within session.

### Layer Binding (Addresses High Priority Issue #5)

**Mechanism**: Associated data binds `layer_index`, `hop_count`, and `timestamp` to ciphertext via AEAD.

**Attack Prevented**:
- **Layer stripping**: Adversary cannot remove outer layers (auth tag verification fails)
- **Layer confusion**: Cannot swap layers between packets (layer_index bound)
- **Hop count tampering**: Cannot modify expected path length

### Forward Secrecy Support (Addresses Critical Issue #1)

**Mechanism**: `session_id` in routing info enables per-session key derivation.

**Key Derivation**:
```python
def derive_session_layer_key(
    master_key: bytes,
    session_id: bytes,      # Unique per session (from ephemeral DH)
    layer_index: int,
    hop_count: int
) -> bytes:
    """
    Derive layer key with session binding for forward secrecy.
    
    🌑 Session compromise != historical compromise
    """
    info = f"anemochory-session-{session_id.hex()}-layer-{layer_index}-of-{hop_count}"
    kdf = HKDF(
        algorithm=hashes.SHA256(),
        length=KEY_SIZE,
        salt=session_id[:16],  # Use session_id as salt (public, random)
        info=info.encode('utf-8')
    )
    return kdf.derive(master_key)
```

**Future Integration** (Week 5):
- Ephemeral X25519 key exchange establishes `session_id`
- Session keys rotate every 10,000 packets or 1 hour
- Old session keys deleted (forward secrecy achieved)

---

## Size Calculations

### Maximum Path Length

With fixed 1024-byte packet:
- Header: 8 bytes (unencrypted)
- Per-layer overhead: 84 bytes (nonce + routing + tag)
- Minimum payload: 64 bytes (reasonable minimum)

**Maximum hops**: `(1024 - 8 - 64) / 84 ≈ 11 hops`

**Protocol limit**: 7 hops (conservative, ensures ample payload space)

### Layer Size Reduction

| Layer | Total Size | Header | Encrypted | Inner Size | Overhead |
|-------|-----------|--------|-----------|-----------|----------|
| 7 (outer) | 1024 | 8 | 1016 | 944 | 80 |
| 6 | 944 | 0 | 944 | 860 | 84 |
| 5 | 860 | 0 | 860 | 776 | 84 |
| 4 | 776 | 0 | 776 | 692 | 84 |
| 3 | 692 | 0 | 692 | 608 | 84 |
| 2 | 608 | 0 | 608 | 524 | 84 |
| 1 (inner) | 524 | 0 | 524 | 440 | 84 |
| Payload | 440 | - | - | - | - |

**Final payload capacity**: 440 bytes for 7-hop path, 692 bytes for 3-hop path

---

## Implementation Notes

### Timing Jitter (Addresses High Priority Issue #7)

**Protocol Layer** (not in packet format itself):
```python
async def forward_packet_with_jitter(packet: bytes, next_hop: Address):
    """
    😐 Make timing analysis harder by adding random delays.
    🌑 Nation-states have microsecond precision. We add milliseconds. It helps.
    """
    # Random jitter: 50-150ms (specified in ADR-001)
    jitter_ms = secrets.randbelow(100) + 50
    await asyncio.sleep(jitter_ms / 1000.0)
    
    # Forward packet
    await send_to_next_hop(packet, next_hop)
```

### Sequence Number Validation

```python
class SessionState:
    """Track per-session state for replay/reordering detection."""
    
    def __init__(self, session_id: bytes):
        self.session_id = session_id
        self.last_sequence = 0
        self.seen_nonces: Set[bytes] = set()  # Or bloom filter
    
    def validate_sequence(self, seq: int) -> bool:
        """
        🌑 Monotonic sequence numbers prevent reordering attacks.
        """
        if seq <= self.last_sequence:
            return False  # Replay or reorder detected
        self.last_sequence = seq
        return True
```

### Nonce Collision Detection (Addresses High Priority Issue #8)

```python
def encrypt_with_collision_detection(
    cipher: ChaCha20Poly1305,
    plaintext: bytes,
    associated_data: bytes,
    seen_nonces: Set[bytes]
) -> bytes:
    """
    🌑 Generate unique nonce with collision detection.
    Birthday paradox: 2^48 encryptions before 50% collision probability.
    We enforce uniqueness anyway because paranoia.
    """
    max_attempts = 10
    for attempt in range(max_attempts):
        nonce = secrets.token_bytes(NONCE_SIZE)
        if nonce not in seen_nonces:
            seen_nonces.add(nonce)
            return cipher.encrypt(nonce, plaintext, associated_data)
    
    # RNG failure - entropy exhaustion?
    raise CryptographicError("Nonce collision after 10 attempts - RNG compromised?")
```

---

## Testing Strategy

### Unit Tests

```python
def test_packet_size_constant():
    """All packets must be exactly 1024 bytes."""
    for hop_count in range(3, 8):
        packet = create_onion_packet(payload, hop_count)
        assert len(packet) == PACKET_SIZE

def test_layer_binding_prevents_stripping():
    """Tampering with layer_index should fail authentication."""
    packet = create_packet(...)
    
    # Modify layer_index in header
    tampered = bytearray(packet)
    tampered[2] = tampered[2] - 1  # Decrement layer_index
    
    with pytest.raises(DecryptionError):
        decrypt_layer(bytes(tampered), layer_key)

def test_timestamp_replay_rejected():
    """Old packets should be rejected."""
    old_timestamp = int(time.time()) - 120  # 2 minutes old
    packet = create_packet(timestamp=old_timestamp)
    
    with pytest.raises(ReplayError):
        decrypt_layer(packet, layer_key)

def test_sequence_number_reordering_detected():
    """Out-of-order packets should fail validation."""
    session = SessionState(session_id)
    
    assert session.validate_sequence(1) == True
    assert session.validate_sequence(2) == True
    assert session.validate_sequence(1) == False  # Replay
    assert session.validate_sequence(3) == True
```

### Integration Tests

```python
def test_full_7_hop_roundtrip():
    """Create, encrypt, forward, decrypt through 7 hops."""
    payload = b"Test payload"
    path = generate_random_path(7)
    
    # Build onion
    packet = build_onion_packet(payload, path)
    assert len(packet) == PACKET_SIZE
    
    # Simulate forwarding through all hops
    current_packet = packet
    for hop_index, hop in enumerate(path):
        routing_info, next_packet = decrypt_layer(current_packet, hop.key)
        
        if hop_index < len(path) - 1:
            # Intermediate hop
            assert routing_info.next_hop_address == path[hop_index + 1].address
            current_packet = next_packet
        else:
            # Final hop
            assert next_packet == payload

def test_timing_jitter_variance():
    """Verify timing jitter adds 50-150ms variance."""
    timings = []
    for _ in range(100):
        start = time.perf_counter()
        asyncio.run(forward_packet_with_jitter(packet, next_hop))
        elapsed = time.perf_counter() - start
        timings.append(elapsed)
    
    # Verify jitter range
    assert min(timings) >= 0.050
    assert max(timings) <= 0.200  # 150ms + overhead
    assert statistics.stdev(timings) > 0.020  # Significant variance
```

---

## Consequences

### Positive

* ✅ **Replay protection**: Timestamp + sequence numbers prevent replay attacks
* ✅ **Layer binding**: AEAD associated data prevents layer stripping/confusion
* ✅ **Forward secrecy ready**: Session ID enables ephemeral key derivation
* ✅ **Traffic analysis resistance**: Fixed size, randomized padding, timing jitter support
* ✅ **Flexible routing**: Supports clearnet and onion addresses
* ✅ **Efficient**: 440-byte payload for max 7 hops (acceptable overhead)

### Negative

* ⚠️ **Timestamp synchronization**: Requires loose clock sync (60s tolerance acceptable)
* ⚠️ **Session state overhead**: Must track seen nonces and sequences per session
* ⚠️ **Fixed packet size**: Small payloads waste bandwidth (future: multiple size classes)
* ⚠️ **Limited payload**: 440 bytes for 7 hops requires fragmentation for large messages

### Neutral

* Network overhead: ~58% overhead for max path (440/1024), ~32% for 3-hop
* Backward compatibility: Version field allows future protocol changes
* Extensibility: Flags and reserved fields enable future features

---

## Related Decisions

* **ADR-001**: Crypto selection (ChaCha20-Poly1305) - implements encryption layer
* **SECURITY-REVIEW-CRYPTO.md**: Security findings - addresses Critical Issues #2, #5, High Priority #7, #8
* **Future ADR-003**: Ephemeral key exchange (will integrate with session_id field)
* **Future ADR-004**: Key rotation mechanism (will use session state tracking)

---

## Implementation Roadmap

### Week 4 (Current)
- [x] Packet format specification (this document)
- [ ] Implement `packet.py`: serialization, parsing, encryption/decryption
- [ ] Implement `routing.py`: path selection, forwarding logic
- [ ] Unit tests for packet format

### Week 5
- [ ] Integrate ephemeral key exchange (session_id generation)
- [ ] Implement session state tracking (sequences, nonces)
- [ ] Add bloom filter for seen-nonce registry
- [ ] Property-based testing with Hypothesis

### Week 6
- [ ] Integration testing with full protocol stack
- [ ] Performance benchmarking (encryption/decryption throughput)
- [ ] Security audit re-review
- [ ] Timing jitter validation

---

## 😐 Harold's Final Notes

*"This packet format is like a Russian nesting doll, except each doll is encrypted, timestamped, and paranoid about replay attacks. Welcome to onion routing."*

*"We've addressed the Critical security issues at the protocol level. Forward secrecy requires key exchange infrastructure (Week 5), but the packet format is ready to support it via session_id."*

*"The 440-byte payload for 7 hops might seem small, but most control messages fit easily. For larger payloads, you'll fragment. That's a feature, not a bug—smaller packets mean less correlation."*

🌑 **Dark Harold's Security Note**: *"Each layer strips 84 bytes. That's not overhead—that's the price of paranoia. Every byte is authenticated, timestamped, and bound to prevent tampering. If you think security is expensive, try getting pwned by a nation-state."*

**Status**: Ready for implementation → `packet.py` and `routing.py`
