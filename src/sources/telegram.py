"""Telegram source — reads messages using Telethon (MTProto user client).

Can read groups, channels, and DMs the user account can see.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

import platformdirs
from telethon import TelegramClient
from telethon.errors import RPCError
from telethon.sessions import StringSession

from src.config import TelegramAccountConfig

from .base import ClassifiedItem, Source, SourceItem

log = logging.getLogger(__name__)


def resolve_telegram_session_file(config: TelegramAccountConfig) -> str:
    """Return session_file from config or generate a default in the data dir."""
    if config.session_file:
        return str(Path(config.session_file).expanduser().resolve())
    data_dir = Path(platformdirs.user_data_dir("ws-ops", ensure_exists=True))
    return str(data_dir / f"tg_{config.name}.session")


def create_telegram_client(config: TelegramAccountConfig) -> TelegramClient:
    """Create a Telegram client from either a saved session string or session file."""
    session: str | StringSession = resolve_telegram_session_file(config)
    if config.session_string:
        session = StringSession(config.session_string.get_secret_value())

    return TelegramClient(
        session=session,
        api_id=config.api_id,
        api_hash=config.api_hash.get_secret_value(),
    )


class TelegramSource(Source[TelegramAccountConfig]):
    """Telegram source: reads recent messages from watched chats."""

    @property
    def source_name(self) -> str:
        return "telegram"

    async def fetch(self) -> list[SourceItem]:
        items: list[SourceItem] = []
        config = self.config

        client = create_telegram_client(config)

        try:
            await client.connect()
        except Exception as e:
            log.error("Telegram connection failed for %s: %s", config.name, e)
            return items

        try:
            if not await client.is_user_authorized():
                log.error(
                    "Telegram auth required for %s: no saved session found. "
                    "Run `ws-ops telegram-login %s` once or configure session_string.",
                    config.name,
                    config.name,
                )
                return items

            dialogs = await client.get_dialogs()
            watch_chats = [str(c) for c in config.watch_chats]

            for dialog in dialogs:
                if watch_chats and dialog.name not in watch_chats:
                    continue

                # Filter by type
                if dialog.is_group and not config.fetch_groups:
                    continue
                if dialog.is_channel and not config.fetch_channels:
                    continue
                if dialog.is_user and not config.fetch_dms:
                    continue

                try:
                    if config.unread_only:
                        # Telethon marks unread via dialog.unread_count
                        if dialog.unread_count == 0:
                            continue
                        limit = min(dialog.unread_count, config.message_limit)
                    else:
                        limit = config.message_limit

                    messages = await client.get_messages(
                        dialog.entity, limit=limit
                    )

                    for msg in messages:
                        if msg.message is None:
                            continue

                        ts = msg.date.replace(tzinfo=UTC) if msg.date else datetime.now(UTC)

                        items.append(
                            SourceItem(
                                id=f"telegram:{config.name}:{msg.id}",
                                source="telegram",
                                title=f"[{dialog.name}] {msg.sender_id}",
                                body=msg.message,
                                timestamp=ts,
                                metadata={
                                    "chat": dialog.name,
                                    "sender_id": msg.sender_id,
                                    "msg_id": msg.id,
                                },
                            )
                        )
                except RPCError:
                    log.exception("Failed to fetch messages from %s", dialog.name)
                    continue

        finally:
            await client.disconnect()

        return items

    async def classify(self, item: SourceItem) -> ClassifiedItem:
        assert self.prompt_manager is not None, "PromptManager required for classify"
        pm = self.prompt_manager
        hours = 24

        user_msg = pm.render_user(
            "telegram_extract",
            chat_name=item.metadata.get("chat", "unknown"),
            hours=hours,
            messages=item.body,
        )

        system_prompt = pm.get("telegram_extract").system
        response = await self.llm.complete(
            system=system_prompt, user=user_msg, expect_json=True
        )

        data = response.parsed or {
            "action_items": [],
            "decisions_made": [],
            "mentions": [],
            "summary": item.body[:200],
        }

        return ClassifiedItem(
            item=item,
            category="notification",
            action="read",
            priority="medium" if data.get("action_items") else "low",
            summary=data.get("summary", item.body[:100]),
            action_items=data.get("action_items", []),
            requires_response=bool(data.get("mentions")),
        )

    async def act(self, item: ClassifiedItem) -> None:
        pass  # Telegram source is read-only
