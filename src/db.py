"""SQLite database layer — lightweight storage for a personal tool.

Tables:
- items: deduplication of processed source items
- action_items: LLM-extracted tasks
- digests: history of morning/evening digests
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import aiosqlite

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS items (
    id              TEXT PRIMARY KEY,
    source          TEXT NOT NULL,
    title           TEXT,
    category        TEXT,
    action          TEXT,
    priority        TEXT,
    summary         TEXT,
    folder          TEXT,
    account         TEXT,
    requires_response INTEGER DEFAULT 0,
    processed_at    TEXT DEFAULT (datetime('now')),
    acted           INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS action_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source_item_id  TEXT REFERENCES items(id),
    text            TEXT NOT NULL,
    source          TEXT,
    status          TEXT DEFAULT 'open',
    created_at      TEXT DEFAULT (datetime('now')),
    snoozed_until   TEXT
);

CREATE TABLE IF NOT EXISTS digests (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    type            TEXT,
    summary         TEXT,
    top_3_focus     TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);
"""


class Database:
    """Async SQLite wrapper for ws-ops storage."""

    def __init__(self, db_path: str) -> None:
        self._path = str(Path(db_path).expanduser())
        self._conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        """Open connection and ensure schema exists."""
        Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self._path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript(SCHEMA_SQL)
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def item_exists(self, item_id: str) -> bool:
        assert self._conn
        cur = await self._conn.execute(
            "SELECT 1 FROM items WHERE id = ?", (item_id,)
        )
        return await cur.fetchone() is not None

    async def insert_item(
        self,
        item_id: str,
        source: str,
        title: str,
        category: str | None = None,
        action: str | None = None,
        priority: str | None = None,
        summary: str | None = None,
        folder: str | None = None,
        account: str | None = None,
        requires_response: bool = False,
        acted: bool = False,
    ) -> None:
        assert self._conn
        await self._conn.execute(
            """INSERT OR IGNORE INTO items
               (id, source, title, category, action, priority, summary,
                folder, account, requires_response, acted)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                item_id,
                source,
                title,
                category,
                action,
                priority,
                summary,
                folder,
                account,
                1 if requires_response else 0,
                1 if acted else 0,
            ),
        )
        await self._conn.commit()

    async def upsert_action_item(
        self, source_item_id: str, text: str, source: str
    ) -> None:
        assert self._conn
        await self._conn.execute(
            """INSERT INTO action_items (source_item_id, text, source)
               VALUES (?, ?, ?)""",
            (source_item_id, text, source),
        )
        await self._conn.commit()

    async def get_action_items(
        self, status: str | None = "open"
    ) -> list[dict[str, Any]]:
        assert self._conn
        if status is None:
            cur = await self._conn.execute(
                """SELECT ai.*, i.title AS item_title, i.source AS item_source
                   FROM action_items ai
                   LEFT JOIN items i ON i.id = ai.source_item_id
                   ORDER BY ai.created_at DESC""",
            )
        else:
            cur = await self._conn.execute(
                """SELECT ai.*, i.title AS item_title, i.source AS item_source
                   FROM action_items ai
                   LEFT JOIN items i ON i.id = ai.source_item_id
                   WHERE ai.status = ?
                   ORDER BY ai.created_at DESC""",
                (status,),
            )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]

    async def save_digest(
        self, digest_type: str, summary: str, top_3_focus: list[str]
    ) -> None:
        assert self._conn
        await self._conn.execute(
            "INSERT INTO digests (type, summary, top_3_focus) VALUES (?, ?, ?)",
            (digest_type, summary, json.dumps(top_3_focus)),
        )
        await self._conn.commit()

    async def mark_acted(self, item_id: str) -> None:
        assert self._conn
        await self._conn.execute(
            "UPDATE items SET acted = 1 WHERE id = ?", (item_id,)
        )
        await self._conn.commit()

    async def mark_action_done(self, action_id: int) -> None:
        assert self._conn
        await self._conn.execute(
            "UPDATE action_items SET status = 'done' WHERE id = ?", (action_id,)
        )
        await self._conn.commit()
