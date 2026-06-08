"""Tests for GitLabSource."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.sources.gitlab import GitLabSource


class TestGitLabSource:
    @pytest.mark.asyncio
    async def test_classify_returns_classified_item(self) -> None:
        """Verify classify produces a ClassifiedItem with expected fields."""
        from src.sources.base import SourceItem

        mock_config = MagicMock()
        mock_config.name = "test"

        mock_llm = AsyncMock()
        mock_db = AsyncMock()

        source = GitLabSource(mock_config, mock_llm, mock_db)

        item = SourceItem(
            id="gitlab:test:mr:1",
            source="gitlab",
            title="Test MR",
            body="Description",
            url="https://gitlab.com/test/merge_requests/1",
            metadata={"type": "mr"},
        )

        result = await source.classify(item)
        assert result.item is item
        assert result.priority == "medium"
        assert len(result.action_items) == 1
