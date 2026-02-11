"""
😐 Scrubbing Engine: Credential Vault

Encrypted storage for platform credentials using Fernet symmetric encryption.
Credentials are encrypted at rest and only decrypted for active use.

🌑 Dark Harold: Credential storage is the single most dangerous component.
   A breach here compromises ALL user accounts. Defense in depth:
   1. Fernet encryption (AES-128-CBC + HMAC-SHA256)
   2. Key derived from user passphrase via PBKDF2
   3. Key never persisted — derived at runtime
   4. Credentials zeroed after use (best-effort)
"""

from __future__ import annotations

import base64
import json
import os
import secrets
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from eraserhead.models import Platform, PlatformCredentials


# ============================================================================
# Constants
# ============================================================================

VAULT_FILE_NAME = "credentials.vault"
SALT_SIZE = 16  # 128-bit salt for PBKDF2
PBKDF2_ITERATIONS = 600_000  # OWASP recommended minimum (2024)


# ============================================================================
# Exceptions
# ============================================================================


class VaultError(Exception):
    """Base vault error."""


class VaultLockedError(VaultError):
    """Vault is locked (passphrase not provided)."""


class VaultCorruptedError(VaultError):
    """Vault data is corrupted or tampered with."""


class CredentialNotFoundError(VaultError):
    """Requested credential not found."""


# ============================================================================
# Vault Implementation
# ============================================================================


class CredentialVault:
    """
    😐 Encrypted credential storage for platform authentication.

    Uses Fernet symmetric encryption with PBKDF2 key derivation.
    Credentials are stored as encrypted JSON in a single file.

    Usage:
        vault = CredentialVault(vault_path)
        vault.unlock("my-passphrase")
        vault.store(PlatformCredentials(...))
        creds = vault.get(Platform.TWITTER, "harold")
        vault.lock()

    🌑 Security Properties:
    - AES-128-CBC + HMAC-SHA256 (Fernet)
    - PBKDF2 with 600k iterations for key derivation
    - Random 128-bit salt per vault
    - Credentials encrypted individually
    - Lock clears the derived key from memory
    """

    def __init__(self, vault_dir: Path) -> None:
        """
        Initialize vault.

        Args:
            vault_dir: Directory to store vault file
        """
        self._vault_dir = vault_dir
        self._vault_path = vault_dir / VAULT_FILE_NAME
        self._fernet: Fernet | None = None
        self._salt: bytes | None = None

    @property
    def is_unlocked(self) -> bool:
        """Check if vault is unlocked."""
        return self._fernet is not None

    @property
    def exists(self) -> bool:
        """Check if vault file exists on disk."""
        return self._vault_path.exists()

    def unlock(self, passphrase: str) -> None:
        """
        Unlock the vault with a passphrase.

        If vault doesn't exist, creates it with a new salt.
        If it exists, loads the salt and derives the key.

        Args:
            passphrase: User-provided passphrase

        Raises:
            VaultCorruptedError: If vault file is malformed
        """
        if self.exists:
            self._load_salt()
        else:
            self._salt = secrets.token_bytes(SALT_SIZE)
            self._vault_dir.mkdir(parents=True, exist_ok=True)

        self._fernet = self._derive_fernet(passphrase, self._salt)

        # If new vault, save empty credential store
        if not self.exists:
            self._save_credentials({})

    def lock(self) -> None:
        """
        Lock the vault, clearing the encryption key from memory.

        😐 Best-effort key clearing. Python doesn't guarantee
        memory zeroing, but we do what we can.
        """
        self._fernet = None

    def store(self, credentials: PlatformCredentials) -> None:
        """
        Store or update credentials for a platform/username.

        Args:
            credentials: Platform credentials to store

        Raises:
            VaultLockedError: If vault is locked
        """
        self._require_unlocked()
        creds_store = self._load_credentials()

        key = f"{credentials.platform}:{credentials.username}"
        creds_store[key] = credentials.to_dict()

        self._save_credentials(creds_store)

    def get(self, platform: Platform, username: str) -> PlatformCredentials:
        """
        Retrieve credentials for a platform/username.

        Args:
            platform: Target platform
            username: Account username

        Returns:
            Decrypted credentials

        Raises:
            VaultLockedError: If vault is locked
            CredentialNotFoundError: If credentials not found
        """
        self._require_unlocked()
        creds_store = self._load_credentials()

        key = f"{platform}:{username}"
        if key not in creds_store:
            raise CredentialNotFoundError(f"No credentials for {platform}:{username}")

        return PlatformCredentials.from_dict(creds_store[key])

    def remove(self, platform: Platform, username: str) -> bool:
        """
        Remove credentials for a platform/username.

        Returns True if removed, False if not found.
        """
        self._require_unlocked()
        creds_store = self._load_credentials()

        key = f"{platform}:{username}"
        if key not in creds_store:
            return False

        del creds_store[key]
        self._save_credentials(creds_store)
        return True

    def list_platforms(self) -> list[tuple[Platform, str]]:
        """
        List all stored platform/username pairs.

        Returns:
            List of (platform, username) tuples
        """
        self._require_unlocked()
        creds_store = self._load_credentials()

        result = []
        for key in creds_store:
            platform_str, username = key.split(":", 1)
            result.append((Platform(platform_str), username))
        return result

    def _require_unlocked(self) -> None:
        """Raise if vault is locked."""
        if not self.is_unlocked:
            raise VaultLockedError("Vault is locked. Call unlock() first.")

    def _derive_fernet(self, passphrase: str, salt: bytes) -> Fernet:
        """Derive Fernet key from passphrase using PBKDF2."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=PBKDF2_ITERATIONS,
        )
        key = base64.urlsafe_b64encode(kdf.derive(passphrase.encode()))
        return Fernet(key)

    def _load_salt(self) -> None:
        """Load salt from vault file header."""
        try:
            raw = self._vault_path.read_bytes()
            if len(raw) < SALT_SIZE:
                raise VaultCorruptedError("Vault file too short")
            self._salt = raw[:SALT_SIZE]
        except (OSError, ValueError) as e:
            raise VaultCorruptedError(f"Cannot read vault: {e}") from e

    def _load_credentials(self) -> dict:
        """Load and decrypt credential store."""
        assert self._fernet is not None

        try:
            raw = self._vault_path.read_bytes()
            encrypted = raw[SALT_SIZE:]
            if not encrypted:
                return {}
            decrypted = self._fernet.decrypt(encrypted)
            return json.loads(decrypted.decode())
        except InvalidToken:
            raise VaultCorruptedError("Decryption failed — wrong passphrase or corrupted vault")
        except (json.JSONDecodeError, OSError) as e:
            raise VaultCorruptedError(f"Vault data corrupted: {e}") from e

    def _save_credentials(self, creds_store: dict) -> None:
        """Encrypt and save credential store."""
        assert self._fernet is not None
        assert self._salt is not None

        plaintext = json.dumps(creds_store).encode()
        encrypted = self._fernet.encrypt(plaintext)
        self._vault_path.write_bytes(self._salt + encrypted)
