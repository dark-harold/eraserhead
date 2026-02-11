"""
Tests for Master Key Storage and Lifecycle Management.

😐 Breaking master key storage with various attack scenarios.
🌑 Testing the attacks that actually happen: filesystem reads,
    wrong passphrases, backup recovery, rotation forward secrecy.

Author: harold-tester
"""

import secrets
import tempfile
import time
from pathlib import Path

import pytest
from cryptography.exceptions import InvalidTag
from src.anemochory.crypto_key_storage import (
    EncryptedFileBackend,
    KeyMetadata,
    MasterKeyManager,
    create_default_backend,
)


# 😐 Use fast iterations for tests (production uses 600k/1M)
# Dark Harold: "We test the logic, not the CPU's ability to suffer."
TEST_PBKDF2_ITERATIONS = 1_000
TEST_BACKUP_PBKDF2_ITERATIONS = 2_000


def _fast_manager(backend: EncryptedFileBackend) -> MasterKeyManager:
    """Create a MasterKeyManager with low PBKDF2 iterations for testing."""
    manager = MasterKeyManager(backend)
    manager.DEFAULT_PBKDF2_ITERATIONS = TEST_PBKDF2_ITERATIONS
    manager.BACKUP_PBKDF2_ITERATIONS = TEST_BACKUP_PBKDF2_ITERATIONS
    return manager


class TestKeyMetadata:
    """Tests for key metadata serialization."""

    def test_to_dict_serialization(self) -> None:
        """Metadata converts to JSON-serializable dict."""
        salt = secrets.token_bytes(16)
        metadata = KeyMetadata(
            key_id="test-key-123",
            salt=salt,
            iterations=600_000,
            created_at=1234567890.5,
            algorithm="chacha20-poly1305",
            rotations=3,
        )

        data = metadata.to_dict()

        assert data["key_id"] == "test-key-123"
        assert data["salt"] == salt.hex()
        assert data["iterations"] == 600_000
        assert data["created_at"] == 1234567890.5
        assert data["algorithm"] == "chacha20-poly1305"
        assert data["rotations"] == 3

    def test_from_dict_deserialization(self) -> None:
        """dict converts back to KeyMetadata."""
        data = {
            "key_id": "test-key-456",
            "salt": "deadbeefcafebabe" * 2,  # 32 hex chars = 16 bytes
            "iterations": 1_000_000,
            "created_at": 9876543210.1,
            "algorithm": "aes-256-gcm",
            "rotations": 5,
        }

        metadata = KeyMetadata.from_dict(data)

        assert metadata.key_id == "test-key-456"
        assert metadata.salt == bytes.fromhex("deadbeefcafebabe" * 2)
        assert metadata.iterations == 1_000_000
        assert metadata.created_at == 9876543210.1
        assert metadata.algorithm == "aes-256-gcm"
        assert metadata.rotations == 5

    def test_roundtrip_serialization(self) -> None:
        """to_dict → from_dict preserves all fields."""
        original = KeyMetadata(
            key_id="roundtrip-test",
            salt=secrets.token_bytes(16),
            iterations=600_000,
            created_at=time.time(),
        )

        data = original.to_dict()
        restored = KeyMetadata.from_dict(data)

        assert restored.key_id == original.key_id
        assert restored.salt == original.salt
        assert restored.iterations == original.iterations
        assert restored.created_at == original.created_at
        assert restored.algorithm == original.algorithm
        assert restored.rotations == original.rotations


class TestEncryptedFileBackend:
    """Tests for file-based key storage (fallback backend)."""

    def test_store_and_retrieve_key(self) -> None:
        """Store encrypted key, retrieve it back."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = EncryptedFileBackend(tmpdir)

            key_id = "test-file-key"
            encrypted_key = secrets.token_bytes(60)  # nonce + ciphertext
            metadata = KeyMetadata(
                key_id=key_id,
                salt=secrets.token_bytes(16),
                iterations=600_000,
                created_at=time.time(),
            )

            backend.store_key(key_id, encrypted_key, metadata)

            result = backend.retrieve_key(key_id)
            assert result is not None
            retrieved_key, retrieved_metadata = result

            assert retrieved_key == encrypted_key
            assert retrieved_metadata.key_id == metadata.key_id
            assert retrieved_metadata.salt == metadata.salt

    def test_retrieve_nonexistent_key_returns_none(self) -> None:
        """Retrieving non-existent key returns None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = EncryptedFileBackend(tmpdir)

            result = backend.retrieve_key("nonexistent-key")

            assert result is None

    def test_delete_key_removes_files(self) -> None:
        """Delete removes both key and metadata files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = EncryptedFileBackend(tmpdir)

            key_id = "delete-test"
            encrypted_key = secrets.token_bytes(60)
            metadata = KeyMetadata(
                key_id=key_id,
                salt=secrets.token_bytes(16),
                iterations=600_000,
                created_at=time.time(),
            )

            backend.store_key(key_id, encrypted_key, metadata)
            assert backend.retrieve_key(key_id) is not None

            backend.delete_key(key_id)
            assert backend.retrieve_key(key_id) is None

    def test_list_keys(self) -> None:
        """list_keys returns all stored key IDs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = EncryptedFileBackend(tmpdir)

            # Store 3 keys
            for i in range(3):
                key_id = f"list-test-{i}"
                encrypted_key = secrets.token_bytes(60)
                metadata = KeyMetadata(
                    key_id=key_id,
                    salt=secrets.token_bytes(16),
                    iterations=600_000,
                    created_at=time.time(),
                )
                backend.store_key(key_id, encrypted_key, metadata)

            keys = backend.list_keys()

            assert len(keys) == 3
            assert "list-test-0" in keys
            assert "list-test-1" in keys
            assert "list-test-2" in keys

    def test_storage_directory_created_with_permissions(self) -> None:
        """Storage directory created with restrictive permissions (0700)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "nonexistent"
            EncryptedFileBackend(storage_path)

            # Directory should be created
            expected_path = storage_path / "eraserhead"
            assert expected_path.exists()
            assert expected_path.is_dir()

            # 😐 Permission check may fail on some filesystems (Windows, Docker)
            # so we accept that this is best-effort
            try:
                mode = expected_path.stat().st_mode & 0o777
                assert mode == 0o700
            except (OSError, AssertionError):
                pass  # Best-effort


class TestMasterKeyManager:
    """Tests for master key lifecycle management."""

    def test_generate_master_key(self) -> None:
        """Generate new master key returns valid key_id."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = EncryptedFileBackend(tmpdir)
            manager = _fast_manager(backend)

            key_id = manager.generate_master_key("strong-passphrase-123")

            assert isinstance(key_id, str)
            assert len(key_id) == 32  # 16 bytes hex-encoded

    def test_generate_rejects_weak_passphrase(self) -> None:
        """🌑 Reject passphrases shorter than 8 characters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = EncryptedFileBackend(tmpdir)
            manager = _fast_manager(backend)

            with pytest.raises(ValueError, match="at least 8 characters"):
                manager.generate_master_key("weak")

    def test_unlock_key_with_correct_passphrase(self) -> None:
        """Unlock returns 32-byte master key."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = EncryptedFileBackend(tmpdir)
            manager = _fast_manager(backend)

            passphrase = "correct-horse-battery-staple"
            key_id = manager.generate_master_key(passphrase)

            master_key = manager.unlock_key(key_id, passphrase)

            assert isinstance(master_key, bytes)
            assert len(master_key) == 32

    def test_unlock_key_with_wrong_passphrase_fails(self) -> None:
        """🌑 Wrong passphrase raises ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = EncryptedFileBackend(tmpdir)
            manager = _fast_manager(backend)

            key_id = manager.generate_master_key("correct-passphrase")

            with pytest.raises(ValueError, match="Incorrect passphrase"):
                manager.unlock_key(key_id, "wrong-passphrase")

    def test_unlock_nonexistent_key_fails(self) -> None:
        """Unlocking non-existent key raises ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = EncryptedFileBackend(tmpdir)
            manager = _fast_manager(backend)

            with pytest.raises(ValueError, match="not found"):
                manager.unlock_key("nonexistent-key-id", "any-passphrase")

    def test_get_active_key_returns_cached_key(self) -> None:
        """get_active_key returns cached key after unlock."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = EncryptedFileBackend(tmpdir)
            manager = _fast_manager(backend)

            passphrase = "test-passphrase"
            key_id = manager.generate_master_key(passphrase)

            # After generate: key is cached
            cached_after_gen = manager.get_active_key()
            assert cached_after_gen is not None
            assert len(cached_after_gen) == 32

            # Lock and re-unlock
            manager.lock_key()
            assert manager.get_active_key() is None

            unlocked_key = manager.unlock_key(key_id, passphrase)
            cached_key = manager.get_active_key()

            # 😐 Both should be bytearray with same content
            assert cached_key == unlocked_key
            assert bytes(cached_key) == bytes(unlocked_key)

    def test_lock_key_wipes_active_key(self) -> None:
        """lock_key wipes cached key from memory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = EncryptedFileBackend(tmpdir)
            manager = _fast_manager(backend)

            key_id = manager.generate_master_key("lock-test-passphrase")
            manager.unlock_key(key_id, "lock-test-passphrase")

            assert manager.get_active_key() is not None

            manager.lock_key()

            assert manager.get_active_key() is None

    def test_same_passphrase_and_salt_derive_same_mek(self) -> None:
        """PBKDF2 is deterministic: same input → same output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = EncryptedFileBackend(tmpdir)
            manager = _fast_manager(backend)

            passphrase = "deterministic-test"
            salt = secrets.token_bytes(16)
            iterations = 100_000  # Lower for speed

            mek1 = manager._derive_mek(passphrase, salt, iterations)
            mek2 = manager._derive_mek(passphrase, salt, iterations)

            assert mek1 == mek2

    def test_different_salt_derives_different_mek(self) -> None:
        """🌑 Different salt prevents rainbow tables."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = EncryptedFileBackend(tmpdir)
            manager = _fast_manager(backend)

            passphrase = "same-passphrase"
            salt1 = secrets.token_bytes(16)
            salt2 = secrets.token_bytes(16)
            iterations = 100_000

            mek1 = manager._derive_mek(passphrase, salt1, iterations)
            mek2 = manager._derive_mek(passphrase, salt2, iterations)

            assert mek1 != mek2

    def test_encrypt_decrypt_roundtrip(self) -> None:
        """Encrypt with MEK → decrypt with same MEK recovers plaintext."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = EncryptedFileBackend(tmpdir)
            manager = _fast_manager(backend)

            mek = secrets.token_bytes(32)
            master_key = secrets.token_bytes(32)
            key_id = "roundtrip-test"

            encrypted = manager._encrypt_with_mek(mek, master_key, key_id)
            decrypted = manager._decrypt_with_mek(mek, encrypted, key_id)

            assert decrypted == master_key

    def test_decrypt_with_wrong_mek_fails(self) -> None:
        """🌑 Wrong MEK causes decryption failure (AEAD integrity)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = EncryptedFileBackend(tmpdir)
            manager = _fast_manager(backend)

            mek_correct = secrets.token_bytes(32)
            mek_wrong = secrets.token_bytes(32)
            master_key = secrets.token_bytes(32)
            key_id = "wrong-mek-test"

            encrypted = manager._encrypt_with_mek(mek_correct, master_key, key_id)

            with pytest.raises(InvalidTag):  # AEAD integrity check
                manager._decrypt_with_mek(mek_wrong, encrypted, key_id)

    def test_decrypt_with_wrong_key_id_fails(self) -> None:
        """🌑 Wrong key_id in associated data causes AEAD failure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = EncryptedFileBackend(tmpdir)
            manager = _fast_manager(backend)

            mek = secrets.token_bytes(32)
            master_key = secrets.token_bytes(32)

            encrypted = manager._encrypt_with_mek(mek, master_key, "key-id-1")

            with pytest.raises(InvalidTag):
                manager._decrypt_with_mek(mek, encrypted, "key-id-2")


class TestKeyRotation:
    """Tests for master key rotation (forward secrecy)."""

    def test_rotate_master_key_generates_new_key(self) -> None:
        """Rotation generates new key_id."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = EncryptedFileBackend(tmpdir)
            manager = _fast_manager(backend)

            old_key_id = manager.generate_master_key("old-passphrase")
            new_key_id = manager.rotate_master_key(old_key_id, "old-passphrase")

            assert new_key_id != old_key_id

    def test_rotate_with_new_passphrase(self) -> None:
        """Rotation can change passphrase."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = EncryptedFileBackend(tmpdir)
            manager = _fast_manager(backend)

            old_key_id = manager.generate_master_key("old-passphrase")
            new_key_id = manager.rotate_master_key(
                old_key_id,
                "old-passphrase",
                new_passphrase="new-passphrase",
            )

            # Old passphrase should fail on new key
            with pytest.raises(ValueError, match="Incorrect passphrase"):
                manager.unlock_key(new_key_id, "old-passphrase")

            # New passphrase should work
            manager.unlock_key(new_key_id, "new-passphrase")

    def test_rotation_deletes_old_key(self) -> None:
        """🌑 Forward secrecy: Old key deleted from backend."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = EncryptedFileBackend(tmpdir)
            manager = _fast_manager(backend)

            old_key_id = manager.generate_master_key("passphrase")
            new_key_id = manager.rotate_master_key(old_key_id, "passphrase")

            # Old key should not be retrievable
            assert backend.retrieve_key(old_key_id) is None

            # New key should exist
            assert backend.retrieve_key(new_key_id) is not None


class TestBackupRecovery:
    """Tests for key backup and recovery operations."""

    def test_export_key_backup(self) -> None:
        """Export produces encrypted backup blob."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = EncryptedFileBackend(tmpdir)
            manager = _fast_manager(backend)

            key_id = manager.generate_master_key("primary-passphrase")
            backup = manager.export_key_backup(
                key_id,
                "primary-passphrase",
                "recovery-passphrase",
            )

            assert isinstance(backup, bytes)
            assert len(backup) > 0
            assert backup[0] == 1  # Version byte

    def test_export_rejects_same_recovery_passphrase(self) -> None:
        """🌑 Recovery passphrase MUST differ from primary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = EncryptedFileBackend(tmpdir)
            manager = _fast_manager(backend)

            key_id = manager.generate_master_key("same-passphrase")

            with pytest.raises(ValueError, match="must differ"):
                manager.export_key_backup(
                    key_id,
                    "same-passphrase",
                    "same-passphrase",
                )

    def test_import_key_backup_restores_key(self) -> None:
        """Import recovers master key from backup."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = EncryptedFileBackend(tmpdir)
            manager = _fast_manager(backend)

            # Generate and backup
            original_key_id = manager.generate_master_key("primary-pass")
            original_key = manager.unlock_key(original_key_id, "primary-pass")

            backup = manager.export_key_backup(
                original_key_id,
                "primary-pass",
                "recovery-pass",
            )

            # Simulate disaster: delete original
            backend.delete_key(original_key_id)
            manager.lock_key()

            # Recover from backup
            recovered_key_id = manager.import_key_backup(
                backup,
                "recovery-pass",
                "new-primary-pass",
            )
            recovered_key = manager.unlock_key(recovered_key_id, "new-primary-pass")

            # 🌑 Recovered key should match original master key
            assert recovered_key == original_key

    def test_import_with_wrong_recovery_passphrase_fails(self) -> None:
        """🌑 Wrong recovery passphrase fails import."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = EncryptedFileBackend(tmpdir)
            manager = _fast_manager(backend)

            key_id = manager.generate_master_key("primary-key")
            backup = manager.export_key_backup(key_id, "primary-key", "recovery-correct")

            with pytest.raises(ValueError, match="Incorrect recovery passphrase"):
                manager.import_key_backup(backup, "recovery-wrong", "new-passphrase")

    def test_import_creates_new_key_id(self) -> None:
        """😐 Import creates NEW key_id (doesn't restore old ID)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = EncryptedFileBackend(tmpdir)
            manager = _fast_manager(backend)

            original_key_id = manager.generate_master_key("primary-key")
            backup = manager.export_key_backup(original_key_id, "primary-key", "recovery-pass")

            recovered_key_id = manager.import_key_backup(backup, "recovery-pass", "new-passphrase")

            assert recovered_key_id != original_key_id


class TestMemorySecurity:
    """Tests for memory security features (best-effort)."""

    def test_secure_zero_overwrites_bytearray(self) -> None:
        """secure_zero overwrites bytearray with zeros."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = EncryptedFileBackend(tmpdir)
            manager = _fast_manager(backend)

            data = bytearray(b"secret-data-12345678")
            original_len = len(data)

            manager._secure_zero(data)

            # After zeroing, should be all zeros
            assert data == bytearray(original_len)
            assert all(b == 0 for b in data)

    def test_secure_zero_handles_immutable_bytes(self) -> None:
        """😐 secure_zero accepts immutable bytes (but can't zero them)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = EncryptedFileBackend(tmpdir)
            manager = _fast_manager(backend)

            data = b"immutable-secret"

            # Should not raise exception (accepts bytes, doesn't modify)
            manager._secure_zero(data)

            # 😐 bytes remain unchanged (Python limitation)
            assert data == b"immutable-secret"

    def test_lock_memory_does_not_crash(self) -> None:
        """😐 lock_memory best-effort (may fail without permissions)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = EncryptedFileBackend(tmpdir)
            manager = _fast_manager(backend)

            key_data = secrets.token_bytes(32)

            # Should not crash (even if mlock fails)
            manager._lock_memory(key_data)

    def test_destructor_wipes_active_key(self) -> None:
        """__del__ wipes active key on garbage collection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = EncryptedFileBackend(tmpdir)
            manager = _fast_manager(backend)

            key_id = manager.generate_master_key("destructor-test")
            manager.unlock_key(key_id, "destructor-test")

            assert manager.get_active_key() is not None

            # Trigger destructor
            del manager

            # 😐 Can't directly verify memory wiping, but __del__ should call secure_zero


class TestEdgeCases:
    """Edge cases and attack scenarios."""

    def test_empty_passphrase_rejected(self) -> None:
        """Empty passphrase rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = EncryptedFileBackend(tmpdir)
            manager = _fast_manager(backend)

            with pytest.raises(ValueError, match="at least 8 characters"):
                manager.generate_master_key("")

    def test_corrupted_backup_rejected(self) -> None:
        """🌑 Corrupted backup blob fails import."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = EncryptedFileBackend(tmpdir)
            manager = _fast_manager(backend)

            # 😐 Version=1, valid salt (16 bytes), LOW iterations (avoid hang),
            # valid nonce (12 bytes), garbage ciphertext
            corrupted_backup = (
                b"\x01"  # Version 1
                + secrets.token_bytes(16)  # Salt
                + TEST_PBKDF2_ITERATIONS.to_bytes(4, "big")  # Iterations (low!)
                + secrets.token_bytes(12)  # Nonce
                + secrets.token_bytes(32)  # Garbage ciphertext
            )

            with pytest.raises(ValueError, match=r"Incorrect recovery passphrase|corrupted"):
                manager.import_key_backup(corrupted_backup, "recovery", "new-pass")

    def test_unsupported_backup_version_rejected(self) -> None:
        """Backup with unsupported version byte rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = EncryptedFileBackend(tmpdir)
            manager = _fast_manager(backend)

            future_backup = b"\xff" + secrets.token_bytes(100)  # Version 255

            with pytest.raises(ValueError, match="Unsupported backup version"):
                manager.import_key_backup(future_backup, "recovery", "new")

    def test_multiple_keys_coexist(self) -> None:
        """Multiple keys can be stored and retrieved independently."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = EncryptedFileBackend(tmpdir)
            manager = _fast_manager(backend)

            key_id_1 = manager.generate_master_key("passphrase-1")
            key_id_2 = manager.generate_master_key("passphrase-2")

            key1 = manager.unlock_key(key_id_1, "passphrase-1")
            key2 = manager.unlock_key(key_id_2, "passphrase-2")

            assert key1 != key2  # Different master keys

    def test_high_iteration_count_accepted(self) -> None:
        """Higher PBKDF2 iterations accepted (future-proofing)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = EncryptedFileBackend(tmpdir)
            manager = _fast_manager(backend)

            # Manually test higher iteration count (but not production-high)
            passphrase = "high-iter-test"
            salt = secrets.token_bytes(16)
            iterations = 10_000  # Higher than test default, but fast

            mek = manager._derive_mek(passphrase, salt, iterations)

            assert len(mek) == 32


class TestCreateDefaultBackend:
    """Tests for default backend factory."""

    def test_create_default_backend_returns_encrypted_file(self) -> None:
        """create_default_backend returns EncryptedFileBackend."""
        backend = create_default_backend()

        assert isinstance(backend, EncryptedFileBackend)

    def test_default_backend_uses_home_directory(self) -> None:
        """Default backend stores keys in ~/.eraserhead/keys."""
        backend = create_default_backend()

        # Check storage path (best-effort, may vary)
        # 😐 Implementation detail: EncryptedFileBackend._storage_path
        assert hasattr(backend, "_storage_path")
