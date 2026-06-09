"""Tests for TelegramSource."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import SecretStr

from src.config import TelegramAccountConfig
from src.sources.telegram import TelegramSource, create_telegram_client


class TestTelegramSource:
    @pytest.mark.asyncio
    async def test_fetch_skips_unauthorized_session(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Digest runs should not trigger interactive Telethon login prompts."""
        config = TelegramAccountConfig(
            name="personal",
            api_id=123456,
            api_hash=SecretStr("hash"),
            watch_chats=["team"],
        )
        client = MagicMock()
        client.connect = AsyncMock()
        client.is_user_authorized = AsyncMock(return_value=False)
        client.disconnect = AsyncMock()

        with patch("src.sources.telegram.create_telegram_client", return_value=client):
            source = TelegramSource(config, AsyncMock(), AsyncMock())
            items = await source.fetch()

        assert items == []
        assert "ws-ops telegram-login personal" in caplog.text

    def test_create_telegram_client_uses_session_string(self) -> None:
        """session_string should avoid file-backed sessions for env-only auth."""
        config = TelegramAccountConfig(
            name="personal",
            api_id=123456,
            api_hash=SecretStr("hash"),
            session_string=SecretStr("session-string"),
        )

        with (
            patch(
                "src.sources.telegram.StringSession", return_value="session-object"
            ) as string_session,
            patch("src.sources.telegram.TelegramClient") as telegram_client,
        ):
            create_telegram_client(config)

        string_session.assert_called_once_with("session-string")
        telegram_client.assert_called_once_with(
            session="session-object",
            api_id=123456,
            api_hash="hash",
        )
