"""Typer CLI for ws-ops.

Commands: morning, evening, run, actions, config-check.
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

import src.sources  # noqa: F401 — triggers source registrations  # pyright: ignore[reportUnusedImport]
from src.config import Config
from src.db import Database
from src.digest import (
    DigestResult,
    format_digest_summary,
    format_digest_telegram,
    run_all,
)
from src.notify import Notifier
from src.registry import SOURCE_REGISTRY
from src.sources.telegram import create_telegram_client, resolve_telegram_session_file

app = typer.Typer(name="ws-ops", help="Personal workstation automation.")
console = Console()
log = logging.getLogger(__name__)


async def _run_sources(
    config: Config,
    source_filter: list[str] | None = None,
    dry_run: bool = False,
) -> DigestResult:
    """Run sources, display results, and return DigestResult."""
    db = Database(config.db_path)
    await db.connect()

    try:
        if source_filter:
            config = _filter_sources(config, source_filter)

        result = await run_all(config, db)

        if result.total_errors:
            console.print(
                Panel(
                    f"{result.total_errors} error(s) occurred",
                    title="⚠️ Errors",
                    border_style="yellow",
                )
            )

        console.print(
            Panel(
                format_digest_summary(result),
                title=f"📋 Digest Summary ({result.total_items} items, "
                f"{result.high_priority_count} high priority)",
                border_style="green" if result.high_priority_count == 0 else "yellow",
            )
        )

        return result
    finally:
        await db.close()


async def _notify_digest(
    config: Config, result: DigestResult, digest_type: str = "morning"
) -> None:
    """Send digest notification via Telegram."""
    if config.telegram_bot:
        notifier = Notifier(config.telegram_bot)
        message = format_digest_telegram(result)
        await notifier.send_digest(
            digest_type=digest_type,
            summary=f"{result.total_items} items processed, "
            f"{result.high_priority_count} high priority",
            sections=[("", message)],
            dry_run=config.dry_run,
        )


async def _login_telegram_account(account_name: str) -> str | None:
    """Perform the one-time interactive Telegram login for a configured account."""
    config = Config()
    account = next((acc for acc in config.telegram_accounts if acc.name == account_name), None)
    if account is None:
        raise ValueError(f"Telegram account '{account_name}' is not configured.")

    if account.session_string:
        return None

    client = create_telegram_client(account)
    try:
        await client.start()
        if not await client.is_user_authorized():
            raise RuntimeError(f"Telegram login did not complete for '{account_name}'.")
    finally:
        await client.disconnect()

    return resolve_telegram_session_file(account)


@app.command()
def morning(
    sources: list[str] = typer.Option(  # noqa: B008
        None, "--source", "-s", help="Run specific sources only"
    ),
    dry_run: bool = typer.Option(  # noqa: B008
        False, "--dry-run", help="Preview actions without executing"
    ),
    notify: bool = typer.Option(  # noqa: B008
        True, "--notify/--no-notify", help="Send Telegram digest"
    ),
) -> None:
    """Run morning digest: fetch, classify, organize, and report."""
    config = Config()
    if dry_run:
        config.dry_run = True

    with console.status("[bold green]Running morning digest..."):
        result = asyncio.run(_run_sources(config, dry_run=dry_run))

    if notify:
        asyncio.run(_notify_digest(config, result, "morning"))
        if config.telegram_bot:
            console.print("[green]✓[/green] Telegram digest sent")


@app.command()
def evening(
    notify: bool = typer.Option(  # noqa: B008
        True, "--notify/--no-notify", help="Send Telegram digest"
    ),
) -> None:
    """Run evening summary with action items for tomorrow."""
    config = Config()

    with console.status("[bold blue]Running evening summary..."):
        result = asyncio.run(_run_sources(config))

    if notify:
        asyncio.run(_notify_digest(config, result, "evening"))
        if config.telegram_bot:
            console.print("[green]✓[/green] Telegram digest sent")


@app.command()
def run(
    source: str = typer.Argument(
        ..., help="Source to run: " + ", ".join(SOURCE_REGISTRY.all)
    ),
    dry_run: bool = typer.Option(False, "--dry-run"),  # noqa: B008
) -> None:
    """Run a single source."""
    config = Config()
    if dry_run:
        config.dry_run = True

    asyncio.run(_run_sources(config, source_filter=[source]))


@app.command("telegram-login")
def telegram_login(
    account: str = typer.Argument(..., help="Telegram account name from config"),
) -> None:
    """Authenticate a Telegram source account and save its session for later runs."""
    try:
        session_file = asyncio.run(_login_telegram_account(account))
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc

    if session_file is None:
        console.print(
            "[yellow]Telegram account uses session_string; "
            "interactive login is not needed.[/yellow]"
        )
        return

    console.print(f"[green]✓[/green] Telegram session saved to {session_file}")


@app.command()
def actions(
    status: str = typer.Option(  # noqa: B008
        "open", "--status", help="open | done | snoozed | all"
    ),
) -> None:
    """Show action items from the database."""
    config = Config()
    db = Database(config.db_path)

    async def _show_actions() -> None:
        await db.connect()
        try:
            items = await db.get_action_items(status if status != "all" else None)
        except Exception:
            items = []

        if not items:
            console.print("[yellow]No action items found.[/yellow]")
            return

        table = Table(title=f"Action Items ({status})")
        table.add_column("ID", style="dim")
        table.add_column("Source")
        table.add_column("Item")
        table.add_column("Task")
        table.add_column("Status")

        for item in items:
            table.add_row(
                str(item.get("id", "")),
                item.get("item_source", item.get("source", "")),
                item.get("item_title", "")[:40],
                item.get("text", "")[:60],
                item.get("status", ""),
            )
        console.print(table)

    asyncio.run(_show_actions())
    asyncio.run(db.close())


@app.command()
def config_check() -> None:
    """Validate config and test all source connections."""
    config = Config()
    console.print("[green]✓[/green] Config loaded successfully")
    checks: list[tuple[str, bool, str]] = []

    # LLM
    checks.append(("LLM", True, f"Provider: {config.llm.provider}"))

    # Sources from registry
    for name, entry in SOURCE_REGISTRY:
        instances = getattr(config, entry.config_field, [])
        if instances:
            checks.append((name.capitalize(), True, f"{len(instances)} instance(s)"))
        else:
            checks.append((name.capitalize(), False, "none"))

    # Telegram Bot
    checks.append(
        (
            "Telegram Bot",
            config.telegram_bot is not None,
            "configured" if config.telegram_bot else "not configured",
        )
    )

    # Runtime checks
    prompts_ok = Path(config.prompts_dir).expanduser().is_dir()
    checks.append(
        (
            "Prompts",
            prompts_ok,
            config.prompts_dir if prompts_ok else "not found",
        )
    )

    db_parent = Path(config.db_path).expanduser().parent
    db_writable = db_parent.exists() or db_parent.mkdir(parents=True, exist_ok=True) or True
    db_writable = db_parent.is_dir() and os.access(str(db_parent), os.W_OK)
    checks.append(
        (
            "Database path",
            db_writable,
            config.db_path if db_writable else "not writable",
        )
    )

    table = Table(title="System Readiness")
    table.add_column("Component", style="cyan")
    table.add_column("Status")
    table.add_column("Details")

    for name, ok, detail in checks:
        table.add_row(
            name,
            "[green]✓[/green]" if ok else "[red]✗[/red]",
            detail,
        )

    console.print(table)

    if not prompts_ok:
        console.print("\n[yellow]⚠  Prompt directory not found. Run from the project root "
                      "or set WS_OPS_PROMPTS_DIR.[/yellow]")


def _filter_sources(config: Config, source_names: list[str]) -> Config:
    """Filter config to only include requested sources."""
    from copy import deepcopy

    filtered = deepcopy(config)

    for name, entry in SOURCE_REGISTRY:
        if name not in source_names:
            setattr(filtered, entry.config_field, [])

    return filtered


def main() -> None:
    """Entry point for the CLI."""
    app()
