"""Telegram source — reads messages using Telethon (MTProto user client).

Can read groups, channels, and DMs the user account can see.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from telethon import TelegramClient
from telethon.errors import RPCError

from src.config import TelegramAccountConfig

from .base import ClassifiedItem, Source, SourceItem

log = logging.getLogger(__name__)


class TelegramSource(Source[TelegramAccountConfig]):
    """Telegram source: reads recent messages from watched chats."""

    @property
    def source_name(self) -> str:
        return "telegram"

    async def fetch(self) -> list[SourceItem]:
        items: list[SourceItem] = []
        config = self.config

        client = TelegramClient(
            session=config.session_file,
            api_id=config.api_id,
            api_hash=config.api_hash.get_secret_value(),
        )

        try:
            await client.start()
        except Exception as e:
            log.error("Telegram auth failed for %s: %s", config.name, e)
            return items

        try:
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
        from src.prompt_manager import PromptManager

        pm = PromptManager("./prompts")
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
