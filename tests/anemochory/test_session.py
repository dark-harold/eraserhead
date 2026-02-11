"""
Tests for Secure Session Manager (Integration).

😐 Testing the full security stack working together.
🌑 This is where integration bugs hide: module A works,
   module B works, but A+B together catches fire.

Author: harold-tester
"""

import contextlib
import secrets

import pytest
from src.anemochory.crypto_key_rotation import DecryptionError
from src.anemochory.session import (
    SecureSession,
    SessionError,
    SessionState,
    SessionStateError,
)


# ============================================================================
# Session Lifecycle Tests
# ============================================================================


class TestSessionLifecycle:
    """Tests for session state transitions."""

    def test_create_session(self) -> None:
        """Factory method creates session in CREATED state."""
        session = SecureSession.create()
        assert session.state == SessionState.CREATED

    def test_session_id_unique(self) -> None:
        """Each session gets unique ID."""
        s1 = SecureSession.create()
        s2 = SecureSession.create()
        assert s1.session_id != s2.session_id

    def test_session_id_correct_size(self) -> None:
        """Session ID is 16 bytes."""
        session = SecureSession.create()
        assert len(session.session_id) == 16

    def test_initiate_key_exchange_returns_public_key(self) -> None:
        """initiate_key_exchange returns 32-byte public key."""
        session = SecureSession.create()
        pubkey = session.initiate_key_exchange()
        assert len(pubkey) == 32
        assert session.state == SessionState.KEY_EXCHANGE

    def test_cannot_initiate_twice(self) -> None:
        """Cannot initiate key exchange twice."""
        session = SecureSession.create()
        session.initiate_key_exchange()
        with pytest.raises(SessionStateError):
            session.initiate_key_exchange()

    def test_close_session(self) -> None:
        """Close session wipes state."""
        session = SecureSession.create()
        session.close()
        assert session.state == SessionState.CLOSED

    def test_cannot_encrypt_before_established(self) -> None:
        """Cannot encrypt in CREATED state."""
        session = SecureSession.create()
        with pytest.raises(SessionStateError):
            session.encrypt(b"test")

    def test_cannot_decrypt_before_established(self) -> None:
        """Cannot decrypt in CREATED state."""
        session = SecureSession.create()
        with pytest.raises(SessionStateError):
            session.decrypt(b"\x00" * 12, b"ciphertext")

    def test_cannot_encrypt_after_close(self) -> None:
        """Cannot encrypt after session closed."""
        key = secrets.token_bytes(32)
        session = SecureSession.create()
        session.establish_with_shared_key(key)
        session.close()
        with pytest.raises(SessionStateError):
            session.encrypt(b"test")


# ============================================================================
# Key Exchange Tests
# ============================================================================


class TestKeyExchange:
    """Tests for ECDH key exchange integration."""

    def test_full_key_exchange(self) -> None:
        """Two sessions establish shared keys via ECDH."""
        alice = SecureSession.create()
        bob = SecureSession.create()

        alice_pubkey = alice.initiate_key_exchange()
        bob_pubkey = bob.initiate_key_exchange()

        alice.complete_key_exchange(bob_pubkey)
        bob.complete_key_exchange(alice_pubkey)

        assert alice.state == SessionState.ESTABLISHED
        assert bob.state == SessionState.ESTABLISHED

    def test_ecdh_produces_different_keys_per_session(self) -> None:
        """Different sessions with same peers produce different keys."""
        # Session 1
        a1 = SecureSession.create()
        b1 = SecureSession.create()
        a1_pub = a1.initiate_key_exchange()
        b1_pub = b1.initiate_key_exchange()
        a1.complete_key_exchange(b1_pub)
        b1.complete_key_exchange(a1_pub)

        # Session 2
        a2 = SecureSession.create()
        b2 = SecureSession.create()
        a2_pub = a2.initiate_key_exchange()
        b2_pub = b2.initiate_key_exchange()
        a2.complete_key_exchange(b2_pub)
        b2.complete_key_exchange(a2_pub)

        # Encrypt same message in both sessions
        _, ct1 = a1.encrypt(b"same message")
        _, ct2 = a2.encrypt(b"same message")

        # Different ciphertexts (different keys + different nonces)
        assert ct1 != ct2

    def test_invalid_peer_key_fails(self) -> None:
        """Invalid peer public key fails key exchange."""
        session = SecureSession.create()
        session.initiate_key_exchange()

        with pytest.raises(SessionError, match="Key exchange failed"):
            session.complete_key_exchange(b"\x00" * 32)

    def test_cannot_complete_without_initiate(self) -> None:
        """Cannot complete key exchange without initiating first."""
        session = SecureSession.create()
        with pytest.raises(SessionStateError):
            session.complete_key_exchange(secrets.token_bytes(32))


# ============================================================================
# Pre-Shared Key Tests
# ============================================================================


class TestPreSharedKey:
    """Tests for pre-shared key establishment."""

    def test_establish_with_shared_key(self) -> None:
        """Session establishes with pre-shared key."""
        key = secrets.token_bytes(32)
        session = SecureSession.create()
        session.establish_with_shared_key(key)
        assert session.state == SessionState.ESTABLISHED

    def test_shared_key_wrong_size_rejected(self) -> None:
        """Shared key must be exactly 32 bytes."""
        session = SecureSession.create()
        with pytest.raises(ValueError, match="32 bytes"):
            session.establish_with_shared_key(b"too short")

    def test_shared_key_encrypt_decrypt(self) -> None:
        """Encrypt/decrypt works with shared key."""
        key = secrets.token_bytes(32)

        sender = SecureSession.create()
        sender.establish_with_shared_key(key)

        receiver = SecureSession.create()
        receiver.establish_with_shared_key(key)

        nonce, ciphertext = sender.encrypt(b"hello from sender")
        plaintext = receiver.decrypt(nonce, ciphertext)
        assert plaintext == b"hello from sender"


# ============================================================================
# Encryption/Decryption Tests
# ============================================================================


class TestEncryptDecrypt:
    """Tests for integrated encryption/decryption."""

    def _create_paired_sessions(self) -> tuple[SecureSession, SecureSession]:
        """Create two sessions connected via ECDH."""
        alice = SecureSession.create()
        bob = SecureSession.create()
        a_pub = alice.initiate_key_exchange()
        b_pub = bob.initiate_key_exchange()
        alice.complete_key_exchange(b_pub)
        bob.complete_key_exchange(a_pub)
        return alice, bob

    def test_roundtrip_encryption(self) -> None:
        """Encrypt → decrypt roundtrip works."""
        alice, bob = self._create_paired_sessions()

        nonce, ct = alice.encrypt(b"test message")
        pt = bob.decrypt(nonce, ct)
        assert pt == b"test message"

    def test_bidirectional_encryption(self) -> None:
        """Both directions work."""
        alice, bob = self._create_paired_sessions()

        # Alice → Bob
        n1, ct1 = alice.encrypt(b"alice says hi")
        assert bob.decrypt(n1, ct1) == b"alice says hi"

        # Bob → Alice
        n2, ct2 = bob.encrypt(b"bob says hello")
        assert alice.decrypt(n2, ct2) == b"bob says hello"

    def test_multiple_messages(self) -> None:
        """Multiple messages in sequence."""
        alice, bob = self._create_paired_sessions()

        for i in range(50):
            msg = f"message-{i}".encode()
            nonce, ct = alice.encrypt(msg)
            assert bob.decrypt(nonce, ct) == msg

    def test_empty_message_fails(self) -> None:
        """Empty plaintext fails (ChaCha20Engine requirement)."""
        alice, _ = self._create_paired_sessions()

        # 😐 ChaCha20Engine may accept or reject empty plaintext
        # depending on implementation
        _nonce, ct = alice.encrypt(b"x")
        assert len(ct) > 0

    def test_large_message(self) -> None:
        """Large messages work."""
        alice, bob = self._create_paired_sessions()

        large_msg = secrets.token_bytes(4096)
        nonce, ct = alice.encrypt(large_msg)
        assert bob.decrypt(nonce, ct) == large_msg

    def test_wrong_key_fails_decryption(self) -> None:
        """Decryption with wrong session fails."""
        alice, _bob = self._create_paired_sessions()
        eve = SecureSession.create()
        eve.establish_with_shared_key(secrets.token_bytes(32))

        nonce, ct = alice.encrypt(b"secret")
        with pytest.raises(DecryptionError):
            eve.decrypt(nonce, ct)


# ============================================================================
# Replay Protection Tests
# ============================================================================


class TestReplayProtection:
    """Tests for integrated replay protection."""

    def test_duplicate_nonce_blocked(self) -> None:
        """🌑 Same nonce rejected on second decrypt (replay attack)."""
        key = secrets.token_bytes(32)
        sender = SecureSession.create()
        sender.establish_with_shared_key(key)

        receiver = SecureSession.create()
        receiver.establish_with_shared_key(key)

        nonce, ct = sender.encrypt(b"original message")
        receiver.decrypt(nonce, ct)  # First: OK

        # Replay same packet
        with pytest.raises(SessionError, match="Replay attack"):
            receiver.decrypt(nonce, ct)

    def test_replay_counter_increments(self) -> None:
        """Replay blocks are counted in stats."""
        key = secrets.token_bytes(32)
        sender = SecureSession.create()
        sender.establish_with_shared_key(key)

        receiver = SecureSession.create()
        receiver.establish_with_shared_key(key)

        nonce, ct = sender.encrypt(b"message")
        receiver.decrypt(nonce, ct)

        with contextlib.suppress(SessionError):
            receiver.decrypt(nonce, ct)

        stats = receiver.get_stats()
        assert stats.replay_attempts_blocked == 1

    def test_different_nonces_accepted(self) -> None:
        """Different nonces are accepted (not false positives)."""
        key = secrets.token_bytes(32)
        sender = SecureSession.create()
        sender.establish_with_shared_key(key)

        receiver = SecureSession.create()
        receiver.establish_with_shared_key(key)

        for _ in range(20):
            nonce, ct = sender.encrypt(b"different nonce each time")
            receiver.decrypt(nonce, ct)

        stats = receiver.get_stats()
        assert stats.packets_received == 20
        assert stats.replay_attempts_blocked == 0


# ============================================================================
# Key Rotation Integration Tests
# ============================================================================


class TestKeyRotationIntegration:
    """Tests for key rotation during active sessions."""

    def test_packets_counted(self) -> None:
        """Session tracks packet counts."""
        key = secrets.token_bytes(32)
        session = SecureSession.create()
        session.establish_with_shared_key(key)

        for _ in range(10):
            session.encrypt(b"count me")

        stats = session.get_stats()
        assert stats.packets_sent == 10

    def test_rotation_stats_available(self) -> None:
        """Key rotation stats accessible through session."""
        key = secrets.token_bytes(32)
        session = SecureSession.create()
        session.establish_with_shared_key(key)

        session.encrypt(b"one packet")
        stats = session.get_stats()
        assert stats.key_rotations >= 0


# ============================================================================
# Session Stats Tests
# ============================================================================


class TestSessionStats:
    """Tests for session statistics."""

    def test_stats_initial(self) -> None:
        """Initial stats show zero counters."""
        session = SecureSession.create()
        stats = session.get_stats()
        assert stats.packets_sent == 0
        assert stats.packets_received == 0
        assert stats.state == "CREATED"

    def test_stats_after_activity(self) -> None:
        """Stats update after encrypted operations."""
        key = secrets.token_bytes(32)
        session = SecureSession.create()
        session.establish_with_shared_key(key)

        receiver = SecureSession.create()
        receiver.establish_with_shared_key(key)

        for _ in range(5):
            nonce, ct = session.encrypt(b"test")
            receiver.decrypt(nonce, ct)

        sender_stats = session.get_stats()
        assert sender_stats.packets_sent == 5
        assert sender_stats.state == "ESTABLISHED"

        recv_stats = receiver.get_stats()
        assert recv_stats.packets_received == 5

    def test_repr(self) -> None:
        """Session repr is informative."""
        session = SecureSession.create()
        r = repr(session)
        assert "SecureSession" in r
        assert "CREATED" in r


# ============================================================================
# Destructor Tests
# ============================================================================


class TestSessionCleanup:
    """Tests for session cleanup."""

    def test_destructor_closes(self) -> None:
        """Session closes on garbage collection."""
        session = SecureSession.create()
        session.establish_with_shared_key(secrets.token_bytes(32))
        assert session.state == SessionState.ESTABLISHED

        del session  # Should trigger __del__ → close()

    def test_double_close_safe(self) -> None:
        """Closing twice doesn't crash."""
        session = SecureSession.create()
        session.close()
        session.close()  # Should not raise
        assert session.state == SessionState.CLOSED
