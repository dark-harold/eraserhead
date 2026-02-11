"""
😐 Tests for EraserHead CLI.
Testing the user-facing facade of Harold's deletion apparatus.
"""

from __future__ import annotations

import pytest
from pathlib import Path

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
        result = runner.invoke(app, [
            "status",
            "--queue", str(tmp_path / "missing.json"),
        ])
        assert result.exit_code == 0
        assert "Nothing pending" in result.output

    def test_status_with_queue(self, tmp_path: Path) -> None:
        from eraserhead.queue import TaskQueue
        from eraserhead.models import ResourceType

        q = TaskQueue()
        q.add_task(Platform.TWITTER, ResourceType.POST, "t1")
        q.add_task(Platform.TWITTER, ResourceType.COMMENT, "c1")
        queue_path = tmp_path / "queue.json"
        q.save(queue_path)

        result = runner.invoke(app, [
            "status",
            "--queue", str(queue_path),
        ])
        assert result.exit_code == 0
        assert "Total:     2" in result.output


# ============================================================================
# Vault CLI
# ============================================================================


class TestVaultCLI:
    def test_vault_store_and_list(self, tmp_path: Path) -> None:
        vault_dir = tmp_path / "vault"

        # Store
        result = runner.invoke(app, [
            "vault", "store", "twitter", "harold",
            "--token", "my-token",
            "--passphrase", "test-pass",
            "--vault-dir", str(vault_dir),
        ])
        assert result.exit_code == 0
        assert "stored" in result.output.lower()

        # List
        result = runner.invoke(app, [
            "vault", "list",
            "--passphrase", "test-pass",
            "--vault-dir", str(vault_dir),
        ])
        assert result.exit_code == 0
        assert "twitter" in result.output
        assert "harold" in result.output

    def test_vault_remove(self, tmp_path: Path) -> None:
        vault_dir = tmp_path / "vault"

        # Store first
        runner.invoke(app, [
            "vault", "store", "twitter", "harold",
            "--token", "tok",
            "--passphrase", "test-pass",
            "--vault-dir", str(vault_dir),
        ])

        # Remove
        result = runner.invoke(app, [
            "vault", "remove", "twitter", "harold",
            "--passphrase", "test-pass",
            "--vault-dir", str(vault_dir),
        ])
        assert result.exit_code == 0
        assert "removed" in result.output.lower()

    def test_vault_unknown_platform(self, tmp_path: Path) -> None:
        result = runner.invoke(app, [
            "vault", "store", "myspace", "harold",
            "--token", "tok",
            "--passphrase", "test-pass",
            "--vault-dir", str(tmp_path / "vault"),
        ])
        assert result.exit_code == 1
        assert "Unknown platform" in result.output


# ============================================================================
# Scrub CLI
# ============================================================================


class TestScrubCLI:
    def test_scrub_no_ids(self, tmp_path: Path) -> None:
        vault_dir = tmp_path / "vault"
        # Store creds first
        runner.invoke(app, [
            "vault", "store", "twitter", "harold",
            "--token", "tok",
            "--passphrase", "pass",
            "--vault-dir", str(vault_dir),
        ])

        result = runner.invoke(app, [
            "scrub", "twitter",
            "--passphrase", "pass",
            "--vault-dir", str(vault_dir),
        ])
        assert result.exit_code == 1
        assert "No resource IDs" in result.output

    def test_scrub_unknown_platform(self, tmp_path: Path) -> None:
        result = runner.invoke(app, [
            "scrub", "myspace",
            "--ids", "post-1",
            "--passphrase", "pass",
            "--vault-dir", str(tmp_path / "vault"),
        ])
        assert result.exit_code == 1

    def test_scrub_dry_run(self, tmp_path: Path) -> None:
        vault_dir = tmp_path / "vault"
        # Store creds
        runner.invoke(app, [
            "vault", "store", "twitter", "harold",
            "--token", "tok",
            "--passphrase", "pass",
            "--vault-dir", str(vault_dir),
        ])

        result = runner.invoke(app, [
            "scrub", "twitter",
            "--ids", "tweet-1,tweet-2",
            "--dry-run",
            "--passphrase", "pass",
            "--vault-dir", str(vault_dir),
        ])
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
