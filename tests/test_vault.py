"""
😐 Tests for credential vault.
Smiling while encrypting secrets. What could go wrong.
"""

from __future__ import annotations

import pytest
from pathlib import Path

from eraserhead.models import Platform, PlatformCredentials
from eraserhead.vault import (
    CredentialVault,
    VaultLockedError,
    VaultCorruptedError,
    CredentialNotFoundError,
    SALT_SIZE,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def vault_dir(tmp_path: Path) -> Path:
    """Temporary directory for vault files."""
    return tmp_path / "vault"


@pytest.fixture
def vault(vault_dir: Path) -> CredentialVault:
    """Unlocked vault ready for use."""
    v = CredentialVault(vault_dir)
    v.unlock("test-passphrase-harold-smiles")
    return v


@pytest.fixture
def sample_creds() -> PlatformCredentials:
    """Sample platform credentials."""
    return PlatformCredentials(
        platform=Platform.TWITTER,
        username="dark_harold",
        auth_token="bearer-token-12345",
        api_key="api-key-abc",
        api_secret="api-secret-xyz",
        extra={"custom_field": "value"},
    )


# ============================================================================
# Lifecycle Tests
# ============================================================================


class TestVaultLifecycle:
    """😐 Basic vault open/close functionality."""

    def test_new_vault_does_not_exist(self, vault_dir: Path) -> None:
        vault = CredentialVault(vault_dir)
        assert not vault.exists
        assert not vault.is_unlocked

    def test_unlock_creates_vault_file(self, vault_dir: Path) -> None:
        vault = CredentialVault(vault_dir)
        vault.unlock("passphrase")
        assert vault.exists
        assert vault.is_unlocked

    def test_lock_clears_key(self, vault: CredentialVault) -> None:
        assert vault.is_unlocked
        vault.lock()
        assert not vault.is_unlocked

    def test_reopen_existing_vault(
        self, vault_dir: Path, sample_creds: PlatformCredentials
    ) -> None:
        """Store creds, lock, reopen with same passphrase."""
        # Store
        v1 = CredentialVault(vault_dir)
        v1.unlock("my-passphrase")
        v1.store(sample_creds)
        v1.lock()

        # Reopen
        v2 = CredentialVault(vault_dir)
        v2.unlock("my-passphrase")
        retrieved = v2.get(Platform.TWITTER, "dark_harold")
        assert retrieved.auth_token == "bearer-token-12345"

    def test_wrong_passphrase_fails(
        self, vault_dir: Path, sample_creds: PlatformCredentials
    ) -> None:
        """🌑 Wrong passphrase must fail, not silently decrypt garbage."""
        v1 = CredentialVault(vault_dir)
        v1.unlock("correct-passphrase")
        v1.store(sample_creds)
        v1.lock()

        v2 = CredentialVault(vault_dir)
        v2.unlock("wrong-passphrase")
        with pytest.raises(VaultCorruptedError):
            v2.list_platforms()


# ============================================================================
# CRUD Tests
# ============================================================================


class TestVaultCRUD:
    """😐 Store, retrieve, remove, list credentials."""

    def test_store_and_get(
        self, vault: CredentialVault, sample_creds: PlatformCredentials
    ) -> None:
        vault.store(sample_creds)
        retrieved = vault.get(Platform.TWITTER, "dark_harold")
        assert retrieved.platform == Platform.TWITTER
        assert retrieved.username == "dark_harold"
        assert retrieved.auth_token == "bearer-token-12345"
        assert retrieved.api_key == "api-key-abc"
        assert retrieved.api_secret == "api-secret-xyz"
        assert retrieved.extra == {"custom_field": "value"}

    def test_get_nonexistent_raises(self, vault: CredentialVault) -> None:
        with pytest.raises(CredentialNotFoundError):
            vault.get(Platform.FACEBOOK, "nobody")

    def test_update_existing(
        self, vault: CredentialVault, sample_creds: PlatformCredentials
    ) -> None:
        """Storing same platform/username overwrites."""
        vault.store(sample_creds)

        updated = PlatformCredentials(
            platform=Platform.TWITTER,
            username="dark_harold",
            auth_token="new-token",
        )
        vault.store(updated)

        retrieved = vault.get(Platform.TWITTER, "dark_harold")
        assert retrieved.auth_token == "new-token"

    def test_remove_existing(
        self, vault: CredentialVault, sample_creds: PlatformCredentials
    ) -> None:
        vault.store(sample_creds)
        assert vault.remove(Platform.TWITTER, "dark_harold") is True

        with pytest.raises(CredentialNotFoundError):
            vault.get(Platform.TWITTER, "dark_harold")

    def test_remove_nonexistent(self, vault: CredentialVault) -> None:
        assert vault.remove(Platform.FACEBOOK, "ghost") is False

    def test_list_platforms_empty(self, vault: CredentialVault) -> None:
        assert vault.list_platforms() == []

    def test_list_platforms_multiple(self, vault: CredentialVault) -> None:
        vault.store(PlatformCredentials(
            platform=Platform.TWITTER, username="user1", auth_token="t1"
        ))
        vault.store(PlatformCredentials(
            platform=Platform.FACEBOOK, username="user2", auth_token="t2"
        ))
        vault.store(PlatformCredentials(
            platform=Platform.INSTAGRAM, username="user3", auth_token="t3"
        ))

        platforms = vault.list_platforms()
        assert len(platforms) == 3
        assert (Platform.TWITTER, "user1") in platforms
        assert (Platform.FACEBOOK, "user2") in platforms


# ============================================================================
# Locked Vault Tests
# ============================================================================


class TestVaultLocked:
    """🌑 All operations must fail when vault is locked."""

    def test_store_locked(self, vault_dir: Path) -> None:
        vault = CredentialVault(vault_dir)
        with pytest.raises(VaultLockedError):
            vault.store(PlatformCredentials(
                platform=Platform.TWITTER, username="x", auth_token="y"
            ))

    def test_get_locked(self, vault_dir: Path) -> None:
        vault = CredentialVault(vault_dir)
        with pytest.raises(VaultLockedError):
            vault.get(Platform.TWITTER, "x")

    def test_remove_locked(self, vault_dir: Path) -> None:
        vault = CredentialVault(vault_dir)
        with pytest.raises(VaultLockedError):
            vault.remove(Platform.TWITTER, "x")

    def test_list_locked(self, vault_dir: Path) -> None:
        vault = CredentialVault(vault_dir)
        with pytest.raises(VaultLockedError):
            vault.list_platforms()


# ============================================================================
# Corruption Tests
# ============================================================================


class TestVaultCorruption:
    """🌑 Vault must detect tampering and corruption."""

    def test_truncated_vault_file(self, vault_dir: Path) -> None:
        """File too short to contain salt."""
        vault_dir.mkdir(parents=True)
        (vault_dir / "credentials.vault").write_bytes(b"\x00" * 5)

        vault = CredentialVault(vault_dir)
        with pytest.raises(VaultCorruptedError):
            vault.unlock("passphrase")

    def test_corrupted_ciphertext(
        self, vault_dir: Path, sample_creds: PlatformCredentials
    ) -> None:
        """Tampered ciphertext must be detected."""
        vault = CredentialVault(vault_dir)
        vault.unlock("passphrase")
        vault.store(sample_creds)
        vault.lock()

        # Tamper with encrypted data
        vault_file = vault_dir / "credentials.vault"
        raw = vault_file.read_bytes()
        # Flip a byte in the ciphertext (after salt)
        tampered = raw[:SALT_SIZE] + bytes([raw[SALT_SIZE] ^ 0xFF]) + raw[SALT_SIZE + 1:]
        vault_file.write_bytes(tampered)

        vault2 = CredentialVault(vault_dir)
        vault2.unlock("passphrase")
        with pytest.raises(VaultCorruptedError):
            vault2.list_platforms()

    def test_empty_ciphertext_returns_empty(self, vault_dir: Path) -> None:
        """Salt-only file (no credentials) returns empty store."""
        vault_dir.mkdir(parents=True)
        salt = b"\x42" * SALT_SIZE
        (vault_dir / "credentials.vault").write_bytes(salt)

        vault = CredentialVault(vault_dir)
        vault.unlock("passphrase")
        assert vault.list_platforms() == []


# ============================================================================
# Edge Cases
# ============================================================================


class TestVaultEdgeCases:
    """😐 Edge cases Harold didn't want to think about."""

    def test_username_with_colon(self, vault: CredentialVault) -> None:
        """Usernames with colons must work (key uses split(1))."""
        creds = PlatformCredentials(
            platform=Platform.GOOGLE,
            username="user:with:colons",
            auth_token="token",
        )
        vault.store(creds)
        retrieved = vault.get(Platform.GOOGLE, "user:with:colons")
        assert retrieved.username == "user:with:colons"

    def test_empty_extra_fields(self, vault: CredentialVault) -> None:
        """Credentials with minimal fields."""
        creds = PlatformCredentials(
            platform=Platform.LINKEDIN,
            username="minimal",
            auth_token="tok",
        )
        vault.store(creds)
        retrieved = vault.get(Platform.LINKEDIN, "minimal")
        # 😐 from_dict returns empty string, not None. Harold accepts.
        assert not retrieved.api_key
        assert not retrieved.api_secret

    def test_multiple_accounts_same_platform(
        self, vault: CredentialVault
    ) -> None:
        """Multiple accounts on the same platform."""
        vault.store(PlatformCredentials(
            platform=Platform.TWITTER, username="harold1", auth_token="t1"
        ))
        vault.store(PlatformCredentials(
            platform=Platform.TWITTER, username="harold2", auth_token="t2"
        ))

        c1 = vault.get(Platform.TWITTER, "harold1")
        c2 = vault.get(Platform.TWITTER, "harold2")
        assert c1.auth_token == "t1"
        assert c2.auth_token == "t2"

    def test_vault_dir_created_automatically(self, tmp_path: Path) -> None:
        """Vault creates its directory if needed."""
        deep_path = tmp_path / "a" / "b" / "c"
        vault = CredentialVault(deep_path)
        vault.unlock("pass")
        assert deep_path.exists()
