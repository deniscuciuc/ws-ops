"""Digest engine — aggregates all sources and produces a unified result.

Runs all configured sources concurrently via asyncio.gather().
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

from src.config import Config
from src.db import Database
from src.llm import get_provider
from src.prompt_manager import PromptManager
from src.registry import SOURCE_REGISTRY
from src.sources.base import SourceResult

log = logging.getLogger(__name__)


@dataclass
class DigestResult:
    """Aggregated result from running all sources."""

    results: list[SourceResult] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def total_items(self) -> int:
        return sum(len(r.items) for r in self.results)

    @property
    def total_errors(self) -> int:
        return sum(len(r.errors) for r in self.results)

    @property
    def high_priority_count(self) -> int:
        return sum(
            1 for r in self.results for item in r.items if item.priority == "high"
        )


async def run_all(config: Config, db: Database) -> DigestResult:
    """Run all configured sources concurrently."""
    llm = get_provider(config.llm)
    prompt_manager = PromptManager(config.prompts_dir)
    tasks: list[asyncio.Task[SourceResult]] = []

    for _entry_name, entry in SOURCE_REGISTRY:
        instances = getattr(config, entry.config_field, [])
        for inst in instances:
            source = entry.source_class(
                inst, llm, db,
                prompt_manager=prompt_manager,
                dry_run=config.dry_run,
            )
            tasks.append(asyncio.create_task(source.run()))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    source_results: list[SourceResult] = []
    for r in results:
        if isinstance(r, Exception):
            log.error("Source run failed: %s", r)
        else:
            source_results.append(r)

    return DigestResult(results=source_results)


def format_digest_summary(result: DigestResult) -> str:
    """Return a human-readable summary of the digest result."""
    lines: list[str] = []

    for sr in result.results:
        high = sum(1 for i in sr.items if i.priority == "high")
        total = len(sr.items)
        errors = len(sr.errors)
        status = f"{high} high, {total} total"
        if errors:
            status += f", {errors} errors"
        lines.append(f"{sr.source}: {status}")

    return "\n".join(lines) if lines else "No data fetched."


def format_digest_telegram(result: DigestResult) -> str:
    """Return a Markdown-formatted digest for Telegram."""
    sections: list[str] = ["*📋 ws-ops Daily Digest*", ""]

    if not result.results:
        sections.append("No data fetched from any source.")
        return "\n".join(sections)

    for sr in result.results:
        high = [i for i in sr.items if i.priority == "high"]
        medium = [i for i in sr.items if i.priority == "medium"]
        lines: list[str] = []
        for item in high:
            lines.append(f"  🔴 *HIGH*: {item.summary}")
        for item in medium:
            lines.append(f"  🟡 *{item.action}*: {item.summary}")
        for item in sr.items:
            if item.priority == "low":
                lines.append(f"  🔵 {item.summary}")

        section = "\n".join(lines) if lines else "  ✅ All clear"
        emoji = _source_emoji(sr.source)
        sections.append(f"{emoji} *{sr.source}*")
        sections.append(section)
        sections.append("")

    return "\n".join(sections)


def _source_emoji(source: str) -> str:
    if source.startswith("email"):
        return "📧"
    if source.startswith("gitlab"):
        return "🦊"
    if source.startswith("github"):
        return "🐙"
    if source.startswith("telegram"):
        return "✈️"
    if source.startswith("jira"):
        return "📋"
    return "📌"
