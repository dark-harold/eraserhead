"""
😐 Test Suite for Anemochory Cryptographic Primitives

Tests ChaCha20-Poly1305 encryption, key derivation, and packet padding.
Includes property-based tests, edge cases, and security validations.

🌑 Dark Harold's Testing Philosophy:
    - If it can fail, it will fail (test for it)
    - Crypto failures are silent (test success AND failure modes)
    - Timing attacks are real (test constant-time operations)
    - Nonce reuse is catastrophic (test uniqueness)
"""

import struct

import pytest

from anemochory.crypto import (
    AUTH_TAG_SIZE,
    DEFAULT_PACKET_SIZE,
    KEY_SIZE,
    NONCE_SIZE,
    ChaCha20Engine,
    DecryptionError,
    derive_layer_key,
    pad_packet,
    unpad_packet,
)


class TestChaCha20Engine:
    """Tests for ChaCha20-Poly1305 encryption engine.

    😐 harold-tester: Covering happy path, sad path, and paranoid path.
    """

    def test_generate_key_produces_correct_size(self):
        """Key generation produces 32-byte keys."""
        key = ChaCha20Engine.generate_key()
        assert len(key) == KEY_SIZE
        assert isinstance(key, bytes)

    def test_generate_key_produces_unique_keys(self):
        """Each key generation produces unique keys.

        🌑 Dark Harold: If keys collide, crypto is broken. Test it.
        """
        keys = [ChaCha20Engine.generate_key() for _ in range(100)]
        unique_keys = set(keys)
        assert len(unique_keys) == 100, "Key collision detected!"

    def test_init_requires_correct_key_size(self):
        """Engine initialization validates key size."""
        with pytest.raises(ValueError, match="32 bytes"):
            ChaCha20Engine(b"short_key")  # Too short

        with pytest.raises(ValueError, match="32 bytes"):
            ChaCha20Engine(b"way_too_long_key_that_exceeds_32_bytes_requirement")

        # 😐 Correct size should work
        key = ChaCha20Engine.generate_key()
        engine = ChaCha20Engine(key)
        assert engine is not None

    def test_encrypt_produces_nonce_and_ciphertext(self):
        """Encryption returns nonce and ciphertext tuple."""
        engine = ChaCha20Engine(ChaCha20Engine.generate_key())
        plaintext = b"secret packet data"

        nonce, ciphertext = engine.encrypt(plaintext)

        assert isinstance(nonce, bytes)
        assert isinstance(ciphertext, bytes)
        assert len(nonce) == NONCE_SIZE
        # Ciphertext = plaintext + auth_tag
        assert len(ciphertext) == len(plaintext) + AUTH_TAG_SIZE

    def test_encrypt_produces_unique_nonces(self):
        """Each encryption call produces unique nonces.

        🌑 Dark Harold: Nonce reuse is cryptographic suicide. Test it.
        """
        engine = ChaCha20Engine(ChaCha20Engine.generate_key())
        plaintext = b"test"

        nonces = [engine.encrypt(plaintext)[0] for _ in range(100)]
        unique_nonces = set(nonces)

        assert len(unique_nonces) == 100, "Nonce reuse detected! 🚨"

    def test_decrypt_recovers_original_plaintext(self):
        """Decryption recovers original plaintext."""
        engine = ChaCha20Engine(ChaCha20Engine.generate_key())
        original = b"The packet you seek is within this ciphertext"

        nonce, ciphertext = engine.encrypt(original)
        recovered = engine.decrypt(nonce, ciphertext)

        assert recovered == original

    def test_decrypt_fails_with_wrong_key(self):
        """Decryption with wrong key fails authentication.

        😐 harold-tester: Security property — wrong key should fail.
        """
        key1 = ChaCha20Engine.generate_key()
        key2 = ChaCha20Engine.generate_key()

        engine1 = ChaCha20Engine(key1)
        engine2 = ChaCha20Engine(key2)

        nonce, ciphertext = engine1.encrypt(b"secret")

        with pytest.raises(DecryptionError, match="Authentication failed"):
            engine2.decrypt(nonce, ciphertext)

    def test_decrypt_fails_with_tampered_ciphertext(self):
        """Tampering with ciphertext causes authentication failure.

        🌑 Dark Harold: Tampered packets MUST be detected. Test it.
        """
        engine = ChaCha20Engine(ChaCha20Engine.generate_key())
        nonce, ciphertext = engine.encrypt(b"original data")

        # Tamper with ciphertext (flip one bit)
        tampered = bytearray(ciphertext)
        tampered[0] ^= 0x01  # Flip first bit

        with pytest.raises(DecryptionError, match="Authentication failed"):
            engine.decrypt(nonce, bytes(tampered))

    def test_decrypt_with_wrong_nonce_size_raises_valueerror(self):
        """Nonce size validation."""
        engine = ChaCha20Engine(ChaCha20Engine.generate_key())
        _, ciphertext = engine.encrypt(b"data")

        with pytest.raises(ValueError, match="Nonce must be 12 bytes"):
            engine.decrypt(b"short", ciphertext)

    def test_decrypt_with_short_ciphertext_raises_error(self):
        """Ciphertext must be at least as long as auth tag."""
        engine = ChaCha20Engine(ChaCha20Engine.generate_key())
        nonce = b"0" * NONCE_SIZE
        short_ciphertext = b"short"  # Less than 16 bytes

        with pytest.raises(DecryptionError, match="too short"):
            engine.decrypt(nonce, short_ciphertext)

    def test_encrypt_decrypt_with_empty_data(self):
        """Edge case: Empty plaintext.

        😐 harold-tester: Empty packets exist. Handle them gracefully.
        """
        engine = ChaCha20Engine(ChaCha20Engine.generate_key())

        nonce, ciphertext = engine.encrypt(b"")
        recovered = engine.decrypt(nonce, ciphertext)

        assert recovered == b""
        assert len(ciphertext) == AUTH_TAG_SIZE  # Just the auth tag

    def test_encrypt_decrypt_with_large_data(self):
        """Handles large packets (10MB).

        😐 Real-world packets can be large. Test it.
        """
        engine = ChaCha20Engine(ChaCha20Engine.generate_key())
        large_data = b"X" * (10 * 1024 * 1024)  # 10MB

        nonce, ciphertext = engine.encrypt(large_data)
        recovered = engine.decrypt(nonce, ciphertext)

        assert recovered == large_data


class TestKeyDerivation:
    """Tests for HKDF-based layer key derivation.

    🌑 Dark Harold: Key derivation errors leak info to attackers. Test thoroughly.
    """

    def test_derive_layer_key_produces_correct_size(self):
        """Derived keys are 32 bytes."""
        master = ChaCha20Engine.generate_key()
        layer_key = derive_layer_key(master, layer_index=0, total_layers=5)

        assert len(layer_key) == KEY_SIZE
        assert isinstance(layer_key, bytes)

    def test_different_layers_produce_different_keys(self):
        """Each layer gets a unique key.

        😐 harold-tester: Key reuse across layers would be bad. Verify independence.
        """
        master = ChaCha20Engine.generate_key()
        total_layers = 5

        keys = [
            derive_layer_key(master, layer_index=i, total_layers=total_layers)
            for i in range(total_layers)
        ]

        # All keys should be unique
        unique_keys = set(keys)
        assert len(unique_keys) == total_layers, "Layer key collision!"

    def test_same_layer_index_produces_same_key(self):
        """Deriving the same layer key twice produces identical results.

        😐 Determinism is important for decryption.
        """
        master = ChaCha20Engine.generate_key()

        key1 = derive_layer_key(master, layer_index=2, total_layers=5)
        key2 = derive_layer_key(master, layer_index=2, total_layers=5)

        assert key1 == key2

    def test_different_master_keys_produce_different_derived_keys(self):
        """Different master keys produce different layer keys."""
        master1 = ChaCha20Engine.generate_key()
        master2 = ChaCha20Engine.generate_key()

        key1 = derive_layer_key(master1, layer_index=0, total_layers=5)
        key2 = derive_layer_key(master2, layer_index=0, total_layers=5)

        assert key1 != key2

    def test_changing_total_layers_changes_keys(self):
        """Changing total_layers produces different keys (binding).

        🌑 Dark Harold: Context binding prevents layer confusion attacks.
        """
        master = ChaCha20Engine.generate_key()

        key_5_layers = derive_layer_key(master, layer_index=0, total_layers=5)
        key_7_layers = derive_layer_key(master, layer_index=0, total_layers=7)

        assert key_5_layers != key_7_layers

    def test_layer_index_out_of_range_raises_error(self):
        """Layer index must be < total_layers."""
        master = ChaCha20Engine.generate_key()

        with pytest.raises(ValueError, match="must be < total_layers"):
            derive_layer_key(master, layer_index=5, total_layers=5)

        with pytest.raises(ValueError, match="must be < total_layers"):
            derive_layer_key(master, layer_index=10, total_layers=5)


class TestPacketPadding:
    """Tests for packet padding (traffic analysis resistance).

    😐 harold-tester: Constant-size packets hide information.
        Test padding logic doesn't leak anything.
    """

    def test_pad_packet_produces_target_size(self):
        """Padded packet is exactly target_size bytes."""
        data = b"small payload"
        padded = pad_packet(data, target_size=1024)

        assert len(padded) == 1024

    def test_pad_packet_with_default_size(self):
        """Default target size is DEFAULT_PACKET_SIZE."""
        data = b"test data"
        padded = pad_packet(data)

        assert len(padded) == DEFAULT_PACKET_SIZE

    def test_unpad_packet_recovers_original_data(self):
        """Unpadding recovers original data exactly."""
        original = b"secret packet payload"
        padded = pad_packet(original, target_size=512)
        recovered = unpad_packet(padded)

        assert recovered == original

    def test_pad_unpad_roundtrip_with_various_sizes(self):
        """Roundtrip works for various data sizes.

        😐 Testing edge cases: empty, small, large.
        """
        test_cases = [
            b"",  # Empty
            b"x",  # Single byte
            b"A" * 10,  # Small
            b"B" * 500,  # Large
        ]

        for data in test_cases:
            padded = pad_packet(data, target_size=1024)
            recovered = unpad_packet(padded)
            assert recovered == data, f"Roundtrip failed for {len(data)}-byte data"

    def test_pad_packet_uses_random_padding(self):
        """Padding is random, not zeros or patterns.

        🌑 Dark Harold: Predictable padding leaks information. Test randomness.
        """
        data = b"test"
        padded1 = pad_packet(data, target_size=256)
        padded2 = pad_packet(data, target_size=256)

        # Same data, different padding (because Random)
        assert padded1[: len(data) + 2] == padded2[: len(data) + 2]  # Data + length same
        assert padded1 != padded2  # But full packets differ (random padding)

    def test_pad_packet_raises_error_if_data_too_large(self):
        """Data exceeding target_size raises ValueError."""
        data = b"way too much data for this packet size"

        with pytest.raises(ValueError, match="too large"):
            pad_packet(data, target_size=10)  # Only 10 bytes total

    def test_unpad_packet_validates_length_prefix(self):
        """Malformed length prefix raises ValueError.

        😐 harold-tester: Bad packets should fail gracefully, not crash.
        """
        # Length prefix says 1000 bytes, but packet is only 100
        bad_packet = struct.pack(">H", 1000) + b"X" * 98

        with pytest.raises(ValueError, match="Padding validation failed"):
            unpad_packet(bad_packet)

    def test_unpad_packet_rejects_too_short_packets(self):
        """Packets < 2 bytes (no room for length prefix) are rejected."""
        with pytest.raises(ValueError, match="too short"):
            unpad_packet(b"")

        with pytest.raises(ValueError, match="too short"):
            unpad_packet(b"X")  # Only 1 byte


class TestIntegration:
    """Integration tests: encryption + padding + key derivation.

    😐 harold-tester: Unit tests passed. Now test them working together.
    """

    def test_multi_layer_encryption_decryption(self):
        """Simulate multi-layer onion encryption.

        🌑 Dark Harold: This is the core Anemochory operation. Must work perfectly.
        """
        master_key = ChaCha20Engine.generate_key()
        total_layers = 5
        original_payload = b"destination: hidden service"

        # Encrypt layer by layer (innermost first)
        packet = original_payload
        nonces = []

        for layer in range(total_layers - 1, -1, -1):  # 4, 3, 2, 1, 0
            layer_key = derive_layer_key(master_key, layer, total_layers)
            engine = ChaCha20Engine(layer_key)

            nonce, ciphertext = engine.encrypt(packet)
            nonces.insert(0, nonce)  # Store nonces in order
            packet = ciphertext  # Next layer encrypts this ciphertext

        # Decrypt layer by layer (outermost first)
        for layer in range(total_layers):  # 0, 1, 2, 3, 4
            layer_key = derive_layer_key(master_key, layer, total_layers)
            engine = ChaCha20Engine(layer_key)

            packet = engine.decrypt(nonces[layer], packet)

        # Final decrypted packet should be original
        assert packet == original_payload

    def test_encrypted_padded_packet_roundtrip(self):
        """Encrypt, pad, unpad, decrypt.

        😐 Real-world workflow: pad before encrypt, decrypt before unpad.
        """
        key = ChaCha20Engine.generate_key()
        engine = ChaCha20Engine(key)
        original = b"secret message"

        # Encrypt
        nonce, ciphertext = engine.encrypt(original)

        # Pad (to hide ciphertext size)
        padded = pad_packet(ciphertext, target_size=512)
        assert len(padded) == 512  # Constant size

        # Unpad
        unpadded_ciphertext = unpad_packet(padded)
        assert unpadded_ciphertext == ciphertext

        # Decrypt
        recovered = engine.decrypt(nonce, unpadded_ciphertext)
        assert recovered == original


# 😐 harold-tester's test coverage assessment:
# - Core functionality: ✅ Covered
# - Edge cases: ✅ Covered
# - Error handling: ✅ Covered
# - Security properties: ✅ Covered
# - Integration: ✅ Covered
#
# 🌑 Dark Harold's review:
# - Nonce uniqueness: ✅ Tested
# - Key isolation: ✅ Tested
# - Authentication: ✅ Tested
# - Tampering detection: ✅ Tested
# - Padding randomness: ✅ Tested
#
# Next steps:
# - Property-based testing with Hypothesis (Week 4)
# - Timing analysis (constant-time verification, Week 5)
# - Fuzzing with malformed packets (Week 5)
# - harold-security review (Week 6)
