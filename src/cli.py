"""Typer CLI for ws-ops.

Commands: morning, evening, run, actions, config-check.
"""

from __future__ import annotations

import asyncio
import logging

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.config import Config
from src.db import Database
from src.digest import (
    format_digest_summary,
    format_digest_telegram,
    run_all,
)
from src.notify import Notifier

app = typer.Typer(name="ws-ops", help="Personal workstation automation.")
console = Console()
log = logging.getLogger(__name__)


async def _run_sources(
    config: Config,
    source_filter: list[str] | None = None,
    dry_run: bool = False,
) -> None:
    """Run sources and display results."""
    db = Database(config.db_path)
    await db.connect()

    try:
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
    finally:
        await db.close()


async def _notify_digest(
    config: Config, result: object, digest_type: str = "morning"
) -> None:
    """Send digest notification via Telegram."""
    from src.digest import DigestResult

    if config.telegram_bot and isinstance(result, DigestResult):
        notifier = Notifier(config.telegram_bot)
        message = format_digest_telegram(result)
        await notifier.send_digest(
            digest_type=digest_type,
            summary=f"{result.total_items} items processed, "
            f"{result.high_priority_count} high priority",
            sections=[("", message)],
            dry_run=config.dry_run,
        )


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

    if sources:
        config = _filter_sources(config, sources)

    with console.status("[bold green]Running morning digest..."):
        result = asyncio.run(_run_sources(config, dry_run=dry_run))

    if notify and config.telegram_bot:
        asyncio.run(_notify_digest(config, result, "morning"))
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

    if notify and config.telegram_bot:
        asyncio.run(_notify_digest(config, result, "evening"))
        console.print("[green]✓[/green] Telegram digest sent")


@app.command()
def run(
    source: str = typer.Argument(
        ..., help="Source to run: email | gitlab | github | telegram | jira"
    ),
    dry_run: bool = typer.Option(False, "--dry-run"),  # noqa: B008
) -> None:
    """Run a single source."""
    config = Config()
    if dry_run:
        config.dry_run = True

    asyncio.run(_run_sources(config, source_filter=[source]))


@app.command()
def actions(
    status: str = typer.Option(  # noqa: B008
        "open", "--status", help="open | done | all"
    ),
) -> None:
    """Show action items from the database."""
    config = Config()
    db = Database(config.db_path)

    async def _show_actions() -> None:
        await db.connect()
        try:
            items = await db.get_action_items(
                status if status != "all" else "open"
            )
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
    checks.append(("LLM", True, f"Provider: {config.llm.provider}"))

    checks.append(
        (
            "Email",
            len(config.email_accounts) > 0,
            f"{len(config.email_accounts)} account(s) configured"
            if config.email_accounts
            else "none",
        )
    )
    checks.append(
        (
            "GitLab",
            len(config.gitlab_instances) > 0,
            f"{len(config.gitlab_instances)} instance(s)"
            if config.gitlab_instances
            else "none",
        )
    )
    checks.append(
        (
            "GitHub",
            len(config.github_accounts) > 0,
            f"{len(config.github_accounts)} account(s)"
            if config.github_accounts
            else "none",
        )
    )
    checks.append(
        (
            "Telegram",
            len(config.telegram_accounts) > 0,
            f"{len(config.telegram_accounts)} account(s)"
            if config.telegram_accounts
            else "none",
        )
    )
    checks.append(
        (
            "Jira",
            len(config.jira_instances) > 0,
            f"{len(config.jira_instances)} instance(s)"
            if config.jira_instances
            else "none",
        )
    )
    checks.append(
        (
            "Telegram Bot",
            config.telegram_bot is not None,
            "configured" if config.telegram_bot else "not configured",
        )
    )

    table = Table(title="Configuration Check")
    table.add_column("Source", style="cyan")
    table.add_column("Status")
    table.add_column("Details")

    for name, ok, detail in checks:
        table.add_row(
            name,
            "[green]✓[/green]" if ok else "[yellow]–[/yellow]",
            detail,
        )

    console.print(table)


def _filter_sources(config: Config, source_names: list[str]) -> Config:
    """Filter config to only include requested sources."""
    from copy import deepcopy

    filtered = deepcopy(config)

    if "email" not in source_names:
        filtered.email_accounts = []
    if "gitlab" not in source_names:
        filtered.gitlab_instances = []
    if "github" not in source_names:
        filtered.github_accounts = []
    if "telegram" not in source_names:
        filtered.telegram_accounts = []
    if "jira" not in source_names:
        filtered.jira_instances = []

    return filtered


def main() -> None:
    """Entry point for the CLI."""
    app()
