"""
😐 Tests for Forward Secrecy Module

Validates X25519 ECDH key exchange and HKDF key derivation.
"""

import secrets

import pytest

# Integration test with existing crypto
from anemochory.crypto import ChaCha20Engine
from anemochory.crypto_forward_secrecy import (
    KEY_SIZE,
    SESSION_ID_SIZE,
    SHARED_SECRET_SIZE,
    ForwardSecrecyError,
    ForwardSecrecyManager,
    SessionKeyPair,
)


class TestSessionKeyPair:
    """Test SessionKeyPair dataclass validation"""

    def test_valid_session_keypair(self):
        """😐 Valid keypair creation succeeds"""
        manager = ForwardSecrecyManager()
        keypair = manager.generate_session_keypair()

        assert isinstance(keypair, SessionKeyPair)
        assert len(keypair.public_key) == SHARED_SECRET_SIZE
        assert len(keypair.session_id) == SESSION_ID_SIZE

    def test_session_id_size_validation(self):
        """🌑 Wrong session ID size rejected"""
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import x25519

        private_key = x25519.X25519PrivateKey.generate()
        public_key = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        )

        with pytest.raises(ValueError, match="Session ID must be"):
            SessionKeyPair(
                private_key=private_key,
                public_key=public_key,
                session_id=b"too_short",
            )


class TestForwardSecrecyManager:
    """Test ForwardSecrecyManager key exchange and derivation"""

    def test_generate_session_keypair_uniqueness(self):
        """😐 Each keypair generation produces unique keys"""
        manager = ForwardSecrecyManager()

        keypairs = [manager.generate_session_keypair() for _ in range(100)]

        # All session IDs unique
        session_ids = [kp.session_id for kp in keypairs]
        assert len(set(session_ids)) == 100, "Session IDs must be unique"

        # All public keys unique
        public_keys = [kp.public_key for kp in keypairs]
        assert len(set(public_keys)) == 100, "Public keys must be unique"

    def test_ecdh_alice_bob_scenario(self):
        """😐 Alice and Bob derive same shared secret"""
        manager = ForwardSecrecyManager()

        # Alice generates her keypair
        alice_keypair = manager.generate_session_keypair()

        # Bob generates his keypair
        bob_keypair = manager.generate_session_keypair()

        # Alice computes shared secret with Bob's public key
        alice_shared = manager.derive_shared_secret(
            alice_keypair.private_key, bob_keypair.public_key
        )

        # Bob computes shared secret with Alice's public key
        bob_shared = manager.derive_shared_secret(
            bob_keypair.private_key, alice_keypair.public_key
        )

        # Both should derive the SAME shared secret
        assert alice_shared == bob_shared
        assert len(alice_shared) == SHARED_SECRET_SIZE

    def test_shared_secret_different_keys_different_secrets(self):
        """🌑 Different key pairs produce different shared secrets"""
        manager = ForwardSecrecyManager()

        alice = manager.generate_session_keypair()
        bob1 = manager.generate_session_keypair()
        bob2 = manager.generate_session_keypair()

        secret1 = manager.derive_shared_secret(alice.private_key, bob1.public_key)
        secret2 = manager.derive_shared_secret(alice.private_key, bob2.public_key)

        assert secret1 != secret2, "Different peers must produce different secrets"

    def test_session_binding_different_session_ids(self):
        """🌑 Same shared secret + different session IDs = different master keys"""
        manager = ForwardSecrecyManager()

        # Same shared secret (simulated)
        shared_secret = secrets.token_bytes(SHARED_SECRET_SIZE)

        # Different session IDs
        session_id1 = secrets.token_bytes(SESSION_ID_SIZE)
        session_id2 = secrets.token_bytes(SESSION_ID_SIZE)

        # Derive master keys
        key1 = manager.derive_session_master_key(shared_secret, session_id1)
        key2 = manager.derive_session_master_key(shared_secret, session_id2)

        assert key1 != key2, "Different session IDs must produce different keys"
        assert len(key1) == KEY_SIZE
        assert len(key2) == KEY_SIZE

    def test_timestamp_binding(self):
        """😐 Different timestamps produce different keys"""
        manager = ForwardSecrecyManager()

        shared_secret = secrets.token_bytes(SHARED_SECRET_SIZE)
        session_id = secrets.token_bytes(SESSION_ID_SIZE)

        # Derive keys with different timestamps
        key1 = manager.derive_session_master_key(
            shared_secret, session_id, timestamp=1000000
        )
        key2 = manager.derive_session_master_key(
            shared_secret, session_id, timestamp=2000000
        )

        assert key1 != key2, "Different timestamps must produce different keys"

    def test_key_serialization_roundtrip(self):
        """😐 Serialize → deserialize → verify usable"""
        manager = ForwardSecrecyManager()

        keypair = manager.generate_session_keypair()


        # Deserialize back
        public_key_obj = manager.deserialize_public_key(keypair.public_key)

        # Re-serialize and verify match
        reserialized = manager.serialize_public_key(public_key_obj)
        assert reserialized == keypair.public_key

    def test_invalid_public_key_size(self):
        """🌑 Wrong public key size rejected"""
        manager = ForwardSecrecyManager()

        keypair = manager.generate_session_keypair()

        with pytest.raises(ForwardSecrecyError, match="ECDH key exchange failed"):
            manager.derive_shared_secret(
                keypair.private_key, b"wrong_size"  # Too short
            )

    def test_invalid_shared_secret_size(self):
        """🌑 Wrong shared secret size rejected"""
        manager = ForwardSecrecyManager()

        with pytest.raises(ForwardSecrecyError, match="Key derivation failed"):
            manager.derive_session_master_key(
                b"too_short",  # Wrong size
                secrets.token_bytes(SESSION_ID_SIZE),
            )

    def test_invalid_session_id_size(self):
        """🌑 Wrong session ID size rejected"""
        manager = ForwardSecrecyManager()

        with pytest.raises(ForwardSecrecyError, match="Key derivation failed"):
            manager.derive_session_master_key(
                secrets.token_bytes(SHARED_SECRET_SIZE),
                b"too_short",  # Wrong size
            )


class TestIntegrationWithChaCha20:
    """Test integration with existing ChaCha20Engine from crypto.py"""

    def test_derived_key_works_with_chacha20(self):
        """😐 Master key from ECDH works with ChaCha20Engine"""
        manager = ForwardSecrecyManager()

        # Simulate Alice-Bob key exchange
        alice = manager.generate_session_keypair()
        bob = manager.generate_session_keypair()

        alice_shared = manager.derive_shared_secret(alice.private_key, bob.public_key)
        alice_master = manager.derive_session_master_key(
            alice_shared, alice.session_id
        )

        # Use derived key with ChaCha20Engine
        engine = ChaCha20Engine(alice_master)
        plaintext = b"test message"

        nonce, ciphertext = engine.encrypt(plaintext)
        decrypted = engine.decrypt(nonce, ciphertext)

        assert decrypted == plaintext

    def test_both_parties_can_communicate(self):
        """😐 Alice encrypts, Bob decrypts with same derived key"""
        manager = ForwardSecrecyManager()

        # Key exchange
        alice = manager.generate_session_keypair()
        bob = manager.generate_session_keypair()

        alice_shared = manager.derive_shared_secret(alice.private_key, bob.public_key)
        bob_shared = manager.derive_shared_secret(bob.private_key, alice.public_key)

        # Use Alice's session_id for consistency (both must agree)
        alice_master = manager.derive_session_master_key(
            alice_shared, alice.session_id
        )
        bob_master = manager.derive_session_master_key(bob_shared, alice.session_id)

        # Verify derived keys match
        assert alice_master == bob_master

        # Alice encrypts
        alice_engine = ChaCha20Engine(alice_master)
        message = b"secret communication"
        nonce, ciphertext = alice_engine.encrypt(message)

        # Bob decrypts
        bob_engine = ChaCha20Engine(bob_master)
        decrypted = bob_engine.decrypt(nonce, ciphertext)

        assert decrypted == message


class TestSecurityProperties:
    """Test security properties and edge cases"""

    def test_repeated_derivations_are_deterministic(self):
        """😐 Same inputs always produce same output"""
        manager = ForwardSecrecyManager()

        shared = secrets.token_bytes(SHARED_SECRET_SIZE)
        session_id = secrets.token_bytes(SESSION_ID_SIZE)

        # Derive key multiple times
        key1 = manager.derive_session_master_key(shared, session_id, timestamp=123456)
        key2 = manager.derive_session_master_key(shared, session_id, timestamp=123456)
        key3 = manager.derive_session_master_key(shared, session_id, timestamp=123456)

        assert key1 == key2 == key3, "Key derivation must be deterministic"

    def test_small_changes_produce_different_keys(self):
        """🌑 Small input changes produce completely different keys"""
        manager = ForwardSecrecyManager()

        shared = secrets.token_bytes(SHARED_SECRET_SIZE)
        session_id = bytearray(secrets.token_bytes(SESSION_ID_SIZE))

        key1 = manager.derive_session_master_key(shared, bytes(session_id))

        # Change one byte of session_id
        session_id[0] ^= 0x01
        key2 = manager.derive_session_master_key(shared, bytes(session_id))

        assert key1 != key2, "Small changes must avalanche to different keys"

        # Measure difference (should be ~50% of bits flipped)
        diff_bits = sum(bin(a ^ b).count("1") for a, b in zip(key1, key2, strict=False))
        total_bits = KEY_SIZE * 8

        # Expect roughly 50% of bits different (avalanche effect)
        assert 0.4 * total_bits < diff_bits < 0.6 * total_bits, \
            f"Expected ~50% bit difference, got {diff_bits}/{total_bits}"
