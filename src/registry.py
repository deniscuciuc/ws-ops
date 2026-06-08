"""Source registry — central place to register and discover source plugins.

Adding a new source requires one registration here instead of scattered
edits across digest.py and cli.py.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SourceEntry:
    """Registration entry for a data source."""

    name: str
    config_field: str
    source_class: type  # type[Source] — Generic Source prevents strict typing


#: Global singleton — populated by src/sources/__init__.py on import.
class SourceRegistry:
    """Registry of all available data source types."""

    def __init__(self) -> None:
        self._entries: dict[str, SourceEntry] = {}

    def register(self, entry: SourceEntry) -> None:
        self._entries[entry.name] = entry

    def get(self, name: str) -> SourceEntry | None:
        return self._entries.get(name)

    @property
    def all(self) -> dict[str, SourceEntry]:
        return dict(self._entries)

    def __iter__(self):
        return iter(self._entries.items())


SOURCE_REGISTRY = SourceRegistry()


def register_source(
    name: str, config_field: str, source_class: type
) -> None:
    """Register a source so digest.py and cli.py can discover it."""
    SOURCE_REGISTRY.register(SourceEntry(name, config_field, source_class))
