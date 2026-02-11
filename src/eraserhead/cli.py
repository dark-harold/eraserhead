"""
😐 EraserHead CLI: Command-line interface for digital footprint erasure.

Powered by Typer. Harold's dry commentary included at no extra charge.

Usage:
    eraserhead scrub --platform twitter --resource-type post
    eraserhead vault unlock
    eraserhead status
    eraserhead verify --platform twitter

🌑 "A CLI is just a GUI for people who prefer their pain in text form."
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import trio
import typer

from eraserhead.adapters.platforms import (
    get_adapter,
)
from eraserhead.engine import EngineConfig, ScrubEngine
from eraserhead.models import (
    Platform,
    PlatformCredentials,
    ResourceType,
    TaskPriority,
)
from eraserhead.vault import CredentialVault, VaultError


# ============================================================================
# App Setup
# ============================================================================

app = typer.Typer(
    name="eraserhead",
    help="😐 EraserHead: Erase your digital footprint. Harold approves.",
    no_args_is_help=True,
)

# Default paths
DEFAULT_VAULT_DIR = Path.home() / ".config" / "eraserhead" / "vault"
DEFAULT_QUEUE_PATH = Path.home() / ".config" / "eraserhead" / "queue.json"


# ============================================================================
# Helper
# ============================================================================


def _run_async() -> None:
    """Placeholder for running async functions synchronously via trio."""
    # 😐 Not currently used — trio.run() called directly in scrub command


# ============================================================================
# Vault Commands
# ============================================================================


vault_app = typer.Typer(help="😐 Manage credential vault.")
app.add_typer(vault_app, name="vault")


@vault_app.command("store")
def vault_store(
    platform: Annotated[str, typer.Argument(help="Platform name")],
    username: Annotated[str, typer.Argument(help="Account username")],
    token: Annotated[str, typer.Option("--token", help="Auth token")] = "",
    api_key: Annotated[str, typer.Option("--api-key", help="API key")] = "",
    api_secret: Annotated[str, typer.Option("--api-secret", help="API secret")] = "",
    passphrase: Annotated[
        str,
        typer.Option("--passphrase", "-p", help="Vault passphrase", prompt=True, hide_input=True),
    ] = "",
    vault_dir: Annotated[
        Path, typer.Option("--vault-dir", help="Vault directory")
    ] = DEFAULT_VAULT_DIR,
) -> None:
    """Store credentials for a platform."""
    try:
        plat = Platform(platform.lower())
    except ValueError:
        typer.echo(f"😐 Unknown platform: {platform}")
        typer.echo(f"   Available: {', '.join(p.value for p in Platform)}")
        raise typer.Exit(1) from None

    vault = CredentialVault(vault_dir)
    try:
        vault.unlock(passphrase)
    except VaultError as e:
        typer.echo(f"🌑 Vault error: {e}")
        raise typer.Exit(1) from None

    creds = PlatformCredentials(
        platform=plat,
        username=username,
        auth_token=token,
        api_key=api_key,
        api_secret=api_secret,
    )
    vault.store(creds)
    vault.lock()
    typer.echo(f"✅ Credentials stored for {plat.value}:{username}")


@vault_app.command("list")
def vault_list(
    passphrase: Annotated[
        str,
        typer.Option("--passphrase", "-p", help="Vault passphrase", prompt=True, hide_input=True),
    ] = "",
    vault_dir: Annotated[
        Path, typer.Option("--vault-dir", help="Vault directory")
    ] = DEFAULT_VAULT_DIR,
) -> None:
    """List stored credentials."""
    vault = CredentialVault(vault_dir)
    try:
        vault.unlock(passphrase)
    except VaultError as e:
        typer.echo(f"🌑 Vault error: {e}")
        raise typer.Exit(1) from None

    platforms = vault.list_platforms()
    vault.lock()

    if not platforms:
        typer.echo("😐 No credentials stored yet.")
        return

    typer.echo("📋 Stored credentials:")
    for plat, user in platforms:
        typer.echo(f"  • {plat.value}: {user}")


@vault_app.command("remove")
def vault_remove(
    platform: Annotated[str, typer.Argument(help="Platform name")],
    username: Annotated[str, typer.Argument(help="Account username")],
    passphrase: Annotated[
        str,
        typer.Option("--passphrase", "-p", help="Vault passphrase", prompt=True, hide_input=True),
    ] = "",
    vault_dir: Annotated[
        Path, typer.Option("--vault-dir", help="Vault directory")
    ] = DEFAULT_VAULT_DIR,
) -> None:
    """Remove stored credentials."""
    try:
        plat = Platform(platform.lower())
    except ValueError:
        typer.echo(f"😐 Unknown platform: {platform}")
        raise typer.Exit(1) from None

    vault = CredentialVault(vault_dir)
    try:
        vault.unlock(passphrase)
    except VaultError as e:
        typer.echo(f"🌑 Vault error: {e}")
        raise typer.Exit(1) from None

    removed = vault.remove(plat, username)
    vault.lock()

    if removed:
        typer.echo(f"✅ Credentials removed for {plat.value}:{username}")
    else:
        typer.echo(f"😐 No credentials found for {plat.value}:{username}")


# ============================================================================
# Scrub Commands
# ============================================================================


@app.command("scrub")
def scrub(
    platform: Annotated[str, typer.Argument(help="Platform to scrub")],
    resource_type: Annotated[
        str, typer.Option("--type", "-t", help="Resource type (post, comment, like, photo, etc.)")
    ] = "post",
    resource_ids: Annotated[
        str | None, typer.Option("--ids", help="Comma-separated resource IDs")
    ] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Preview without deleting")] = False,
    priority: Annotated[
        str, typer.Option("--priority", help="Task priority (urgent/high/standard/low/background)")
    ] = "standard",
    passphrase: Annotated[
        str,
        typer.Option("--passphrase", "-p", help="Vault passphrase", prompt=True, hide_input=True),
    ] = "",
    vault_dir: Annotated[
        Path, typer.Option("--vault-dir", help="Vault directory")
    ] = DEFAULT_VAULT_DIR,
) -> None:
    """
    😐 Scrub resources from a platform.

    If --ids not provided, lists available resources first.
    """
    try:
        plat = Platform(platform.lower())
    except ValueError:
        typer.echo(f"😐 Unknown platform: {platform}")
        raise typer.Exit(1) from None

    try:
        res_type = ResourceType(resource_type.lower())
    except ValueError:
        typer.echo(f"😐 Unknown resource type: {resource_type}")
        typer.echo(f"   Available: {', '.join(r.value for r in ResourceType)}")
        raise typer.Exit(1) from None

    try:
        prio = {
            "urgent": TaskPriority.URGENT,
            "high": TaskPriority.HIGH,
            "standard": TaskPriority.STANDARD,
            "low": TaskPriority.LOW,
            "background": TaskPriority.BACKGROUND,
        }[priority.lower()]
    except KeyError:
        typer.echo(f"😐 Unknown priority: {priority}")
        raise typer.Exit(1) from None

    if not resource_ids:
        typer.echo("😐 No resource IDs provided. Use --ids tweet-1,tweet-2,...")
        raise typer.Exit(1) from None

    ids = [rid.strip() for rid in resource_ids.split(",") if rid.strip()]

    # Load credentials
    vault = CredentialVault(vault_dir)
    try:
        vault.unlock(passphrase)
    except VaultError as e:
        typer.echo(f"🌑 Vault error: {e}")
        raise typer.Exit(1) from None

    try:
        creds = vault.get(plat, _find_username(vault, plat))
    except Exception as e:
        typer.echo(f"🌑 No credentials for {plat.value}: {e}")
        vault.lock()
        raise typer.Exit(1) from None

    vault.lock()

    # Run scrubbing
    mode = "DRY RUN" if dry_run else "LIVE"
    typer.echo(f"\n😐 Starting scrub [{mode}]")
    typer.echo(f"   Platform: {plat.value}")
    typer.echo(f"   Type: {res_type.value}")
    typer.echo(f"   Tasks: {len(ids)}")
    typer.echo(f"   Priority: {priority}")
    typer.echo()

    config = EngineConfig(
        dry_run=dry_run,
        verify_after_delete=not dry_run,
    )

    async def _run() -> None:
        adapter = get_adapter(plat)
        await adapter.authenticate(creds)

        engine = ScrubEngine(config)
        engine.register_adapter(adapter)
        engine.add_tasks(plat, res_type, ids, prio)

        results = await engine.run()

        for r in results:
            status = "✅" if r.success else "❌"
            typer.echo(f"  {status} {r.task_id}: {r.proof or r.error_message}")

        success_count = sum(1 for r in results if r.success)
        typer.echo(f"\n😐 Complete: {success_count}/{len(results)} succeeded")

    trio.run(_run)


@app.command("status")
def status(
    queue_path: Annotated[
        Path, typer.Option("--queue", help="Queue file path")
    ] = DEFAULT_QUEUE_PATH,
) -> None:
    """Show current queue status."""
    from eraserhead.queue import QueueError, TaskQueue

    if not queue_path.exists():
        typer.echo("😐 No queue file found. Nothing pending.")
        return

    try:
        queue = TaskQueue.load(queue_path)
    except QueueError as e:
        typer.echo(f"🌑 Error loading queue: {e}")
        raise typer.Exit(1) from None

    stats = queue.get_stats()
    typer.echo("📊 Queue Status:")
    typer.echo(f"  Total:     {stats.total}")
    typer.echo(f"  Pending:   {stats.pending}")
    typer.echo(f"  Running:   {stats.running}")
    typer.echo(f"  Completed: {stats.completed}")
    typer.echo(f"  Failed:    {stats.failed}")
    typer.echo(f"  Retrying:  {stats.retrying}")
    typer.echo(f"  Cancelled: {stats.cancelled}")


@app.command("version")
def version() -> None:
    """Show EraserHead version."""
    typer.echo("😐 EraserHead v0.1.0-alpha")
    typer.echo("   Harold's Digital Footprint Eraser")
    typer.echo("   🌑 Everything is compromised. We're here to help.")


# ============================================================================
# Helpers
# ============================================================================


def _find_username(vault: CredentialVault, platform: Platform) -> str:
    """Find the first username for a platform in the vault."""
    for plat, user in vault.list_platforms():
        if plat == platform:
            return user
    raise ValueError(f"No credentials for {platform}")


# ============================================================================
# Entry Point
# ============================================================================


def main() -> None:
    """CLI entry point."""
    app()


if __name__ == "__main__":
    main()
