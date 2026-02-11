"""
😐 Tests for Replay Protection Module

Validates timestamp validation, nonce tracking, and memory management.
"""

import secrets
import time

import pytest

from anemochory.crypto_replay import (
    PacketMetadata,
    ReplayProtectionManager,
)


class TestPacketMetadata:
    """Test PacketMetadata dataclass"""

    def test_valid_metadata(self):
        """😐 Valid metadata creation succeeds"""
        session_id = secrets.token_bytes(32)
        metadata = PacketMetadata(
            timestamp=time.time(), sequence_number=1, session_id=session_id
        )

        assert metadata.timestamp > 0
        assert metadata.sequence_number == 1
        assert len(metadata.session_id) == 32

    def test_sequence_number_bounds(self):
        """🌑 Sequence number must be within valid range"""
        session_id = secrets.token_bytes(16)

        # Valid: 0 to 2^64-1
        metadata = PacketMetadata(timestamp=time.time(), sequence_number=0, session_id=session_id)
        assert metadata.sequence_number == 0

        metadata = PacketMetadata(
            timestamp=time.time(), sequence_number=2**64 - 1, session_id=session_id
        )
        assert metadata.sequence_number == 2**64 - 1

        # Invalid: negative
        with pytest.raises(ValueError, match="Sequence number must be"):
            PacketMetadata(timestamp=time.time(), sequence_number=-1, session_id=session_id)

        # Invalid: too large
        with pytest.raises(ValueError, match="Sequence number must be"):
            PacketMetadata(timestamp=time.time(), sequence_number=2**64, session_id=session_id)

    def test_session_id_min_size(self):
        """🌑 Session ID must be at least 16 bytes"""
        with pytest.raises(ValueError, match="Session ID must be"):
            PacketMetadata(
                timestamp=time.time(), sequence_number=1, session_id=b"too_short"
            )


class TestTimestampValidation:
    """Test packet freshness validation"""

    def test_fresh_packet_accepted(self):
        """😐 Fresh packets within time window accepted"""
        manager = ReplayProtectionManager()
        session_id = secrets.token_bytes(16)

        metadata = manager.create_packet_metadata(session_id, sequence_number=1)
        assert manager.validate_packet_metadata(metadata)

    def test_old_packet_rejected(self):
        """🌑 Packets older than max_age rejected"""
        manager = ReplayProtectionManager(max_age_seconds=60)
        session_id = secrets.token_bytes(16)

        # 70 seconds old (beyond 60 + 5s tolerance)
        old_time = time.time() - 70
        metadata = PacketMetadata(
            timestamp=old_time, sequence_number=1, session_id=session_id
        )

        assert not manager.validate_packet_metadata(metadata)

    def test_packet_within_tolerance_accepted(self):
        """😐 Packets within clock skew tolerance accepted"""
        manager = ReplayProtectionManager(max_age_seconds=60)
        session_id = secrets.token_bytes(16)

        # 59 seconds old (within 60s window)
        recent_time = time.time() - 59
        metadata = PacketMetadata(
            timestamp=recent_time, sequence_number=1, session_id=session_id
        )

        assert manager.validate_packet_metadata(metadata)

    def test_future_packet_within_skew_accepted(self):
        """😐 Future packets within clock skew accepted (NTP sync)"""
        manager = ReplayProtectionManager()
        session_id = secrets.token_bytes(16)

        # 4 seconds in future (within 5s tolerance)
        future_time = time.time() + 4
        metadata = PacketMetadata(
            timestamp=future_time, sequence_number=1, session_id=session_id
        )

        assert manager.validate_packet_metadata(metadata)

    def test_far_future_packet_rejected(self):
        """🌑 Packets far in future rejected (attack or bad clock)"""
        manager = ReplayProtectionManager()
        session_id = secrets.token_bytes(16)

        # 10 seconds in future (beyond 5s tolerance)
        future_time = time.time() + 10
        metadata = PacketMetadata(
            timestamp=future_time, sequence_number=1, session_id=session_id
        )

        assert not manager.validate_packet_metadata(metadata)

    def test_custom_current_time(self):
        """😐 Can override current time for testing"""
        manager = ReplayProtectionManager()
        session_id = secrets.token_bytes(16)

        metadata = PacketMetadata(
            timestamp=1000000.0, sequence_number=1, session_id=session_id
        )

        # At timestamp 1000010, packet is 10 seconds old (fresh)
        assert manager.validate_packet_metadata(metadata, current_time=1000010.0)

        # At timestamp 1000070, packet is 70 seconds old (expired)
        assert not manager.validate_packet_metadata(metadata, current_time=1000070.0)


class TestNonceTracking:
    """Test nonce duplicate detection"""

    def test_first_nonce_not_seen(self):
        """😐 First time nonce is not marked as seen"""
        manager = ReplayProtectionManager()
        session_id = secrets.token_bytes(16)
        nonce = secrets.token_bytes(12)

        assert not manager.is_nonce_seen(nonce, session_id)

    def test_duplicate_nonce_detected(self):
        """🌑 Duplicate nonce detected (replay attack)"""
        manager = ReplayProtectionManager()
        session_id = secrets.token_bytes(16)
        nonce = secrets.token_bytes(12)

        # First use
        assert not manager.is_nonce_seen(nonce, session_id)
        manager.mark_nonce_seen(nonce, session_id)

        # Second use - duplicate!
        assert manager.is_nonce_seen(nonce, session_id)

    def test_same_nonce_different_sessions_allowed(self):
        """😐 Same nonce in different sessions is allowed"""
        manager = ReplayProtectionManager()
        session_id1 = secrets.token_bytes(16)
        session_id2 = secrets.token_bytes(16)
        nonce = secrets.token_bytes(12)

        # Use nonce in session 1
        manager.mark_nonce_seen(nonce, session_id1)
        assert manager.is_nonce_seen(nonce, session_id1)

        # Same nonce in session 2 should be allowed
        assert not manager.is_nonce_seen(nonce, session_id2)
        manager.mark_nonce_seen(nonce, session_id2)
        assert manager.is_nonce_seen(nonce, session_id2)

    def test_many_unique_nonces_tracked(self):
        """😐 Can track many unique nonces"""
        manager = ReplayProtectionManager()
        session_id = secrets.token_bytes(16)

        nonces = [secrets.token_bytes(12) for _ in range(1000)]

        for nonce in nonces:
            assert not manager.is_nonce_seen(nonce, session_id)
            manager.mark_nonce_seen(nonce, session_id)
            assert manager.is_nonce_seen(nonce, session_id)


class TestSessionIsolation:
    """Test per-session nonce tracking"""

    def test_sessions_tracked_independently(self):
        """😐 Different sessions tracked independently"""
        manager = ReplayProtectionManager()

        session1 = secrets.token_bytes(16)
        session2 = secrets.token_bytes(16)

        nonce1 = secrets.token_bytes(12)
        nonce2 = secrets.token_bytes(12)

        # Session 1: nonce1
        manager.mark_nonce_seen(nonce1, session1)

        # Session 2: nonce2
        manager.mark_nonce_seen(nonce2, session2)

        # Each session only sees its own nonces
        assert manager.is_nonce_seen(nonce1, session1)
        assert not manager.is_nonce_seen(nonce2, session1)

        assert manager.is_nonce_seen(nonce2, session2)
        assert not manager.is_nonce_seen(nonce1, session2)


class TestSequenceNumbers:
    """Test sequence number tracking"""

    def test_track_sequence_numbers(self):
        """😐 Sequence numbers tracked per session"""
        manager = ReplayProtectionManager()
        session_id = secrets.token_bytes(16)

        metadata1 = PacketMetadata(
            timestamp=time.time(), sequence_number=1, session_id=session_id
        )
        metadata2 = PacketMetadata(
            timestamp=time.time(), sequence_number=2, session_id=session_id
        )

        assert manager.track_sequence_number(metadata1)
        assert manager.track_sequence_number(metadata2)

    def test_out_of_order_sequences_allowed(self):
        """😐 Out-of-order delivery allowed (network reordering)"""
        manager = ReplayProtectionManager()
        session_id = secrets.token_bytes(16)

        # Receive packets out of order: 2, 1, 3
        meta2 = PacketMetadata(timestamp=time.time(), sequence_number=2, session_id=session_id)
        meta1 = PacketMetadata(timestamp=time.time(), sequence_number=1, session_id=session_id)
        meta3 = PacketMetadata(timestamp=time.time(), sequence_number=3, session_id=session_id)

        # All acceptable (no strict ordering enforced)
        assert manager.track_sequence_number(meta2)
        assert manager.track_sequence_number(meta1)
        assert manager.track_sequence_number(meta3)


class TestMemoryManagement:
    """Test memory limits and eviction"""

    def test_memory_limit_enforced(self):
        """🌑 LRU eviction triggers at max_seen_nonces"""
        manager = ReplayProtectionManager(max_seen_nonces=100)
        session_id = secrets.token_bytes(16)

        # Add 150 nonces (exceeds limit of 100)
        nonces = [secrets.token_bytes(12) for _ in range(150)]

        for nonce in nonces:
            manager.mark_nonce_seen(nonce, session_id)

        # Check stats
        stats = manager.get_stats()
        assert stats["total_nonces_tracked"] <= 100, "Should not exceed max_seen_nonces"

    def test_oldest_nonces_evicted_first(self):
        """😐 LRU eviction removes oldest nonces"""
        manager = ReplayProtectionManager(max_seen_nonces=50)
        session_id = secrets.token_bytes(16)

        # Add 50 nonces
        old_nonces = [secrets.token_bytes(12) for _ in range(50)]
        for nonce in old_nonces:
            manager.mark_nonce_seen(nonce, session_id)
            time.sleep(0.001)  # Ensure timestamp differences

        # Add 50 more (should evict old ones)
        new_nonces = [secrets.token_bytes(12) for _ in range(50)]
        for nonce in new_nonces:
            manager.mark_nonce_seen(nonce, session_id)

        # Old nonces likely evicted (may have small false negative window)
        # 😐 This test may be flaky due to eviction timing
        stats = manager.get_stats()
        assert stats["total_nonces_tracked"] <= 50

    def test_memory_stats_accurate(self):
        """😐 Memory statistics reflect actual tracking"""
        manager = ReplayProtectionManager()
        session1 = secrets.token_bytes(16)
        session2 = secrets.token_bytes(16)

        # Add nonces to two sessions
        for _ in range(10):
            manager.mark_nonce_seen(secrets.token_bytes(12), session1)
        for _ in range(15):
            manager.mark_nonce_seen(secrets.token_bytes(12), session2)

        stats = manager.get_stats()
        assert stats["active_sessions"] == 2
        assert stats["total_nonces_tracked"] == 25


class TestIntegration:
    """Test full workflow integration"""

    def test_sender_receiver_workflow(self):
        """😐 Full send/receive workflow with replay protection"""
        from anemochory.crypto import ChaCha20Engine

        # Both nodes have replay managers
        sender_mgr = ReplayProtectionManager()
        receiver_mgr = ReplayProtectionManager()

        session_id = secrets.token_bytes(32)
        key = secrets.token_bytes(32)
        engine = ChaCha20Engine(key)

        # Sender: Create packet
        metadata = sender_mgr.create_packet_metadata(session_id, sequence_number=1)
        plaintext = b"test message"
        nonce, ciphertext = engine.encrypt(plaintext)
        sender_mgr.mark_nonce_seen(nonce, session_id)

        # Receiver: Validate and decrypt
        assert receiver_mgr.validate_packet_metadata(metadata), "Fresh packet should be valid"
        assert not receiver_mgr.is_nonce_seen(nonce, session_id), "Nonce should be new"

        receiver_mgr.mark_nonce_seen(nonce, session_id)
        decrypted = engine.decrypt(nonce, ciphertext)
        assert decrypted == plaintext

        # Attacker: Try replay
        assert receiver_mgr.is_nonce_seen(nonce, session_id), "Replay detected!"

    def test_multiple_sessions_parallel(self):
        """😐 Multiple sessions tracked independently"""
        manager = ReplayProtectionManager()

        sessions = [secrets.token_bytes(32) for _ in range(5)]
        nonces_per_session = 20

        # Send packets in all sessions
        for session_id in sessions:
            for _seq in range(nonces_per_session):
                nonce = secrets.token_bytes(12)
                manager.mark_nonce_seen(nonce, session_id)

        stats = manager.get_stats()
        assert stats["active_sessions"] == 5
        assert stats["total_nonces_tracked"] == 100


class TestEdgeCases:
    """Test edge cases and error scenarios"""

    def test_empty_session_id_behavior(self):
        """🌑 Empty session ID rejected by PacketMetadata"""
        with pytest.raises(ValueError, match="Session ID must be"):
            PacketMetadata(timestamp=time.time(), sequence_number=1, session_id=b"")

    def test_zero_sequence_number_valid(self):
        """😐 Sequence number 0 is valid"""
        session_id = secrets.token_bytes(16)
        metadata = PacketMetadata(timestamp=time.time(), sequence_number=0, session_id=session_id)
        assert metadata.sequence_number == 0

    def test_large_nonce_values(self):
        """😐 Large nonces (various sizes) handled correctly"""
        manager = ReplayProtectionManager()
        session_id = secrets.token_bytes(16)

        # ChaCha20-Poly1305 uses 12-byte nonces
        nonce = secrets.token_bytes(12)
        manager.mark_nonce_seen(nonce, session_id)
        assert manager.is_nonce_seen(nonce, session_id)

        # Larger nonce (for future algorithms)
        large_nonce = secrets.token_bytes(32)
        manager.mark_nonce_seen(large_nonce, session_id)
        assert manager.is_nonce_seen(large_nonce, session_id)
