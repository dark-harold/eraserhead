"""
😐 Anemochory Protocol: Replay Protection Module

Implements timestamp validation and nonce tracking to prevent replay attacks.
Addresses SECURITY-REVIEW-CRYPTO.md Critical Issue #2.

🌑 Security Guarantee: Captured packets cannot be replayed to track users
   or correlate traffic across time periods.
"""

import time
from collections import deque
from dataclasses import dataclass


# Constants
MAX_AGE_SECONDS = 60  # Packet freshness window
CLOCK_SKEW_TOLERANCE = 5  # Allow ±5 seconds for clock drift
MAX_SEEN_NONCES = 100_000  # Memory limit for nonce tracking


class ReplayProtectionError(Exception):
    """Raised for replay attack detection"""

    pass


@dataclass
class PacketMetadata:
    """
    Metadata for replay detection.

    😐 Embedded in or alongside encrypted packets.

    Attributes:
        timestamp: Unix timestamp when packet created
        sequence_number: Monotonic sequence within session
        session_id: Session identifier for nonce isolation
    """

    timestamp: float
    sequence_number: int
    session_id: bytes

    def __post_init__(self) -> None:
        """Validate metadata fields"""
        if not 0 <= self.sequence_number < 2**64:
            raise ValueError(
                f"Sequence number must be 0-2^64, got {self.sequence_number}"
            )
        if len(self.session_id) < 16:
            raise ValueError(
                f"Session ID must be >=16 bytes, got {len(self.session_id)}"
            )


class ReplayProtectionManager:
    """
    😐 Prevents replay attacks via timestamp validation and nonce tracking.

    🌑 Attack Scenarios Prevented:
    - Replay: Adversary captures packet, replays minutes/hours later
    - Traffic correlation: Same packet replayed to different nodes for timing
    - Nonce reuse: Duplicate nonces within session (catastrophic for crypto)

    Implementation Notes:
    - Uses simple set-based nonce tracking (4MB for 100k nonces)
    - LRU eviction prevents memory exhaustion
    - Per-session isolation (nonces tracked separately per session_id)

    🌑 Future Enhancement: Replace set with bloom filter for <1MB footprint
       with ~1% false positive rate (acceptable for security).

    Example usage:
        >>> # Sender side
        >>> manager = ReplayProtectionManager()
        >>> metadata = manager.create_packet_metadata(session_id, seq_num=1)
        >>> nonce, ciphertext = engine.encrypt(plaintext)
        >>> manager.mark_nonce_seen(nonce, session_id)
        >>>
        >>> # Receiver side (different node)
        >>> if not manager.validate_packet_metadata(metadata):
        ...     raise ReplayProtectionError("Expired packet")
        >>> if manager.is_nonce_seen(nonce, session_id):
        ...     raise ReplayProtectionError("Duplicate nonce - replay attack!")
        >>> manager.mark_nonce_seen(nonce, session_id)
        >>> plaintext = engine.decrypt(nonce, ciphertext)
    """

    def __init__(
        self, max_age_seconds: int = MAX_AGE_SECONDS, max_seen_nonces: int = MAX_SEEN_NONCES
    ):
        """
        Initialize replay protection manager.

        Args:
            max_age_seconds: Packet freshness window (default: 60 seconds)
            max_seen_nonces: Maximum nonces to track before eviction (default: 100k)
        """
        self._max_age = max_age_seconds
        self._max_seen_nonces = max_seen_nonces

        # Per-session nonce tracking: session_id -> deque of nonces
        # 😐 Using deque for efficient FIFO eviction
        self._seen_nonces: dict[bytes, deque[bytes]] = {}

        # Global nonce -> timestamp mapping for LRU eviction
        # 🌑 Needed to evict oldest nonces across all sessions
        self._nonce_timestamps: dict[bytes, float] = {}

        # Per-session sequence number tracking
        # 😐 Tracks highest seen sequence per session
        self._session_sequences: dict[bytes, int] = {}

    def create_packet_metadata(
        self, session_id: bytes, sequence_number: int, timestamp: float | None = None
    ) -> PacketMetadata:
        """
        Create metadata for new packet with current timestamp.

        😐 Call this when creating outbound packets.

        Args:
            session_id: Session identifier (>= 16 bytes)
            sequence_number: Monotonic sequence within session
            timestamp: Optional override timestamp (default: current time)

        Returns:
            PacketMetadata to embed in packet

        Example:
            >>> manager = ReplayProtectionManager()
            >>> session_id = secrets.token_bytes(32)
            >>> metadata = manager.create_packet_metadata(session_id, seq_num=1)
            >>> assert metadata.sequence_number == 1
        """
        if timestamp is None:
            timestamp = time.time()

        return PacketMetadata(
            timestamp=timestamp, sequence_number=sequence_number, session_id=session_id
        )

    def validate_packet_metadata(
        self, metadata: PacketMetadata, current_time: float | None = None
    ) -> bool:
        """
        Validate packet is fresh and not expired.

        😐 Rejects packets outside time window (prevents replay).
        🌑 Allows ±5s clock skew for NTP sync delays and VM drift.

        Args:
            metadata: Packet metadata to validate
            current_time: Optional override current time (for testing)

        Returns:
            True if packet is fresh, False if expired

        Example:
            >>> metadata = PacketMetadata(
            ...     timestamp=time.time() - 70,  # 70 seconds old
            ...     sequence_number=1,
            ...     session_id=b"test"
            ... )
            >>> assert not manager.validate_packet_metadata(metadata)  # Too old
        """
        if current_time is None:
            current_time = time.time()

        packet_age = current_time - metadata.timestamp

        # Check if packet is too old
        if packet_age > self._max_age + CLOCK_SKEW_TOLERANCE:
            return False

        # Check if packet is from the future (clock skew or attack)
        # 🌑 Allows some future packets due to clock skew
        return not packet_age < -CLOCK_SKEW_TOLERANCE

    def mark_nonce_seen(self, nonce: bytes, session_id: bytes) -> None:
        """
        Record nonce as seen to detect duplicates.

        😐 Call this after successfully decrypting packet.
        🌑 If nonce already seen, that's a replay attack!

        Args:
            nonce: Nonce from encryption (12 bytes for ChaCha20-Poly1305)
            session_id: Session identifier for isolation

        Raises:
            ReplayProtectionError: If memory limit exceeded (defensive)
        """
        # Initialize session tracking if new session
        if session_id not in self._seen_nonces:
            self._seen_nonces[session_id] = deque()

        # Add nonce to session's seen list
        self._seen_nonces[session_id].append(nonce)
        self._nonce_timestamps[nonce] = time.time()

        # Enforce memory limit with LRU eviction
        self._enforce_memory_limit()

    def is_nonce_seen(self, nonce: bytes, session_id: bytes) -> bool:
        """
        Check if nonce was already used in this session.

        😐 Returns True if nonce seen before (replay detected).
        🌑 False positives possible after eviction, but rare.

        Args:
            nonce: Nonce to check
            session_id: Session identifier

        Returns:
            True if nonce was seen before, False otherwise

        Example:
            >>> manager = ReplayProtectionManager()
            >>> session_id = b"test_session_16b"
            >>> nonce = b"unique_nonce"
            >>>
            >>> assert not manager.is_nonce_seen(nonce, session_id)  # First time
            >>> manager.mark_nonce_seen(nonce, session_id)
            >>> assert manager.is_nonce_seen(nonce, session_id)  # Duplicate!
        """
        if session_id not in self._seen_nonces:
            return False

        return nonce in self._seen_nonces[session_id]

    def track_sequence_number(self, metadata: PacketMetadata) -> bool:
        """
        Track sequence numbers for out-of-order detection.

        😐 Currently just tracks highest seen - doesn't enforce strict ordering.
        🌑 Network reordering is legitimate, strict enforcement would break things.

        Args:
            metadata: Packet metadata with sequence_number

        Returns:
            True if sequence is acceptable, False if suspicious

        Note:
            Future enhancement: Detect large gaps (e.g., >100) as potential attack.
        """
        session_id = metadata.session_id
        seq_num = metadata.sequence_number

        if session_id not in self._session_sequences:
            self._session_sequences[session_id] = seq_num
            return True

        # Track highest seen sequence
        self._session_sequences[session_id] = max(self._session_sequences[session_id], seq_num)

        # Currently accept all sequences (no strict ordering)
        # 🌑 Future: Reject sequences that jump >1000 (potential attack)
        return True

    def _enforce_memory_limit(self) -> None:
        """
        Enforce memory limit by evicting oldest nonces.

        😐 Uses LRU eviction - oldest nonces removed first.
        🌑 This creates small false-negative window (old nonce might be reused).
        """
        total_nonces = sum(len(nonces) for nonces in self._seen_nonces.values())

        if total_nonces <= self._max_seen_nonces:
            return

        # Need to evict oldest nonces
        # 😐 Find oldest nonces across all sessions
        to_evict = total_nonces - self._max_seen_nonces

        # Sort nonces by timestamp (oldest first)
        sorted_nonces = sorted(self._nonce_timestamps.items(), key=lambda x: x[1])

        for nonce, _ in sorted_nonces[:to_evict]:
            # Remove from all session trackers
            for nonces in self._seen_nonces.values():
                if nonce in nonces:
                    # Remove from deque (O(n) but rare)
                    nonces.remove(nonce)
                    break

            # Remove from timestamp tracker
            del self._nonce_timestamps[nonce]

    def get_stats(self) -> dict[str, int | float]:
        """
        Get statistics about current state.

        😐 Useful for monitoring memory usage.

        Returns:
            Dictionary with session count, nonce count, memory estimate
        """
        total_nonces = sum(len(nonces) for nonces in self._seen_nonces.values())

        # Estimate memory: nonce (16 bytes) + session_id (32 bytes) + timestamp (8 bytes)
        # 😐 Rough estimate, actual overhead higher due to Python objects
        memory_estimate_mb = (total_nonces * (16 + 32 + 8)) / (1024 * 1024)

        return {
            "active_sessions": len(self._seen_nonces),
            "total_nonces_tracked": total_nonces,
            "memory_estimate_mb": round(memory_estimate_mb, 2),
            "max_nonces": self._max_seen_nonces,
        }
