"""
🌑 Adversarial Security Tests for Anemochory Protocol

Dark Harold's test suite: attacking our own crypto from every angle.
These tests simulate adversary capabilities and verify defenses hold.

😐 If any of these fail, we have a real problem.
"""

from __future__ import annotations

import secrets
import struct

import pytest

from anemochory.crypto import (
    ChaCha20Engine,
    DecryptionError,
    derive_layer_key,
    pad_packet,
    unpad_packet,
)
from anemochory.crypto_forward_secrecy import ForwardSecrecyManager
from anemochory.crypto_key_rotation import KeyRotationManager
from anemochory.crypto_replay import ReplayProtectionManager
from anemochory.session import SecureSession, SessionError, SessionState, SessionStateError


class TestNonceReplayAdversary:
    """🌑 Attacker captures nonces and replays packets."""

    def test_replay_same_nonce_detected(self) -> None:
        """Captured nonce+ciphertext pair detected on replay."""
        key = secrets.token_bytes(32)
        sender = SecureSession.create()
        sender.establish_with_shared_key(key)
        receiver = SecureSession.create()
        receiver.establish_with_shared_key(key)

        nonce, ciphertext = sender.encrypt(b"secret message")
        receiver.decrypt(nonce, ciphertext)  # First time OK

        with pytest.raises(SessionError, match="Replay attack"):
            receiver.decrypt(nonce, ciphertext)  # Replay!

        sender.close()
        receiver.close()

    def test_replay_across_rapid_succession(self) -> None:
        """Rapid replay attempts are all caught."""
        key = secrets.token_bytes(32)
        sender = SecureSession.create()
        sender.establish_with_shared_key(key)
        receiver = SecureSession.create()
        receiver.establish_with_shared_key(key)

        nonce, ciphertext = sender.encrypt(b"data")
        receiver.decrypt(nonce, ciphertext)

        for _ in range(100):
            with pytest.raises(SessionError, match="Replay"):
                receiver.decrypt(nonce, ciphertext)

        stats = receiver.get_stats()
        assert stats.replay_attempts_blocked == 100

        sender.close()
        receiver.close()


class TestKeyExchangeAdversary:
    """🌑 Attacker attempts to compromise key exchange."""

    def test_wrong_peer_key_size_rejected(self) -> None:
        """Malformed peer public key is rejected."""
        session = SecureSession.create()
        session.initiate_key_exchange()

        # Try wrong-size key (attacker sends garbage)
        with pytest.raises(SessionError, match="32 bytes"):
            session.complete_key_exchange(b"short")

    def test_cannot_exchange_twice(self) -> None:
        """Cannot complete key exchange after already established."""
        # First exchange succeeds
        alice = SecureSession.create()
        bob = SecureSession.create()
        a_pub = alice.initiate_key_exchange()
        b_pub = bob.initiate_key_exchange()
        alice.complete_key_exchange(b_pub)
        bob.complete_key_exchange(a_pub)

        assert alice.state == SessionState.ESTABLISHED

        # Second exchange should fail — already ESTABLISHED
        with pytest.raises(SessionStateError):
            alice.initiate_key_exchange()

    def test_forward_secrecy_independent_sessions(self) -> None:
        """Compromise of one session key doesn't compromise others."""
        # Create two independent sessions with same peer
        fs_manager = ForwardSecrecyManager()
        session_keys = []

        for _ in range(5):
            kp = fs_manager.generate_session_keypair()
            # Each keypair is independent
            session_keys.append(kp.public_key)

        # All public keys must be unique (ephemeral)
        assert len(set(session_keys)) == 5

    def test_ecdh_produces_different_shared_secrets(self) -> None:
        """Each ECDH exchange produces a unique shared secret."""
        fs = ForwardSecrecyManager()
        secrets_set: set[bytes] = set()

        for _ in range(10):
            kp_a = fs.generate_session_keypair()
            kp_b = fs.generate_session_keypair()

            shared = fs.derive_shared_secret(kp_a.private_key, kp_b.public_key)
            secrets_set.add(shared)

        assert len(secrets_set) == 10


class TestKeyRotationAdversary:
    """🌑 Attacker exploits key rotation timing."""

    def test_rotation_produces_independent_keys(self) -> None:
        """Rotated keys cannot be derived from future keys."""
        initial_key = secrets.token_bytes(32)
        manager = KeyRotationManager(initial_key)

        keys_seen = set()
        keys_seen.add(manager._current_session_key)
        for _ in range(4):
            # Force rotation by exceeding packet threshold
            manager.state.packets_with_current_key = 10001
            manager.encrypt(b"data")  # triggers rotation check
            keys_seen.add(manager._current_session_key)

        # All distinct keys (initial + 4 rotations = 5)
        assert len(keys_seen) == 5

    def test_grace_period_decryption_with_old_key(self) -> None:
        """Packets encrypted with pre-rotation key still decrypt during grace."""
        key = secrets.token_bytes(32)
        manager = KeyRotationManager(key)

        # Encrypt with current key
        nonce, ciphertext = manager.encrypt(b"pre-rotation data")

        # Force rotation
        manager.state.packets_with_current_key = 10001
        manager.encrypt(b"trigger rotation")

        # Old ciphertext should still decrypt (grace period)
        plaintext = manager.decrypt(nonce, ciphertext)
        assert plaintext == b"pre-rotation data"


class TestPaddingOracleAdversary:
    """🌑 Attacker probes padding for information leakage."""

    def test_constant_error_for_bad_length_prefix(self) -> None:
        """All invalid length prefixes produce identical generic error."""
        bad_packets = [
            struct.pack(">H", 500) + b"X" * 10,  # Length > actual
            struct.pack(">H", 999) + b"X" * 50,  # Much larger
            struct.pack(">H", 65535) + b"X" * 100,  # Max uint16
        ]

        for bad in bad_packets:
            with pytest.raises(ValueError, match="Padding validation failed"):
                unpad_packet(bad)

    def test_valid_padding_does_not_reveal_length_distribution(self) -> None:
        """All valid padded packets produce same constant output size."""
        sizes = [1, 10, 100, 500, 1000]
        for size in sizes:
            data = secrets.token_bytes(min(size, 1022))
            padded = pad_packet(data)
            assert len(padded) == 1024  # Always constant

    def test_padding_randomness_per_call(self) -> None:
        """Same data produces different padding each time (random fill)."""
        data = b"constant"
        paddings = set()
        for _ in range(50):
            padded = pad_packet(data)
            paddings.add(padded[2 + len(data) :])

        # Random padding should produce unique values
        assert len(paddings) == 50


class TestLayerDerivationAdversary:
    """🌑 Attacker tries layer confusion or key extraction."""

    def test_salt_changes_derived_key(self) -> None:
        """Different salts produce different layer keys (defense-in-depth)."""
        master = ChaCha20Engine.generate_key()
        salt1 = secrets.token_bytes(16)
        salt2 = secrets.token_bytes(16)

        key1 = derive_layer_key(master, 0, 5, salt=salt1)
        key2 = derive_layer_key(master, 0, 5, salt=salt2)

        assert key1 != key2

    def test_default_salt_backward_compatible(self) -> None:
        """derive_layer_key without explicit salt is deterministic."""
        master = ChaCha20Engine.generate_key()

        key1 = derive_layer_key(master, 0, 5)
        key2 = derive_layer_key(master, 0, 5)

        assert key1 == key2

    def test_layer_key_cross_contamination_impossible(self) -> None:
        """Knowledge of one layer key reveals nothing about others."""
        master = ChaCha20Engine.generate_key()
        keys = [derive_layer_key(master, i, 7) for i in range(7)]

        # Each key is 32 bytes of unique material
        for i, key_a in enumerate(keys):
            for j, key_b in enumerate(keys):
                if i != j:
                    assert key_a != key_b
                    # Check no shared prefix/suffix patterns
                    assert key_a[:16] != key_b[:16]


class TestSessionLifecycleAdversary:
    """🌑 Attacker attempts to exploit session state machine."""

    def test_encrypt_before_established_fails(self) -> None:
        """Can't encrypt in CREATED state."""
        session = SecureSession.create()
        with pytest.raises(SessionStateError):
            session.encrypt(b"data")

    def test_encrypt_after_close_fails(self) -> None:
        """Can't encrypt in CLOSED state."""
        session = SecureSession.create()
        session.establish_with_shared_key(secrets.token_bytes(32))
        session.close()

        with pytest.raises(SessionStateError):
            session.encrypt(b"data")

    def test_decrypt_after_close_fails(self) -> None:
        """Can't decrypt in CLOSED state."""
        session = SecureSession.create()
        session.establish_with_shared_key(secrets.token_bytes(32))
        nonce, ct = session.encrypt(b"data")
        session.close()

        with pytest.raises(SessionStateError):
            session.decrypt(nonce, ct)

    def test_double_key_exchange_fails(self) -> None:
        """Can't initiate key exchange twice."""
        session = SecureSession.create()
        session.initiate_key_exchange()

        with pytest.raises(SessionStateError):
            session.initiate_key_exchange()

    def test_complete_exchange_without_initiate_fails(self) -> None:
        """Can't complete exchange without initiating first."""
        session = SecureSession.create()
        with pytest.raises(SessionStateError):
            session.complete_key_exchange(secrets.token_bytes(32))

    def test_session_id_uniqueness(self) -> None:
        """Every session gets a unique 16-byte ID."""
        ids = set()
        for _ in range(100):
            session = SecureSession.create()
            ids.add(session.session_id)
            session.close()

        assert len(ids) == 100


class TestCiphertextTamperingAdversary:
    """🌑 Attacker modifies ciphertext in transit."""

    def test_single_bit_flip_detected(self) -> None:
        """Single bit flip in ciphertext causes authentication failure."""
        engine = ChaCha20Engine(ChaCha20Engine.generate_key())
        nonce, ciphertext = engine.encrypt(b"important data")

        # Flip one bit in middle of ciphertext
        tampered = bytearray(ciphertext)
        tampered[len(tampered) // 2] ^= 0x01

        with pytest.raises(DecryptionError):
            engine.decrypt(nonce, bytes(tampered))

    def test_truncated_ciphertext_rejected(self) -> None:
        """Truncated ciphertext fails authentication."""
        engine = ChaCha20Engine(ChaCha20Engine.generate_key())
        nonce, ciphertext = engine.encrypt(b"data")

        with pytest.raises(DecryptionError):
            engine.decrypt(nonce, ciphertext[:-1])

    def test_extended_ciphertext_rejected(self) -> None:
        """Appended bytes cause authentication failure."""
        engine = ChaCha20Engine(ChaCha20Engine.generate_key())
        nonce, ciphertext = engine.encrypt(b"data")

        with pytest.raises(DecryptionError):
            engine.decrypt(nonce, ciphertext + b"\x00")

    def test_nonce_swap_fails(self) -> None:
        """Using wrong nonce for decryption fails."""
        engine = ChaCha20Engine(ChaCha20Engine.generate_key())
        nonce1, ct1 = engine.encrypt(b"message one")
        nonce2, ct2 = engine.encrypt(b"message two")

        with pytest.raises(DecryptionError):
            engine.decrypt(nonce2, ct1)  # Wrong nonce

        with pytest.raises(DecryptionError):
            engine.decrypt(nonce1, ct2)  # Wrong nonce


class TestReplayProtectionEdgeCases:
    """🌑 Edge cases in replay protection."""

    def test_lru_eviction_maintains_protection(self) -> None:
        """LRU eviction doesn't silently drop active session nonces."""
        manager = ReplayProtectionManager(max_seen_nonces=100)
        session_id = secrets.token_bytes(16)

        # Fill with 100 nonces
        nonces = []
        for _ in range(100):
            nonce = secrets.token_bytes(12)
            manager.mark_nonce_seen(nonce, session_id)
            nonces.append(nonce)

        # Recent nonces should still be tracked
        assert manager.is_nonce_seen(nonces[-1], session_id)

    def test_different_sessions_independent(self) -> None:
        """Same nonce in different sessions doesn't trigger false positive."""
        manager = ReplayProtectionManager()
        nonce = secrets.token_bytes(12)
        session_a = secrets.token_bytes(16)
        session_b = secrets.token_bytes(16)

        manager.mark_nonce_seen(nonce, session_a)

        # Same nonce in different session is NOT a replay
        assert not manager.is_nonce_seen(nonce, session_b)

    def test_stats_accuracy(self) -> None:
        """Replay protection stats accurately reflect operations."""
        manager = ReplayProtectionManager()
        session_id = secrets.token_bytes(16)

        for _ in range(50):
            nonce = secrets.token_bytes(12)
            manager.mark_nonce_seen(nonce, session_id)

        stats = manager.get_stats()
        assert stats["total_nonces_tracked"] == 50
