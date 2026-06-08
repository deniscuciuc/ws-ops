"""Tests for LLM provider abstraction."""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from pydantic import SecretStr

from src.llm import get_provider


@dataclass
class FakeOllamaConfig:
    base_url: str = "http://localhost:11434"
    model: str = "test-model"
    timeout: int = 5


@dataclass
class FakeOpenAIConfig:
    api_key: object
    model: str = "gpt-4o-mini"
    base_url: str = "https://api.openai.com/v1"


@dataclass
class FakeLLMConfig:
    provider: str
    ollama: object = None
    openai: object = None


class TestGetProvider:
    def test_ollama_provider(self) -> None:
        config = FakeLLMConfig(
            provider="ollama",
            ollama=FakeOllamaConfig(),
        )
        provider = get_provider(config)  # type: ignore[arg-type]
        from src.llm import OllamaProvider

        assert isinstance(provider, OllamaProvider)

    def test_openai_provider(self) -> None:
        config = FakeLLMConfig(
            provider="openai",
            openai=FakeOpenAIConfig(api_key="sk-test"),
        )
        with pytest.raises(AttributeError):
            # Fails because FakeOpenAIConfig.api_key is a str, not SecretStr
            get_provider(config)  # type: ignore[arg-type]

    def test_openai_provider_with_secret(self) -> None:
        config = FakeLLMConfig(
            provider="openai",
            openai=FakeOpenAIConfig(api_key=SecretStr("sk-test")),
        )
        provider = get_provider(config)  # type: ignore[arg-type]
        from src.llm import OpenAIProvider

        assert isinstance(provider, OpenAIProvider)

    def test_unknown_provider_raises(self) -> None:
        config = FakeLLMConfig(provider="invalid")
        with pytest.raises(ValueError, match="Unknown provider"):
            get_provider(config)  # type: ignore[arg-type]
