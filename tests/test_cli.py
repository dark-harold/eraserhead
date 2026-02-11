"""
😐 Tests for EraserHead CLI.
Testing the user-facing facade of Harold's deletion apparatus.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from eraserhead.cli import app
from eraserhead.models import Platform, PlatformCredentials
from eraserhead.vault import CredentialVault


runner = CliRunner()


# ============================================================================
# Version
# ============================================================================


class TestVersion:
    def test_version_command(self) -> None:
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "EraserHead" in result.output
        assert "0.1.0" in result.output


# ============================================================================
# Status
# ============================================================================


class TestStatus:
    def test_status_no_queue(self, tmp_path: Path) -> None:
        result = runner.invoke(
            app,
            [
                "status",
                "--queue",
                str(tmp_path / "missing.json"),
            ],
        )
        assert result.exit_code == 0
        assert "Nothing pending" in result.output

    def test_status_with_queue(self, tmp_path: Path) -> None:
        from eraserhead.models import ResourceType
        from eraserhead.queue import TaskQueue

        q = TaskQueue()
        q.add_task(Platform.TWITTER, ResourceType.POST, "t1")
        q.add_task(Platform.TWITTER, ResourceType.COMMENT, "c1")
        queue_path = tmp_path / "queue.json"
        q.save(queue_path)

        result = runner.invoke(
            app,
            [
                "status",
                "--queue",
                str(queue_path),
            ],
        )
        assert result.exit_code == 0
        assert "Total:     2" in result.output


# ============================================================================
# Vault CLI
# ============================================================================


class TestVaultCLI:
    def test_vault_store_and_list(self, tmp_path: Path) -> None:
        vault_dir = tmp_path / "vault"

        # Store
        result = runner.invoke(
            app,
            [
                "vault",
                "store",
                "twitter",
                "harold",
                "--token",
                "my-token",
                "--passphrase",
                "test-pass",
                "--vault-dir",
                str(vault_dir),
            ],
        )
        assert result.exit_code == 0
        assert "stored" in result.output.lower()

        # List
        result = runner.invoke(
            app,
            [
                "vault",
                "list",
                "--passphrase",
                "test-pass",
                "--vault-dir",
                str(vault_dir),
            ],
        )
        assert result.exit_code == 0
        assert "twitter" in result.output
        assert "harold" in result.output

    def test_vault_remove(self, tmp_path: Path) -> None:
        vault_dir = tmp_path / "vault"

        # Store first
        runner.invoke(
            app,
            [
                "vault",
                "store",
                "twitter",
                "harold",
                "--token",
                "tok",
                "--passphrase",
                "test-pass",
                "--vault-dir",
                str(vault_dir),
            ],
        )

        # Remove
        result = runner.invoke(
            app,
            [
                "vault",
                "remove",
                "twitter",
                "harold",
                "--passphrase",
                "test-pass",
                "--vault-dir",
                str(vault_dir),
            ],
        )
        assert result.exit_code == 0
        assert "removed" in result.output.lower()

    def test_vault_unknown_platform(self, tmp_path: Path) -> None:
        result = runner.invoke(
            app,
            [
                "vault",
                "store",
                "myspace",
                "harold",
                "--token",
                "tok",
                "--passphrase",
                "test-pass",
                "--vault-dir",
                str(tmp_path / "vault"),
            ],
        )
        assert result.exit_code == 1
        assert "Unknown platform" in result.output


# ============================================================================
# Scrub CLI
# ============================================================================


class TestScrubCLI:
    def test_scrub_no_ids(self, tmp_path: Path) -> None:
        vault_dir = tmp_path / "vault"
        # Store creds first
        runner.invoke(
            app,
            [
                "vault",
                "store",
                "twitter",
                "harold",
                "--token",
                "tok",
                "--passphrase",
                "pass",
                "--vault-dir",
                str(vault_dir),
            ],
        )

        result = runner.invoke(
            app,
            [
                "scrub",
                "twitter",
                "--passphrase",
                "pass",
                "--vault-dir",
                str(vault_dir),
            ],
        )
        assert result.exit_code == 1
        assert "No resource IDs" in result.output

    def test_scrub_unknown_platform(self, tmp_path: Path) -> None:
        result = runner.invoke(
            app,
            [
                "scrub",
                "myspace",
                "--ids",
                "post-1",
                "--passphrase",
                "pass",
                "--vault-dir",
                str(tmp_path / "vault"),
            ],
        )
        assert result.exit_code == 1

    def test_scrub_dry_run(self, tmp_path: Path) -> None:
        vault_dir = tmp_path / "vault"
        # Store creds
        runner.invoke(
            app,
            [
                "vault",
                "store",
                "twitter",
                "harold",
                "--token",
                "tok",
                "--passphrase",
                "pass",
                "--vault-dir",
                str(vault_dir),
            ],
        )

        result = runner.invoke(
            app,
            [
                "scrub",
                "twitter",
                "--ids",
                "tweet-1,tweet-2",
                "--dry-run",
                "--passphrase",
                "pass",
                "--vault-dir",
                str(vault_dir),
            ],
        )
        assert result.exit_code == 0
        assert "DRY RUN" in result.output
        assert "Complete" in result.output


# ============================================================================
# Help
# ============================================================================


class TestHelp:
    def test_main_help(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "EraserHead" in result.output

    def test_vault_help(self) -> None:
        result = runner.invoke(app, ["vault", "--help"])
        assert result.exit_code == 0

    def test_scrub_help(self) -> None:
        result = runner.invoke(app, ["scrub", "--help"])
        assert result.exit_code == 0


# ============================================================================
# CLI Error Paths
# ============================================================================


class TestCLIErrorPaths:
    """😐 Testing the many ways Harold's CLI can say 'no'."""

    def test_vault_store_wrong_passphrase_on_list(self, tmp_path: Path) -> None:
        vault_dir = tmp_path / "vault"
        # Store with one passphrase
        runner.invoke(
            app,
            [
                "vault",
                "store",
                "twitter",
                "harold",
                "--token",
                "tok",
                "--passphrase",
                "correct-pass",
                "--vault-dir",
                str(vault_dir),
            ],
        )
        # List with different passphrase — VaultCorruptedError propagates
        result = runner.invoke(
            app,
            [
                "vault",
                "list",
                "--passphrase",
                "wrong-pass",
                "--vault-dir",
                str(vault_dir),
            ],
        )
        # The exception may or may not be caught depending on vault behavior
        # Wrong passphrase produces VaultCorruptedError from _load_credentials
        assert result.exit_code != 0

    def test_vault_remove_unknown_platform(self, tmp_path: Path) -> None:
        result = runner.invoke(
            app,
            [
                "vault",
                "remove",
                "myspace",
                "harold",
                "--passphrase",
                "pass",
                "--vault-dir",
                str(tmp_path / "vault"),
            ],
        )
        assert result.exit_code == 1
        assert "Unknown platform" in result.output

    def test_vault_remove_nonexistent_creds(self, tmp_path: Path) -> None:
        vault_dir = tmp_path / "vault"
        # Create vault first
        runner.invoke(
            app,
            [
                "vault",
                "store",
                "twitter",
                "harold",
                "--token",
                "tok",
                "--passphrase",
                "pass",
                "--vault-dir",
                str(vault_dir),
            ],
        )
        # Remove non-existent user
        result = runner.invoke(
            app,
            [
                "vault",
                "remove",
                "twitter",
                "nobody",
                "--passphrase",
                "pass",
                "--vault-dir",
                str(vault_dir),
            ],
        )
        assert result.exit_code == 0
        assert "No credentials found" in result.output

    def test_vault_list_empty(self, tmp_path: Path) -> None:
        vault_dir = tmp_path / "vault"
        # Create empty vault
        vault = CredentialVault(vault_dir)
        vault.unlock("pass")
        vault.lock()

        result = runner.invoke(
            app,
            [
                "vault",
                "list",
                "--passphrase",
                "pass",
                "--vault-dir",
                str(vault_dir),
            ],
        )
        assert result.exit_code == 0
        assert "No credentials stored" in result.output

    def test_scrub_unknown_resource_type(self, tmp_path: Path) -> None:
        result = runner.invoke(
            app,
            [
                "scrub",
                "twitter",
                "--type",
                "quantum_state",
                "--ids",
                "id-1",
                "--passphrase",
                "pass",
                "--vault-dir",
                str(tmp_path / "vault"),
            ],
        )
        assert result.exit_code == 1
        assert "Unknown resource type" in result.output

    def test_scrub_unknown_priority(self, tmp_path: Path) -> None:
        result = runner.invoke(
            app,
            [
                "scrub",
                "twitter",
                "--type",
                "post",
                "--priority",
                "ludicrous",
                "--ids",
                "id-1",
                "--passphrase",
                "pass",
                "--vault-dir",
                str(tmp_path / "vault"),
            ],
        )
        assert result.exit_code == 1
        assert "Unknown priority" in result.output

    def test_scrub_no_creds_for_platform(self, tmp_path: Path) -> None:
        vault_dir = tmp_path / "vault"
        # Store creds for twitter, try to scrub facebook
        runner.invoke(
            app,
            [
                "vault",
                "store",
                "twitter",
                "harold",
                "--token",
                "tok",
                "--passphrase",
                "pass",
                "--vault-dir",
                str(vault_dir),
            ],
        )
        result = runner.invoke(
            app,
            [
                "scrub",
                "facebook",
                "--ids",
                "post-1",
                "--passphrase",
                "pass",
                "--vault-dir",
                str(vault_dir),
            ],
        )
        assert result.exit_code == 1
        assert "No credentials" in result.output

    def test_status_corrupted_queue(self, tmp_path: Path) -> None:
        queue_path = tmp_path / "queue.json"
        queue_path.write_text("{{{invalid json")
        result = runner.invoke(
            app,
            [
                "status",
                "--queue",
                str(queue_path),
            ],
        )
        assert result.exit_code == 1
        assert "Error loading queue" in result.output
