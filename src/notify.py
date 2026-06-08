"""Telegram Bot sender for outbound digest delivery.

Uses python-telegram-bot to send formatted Markdown digests to the user.
"""

from __future__ import annotations

from src.config import TelegramBotConfig


class Notifier:
    """Sends formatted digests to the user's Telegram chat."""

    def __init__(self, config: TelegramBotConfig) -> None:
        self._token = config.token.get_secret_value()
        self._chat_id = config.chat_id

    async def send_message(self, text: str, dry_run: bool = False) -> bool:
        """Send a Markdown-formatted message to the configured chat."""
        if dry_run:
            return True

        from telegram import Bot

        bot = Bot(token=self._token)
        await bot.send_message(
            chat_id=self._chat_id,
            text=text,
            parse_mode="Markdown",
        )
        return True

    async def send_digest(
        self,
        digest_type: str,
        summary: str,
        sections: list[tuple[str, str]],
        dry_run: bool = False,
    ) -> bool:
        """Send a multi-section digest as a formatted message."""
        lines: list[str] = [
            f"*📋 ws-ops {digest_type.title()} Digest*",
            "",
            summary,
            "",
        ]

        for title, content in sections:
            lines.append(f"*{title}*")
            lines.append(content)
            lines.append("")

        message = "\n".join(lines)
        return await self.send_message(message, dry_run=dry_run)
