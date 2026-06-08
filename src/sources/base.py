"""Abstract source interface for all data sources.

Every source (email, GitLab, GitHub, Telegram, Jira) implements this interface.
Adding a new source means creating a new module under sources/ implementing Source.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Generic, TypeVar

if TYPE_CHECKING:
    from src.db import Database
    from src.llm import LLMProvider
    from src.prompt_manager import PromptManager


@dataclass
class SourceItem:
    """Base unit of information from any source."""

    id: str
    source: str
    title: str
    body: str
    url: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict = field(default_factory=dict)


@dataclass
class ClassifiedItem:
    """A source item after LLM classification."""

    item: SourceItem
    category: str
    action: str
    priority: str
    summary: str
    action_items: list[str]
    folder: str | None = None
    requires_response: bool = False


@dataclass
class SourceResult:
    """Result from running a single source."""

    source: str
    items: list[ClassifiedItem]
    errors: list[str] = field(default_factory=list)
    fetched_at: datetime = field(default_factory=lambda: datetime.now(UTC))


SourceConfigT = TypeVar("SourceConfigT")


class Source(ABC, Generic[SourceConfigT]):  # noqa: UP046
    """All sources implement this interface.

    The pipeline is: fetch() → classify() → act() → SourceResult.
    """

    def __init__(
        self,
        config: SourceConfigT,
        llm: LLMProvider,
        db: Database,
        prompt_manager: PromptManager | None = None,
        dry_run: bool = False,
    ) -> None:
        self.config = config
        self.llm = llm
        self.db = db
        self.dry_run = dry_run
        self.label = config.name if hasattr(config, "name") else config.__class__.__name__
        self.prompt_manager = prompt_manager

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Short source identifier, e.g. 'email', 'gitlab'."""
        ...

    @abstractmethod
    async def fetch(self) -> list[SourceItem]:
        """Fetch raw items from the source."""
        ...

    @abstractmethod
    async def classify(self, item: SourceItem) -> ClassifiedItem:
        """Classify a single item using LLM."""
        ...

    @abstractmethod
    async def act(self, item: ClassifiedItem) -> None:
        """Execute the action — respects dry_run."""
        ...

    async def run(self) -> SourceResult:
        """Full pipeline: fetch → classify → act."""
        items = await self.fetch()
        classified: list[ClassifiedItem] = []
        errors: list[str] = []

        for item in items:
            try:
                if not self.dry_run and await self.db.item_exists(item.id):
                    continue  # already processed (skip dedup check in dry-run)

                c = await self.classify(item)

                await self.act(c)

                if not self.dry_run:
                    await self.db.insert_item(
                        item_id=item.id,
                        source=f"{self.source_name}:{self.label}",
                        title=item.title,
                        category=c.category,
                        action=c.action,
                        priority=c.priority,
                        summary=c.summary,
                        folder=c.folder,
                        account=self.label,
                        requires_response=c.requires_response,
                        acted=True,
                    )

                    for ai_text in c.action_items:
                        await self.db.upsert_action_item(
                            source_item_id=item.id,
                            text=ai_text,
                            source=f"{self.source_name}:{self.label}",
                        )

                classified.append(c)
            except Exception as e:
                errors.append(f"{item.id}: {e}")

        return SourceResult(
            source=f"{self.source_name}:{self.label}",
            items=classified,
            errors=errors,
        )
