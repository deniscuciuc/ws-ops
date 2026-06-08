"""Tests for PromptManager."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from src.prompt_manager import PromptManager


@pytest.fixture
def prompts_dir(tmp_path: Path) -> Path:
    """Create a temporary prompts directory with a test prompt."""
    prompts = tmp_path / "prompts"
    prompts.mkdir()

    data = {
        "name": "test_prompt",
        "version": "1.0",
        "description": "A test prompt",
        "system": "You are a test assistant.",
        "user": "Hello {{ name }}!",
        "output_schema": {"greeting": "str"},
    }
    (prompts / "test_prompt.yaml").write_text(yaml.dump(data))
    return prompts


class TestPromptManager:
    def test_get_prompt(self, prompts_dir: Path) -> None:
        pm = PromptManager(str(prompts_dir))
        prompt = pm.get("test_prompt")
        assert prompt.name == "test_prompt"
        assert prompt.version == "1.0"
        assert prompt.system == "You are a test assistant."
        assert prompt.output_schema == {"greeting": "str"}

    def test_render_user(self, prompts_dir: Path) -> None:
        pm = PromptManager(str(prompts_dir))
        rendered = pm.render_user("test_prompt", name="World")
        assert rendered == "Hello World!"

    def test_get_cached(self, prompts_dir: Path) -> None:
        pm = PromptManager(str(prompts_dir))
        p1 = pm.get("test_prompt")
        p2 = pm.get("test_prompt")
        assert p1 is p2

    def test_missing_prompt_raises(self, tmp_path: Path) -> None:
        pm = PromptManager(str(tmp_path))
        with pytest.raises(FileNotFoundError):
            pm.get("nonexistent")
