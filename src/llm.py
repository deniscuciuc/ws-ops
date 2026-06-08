"""LLM provider abstraction.

Supports Ollama (local), OpenAI, and any OpenAI-compatible endpoint.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import httpx

if httpx.__version__ >= "0.28":
    from openai import APIStatusError, OpenAI
else:
    from openai import APIStatusError, OpenAI  # type: ignore[no-redef]

from src.config import LLMConfig, OllamaConfig, OpenAIConfig


@dataclass
class LLMResponse:
    raw: str
    parsed: dict[str, Any] | None = None


class LLMProvider(ABC):
    """Abstract base for all LLM providers."""

    @abstractmethod
    async def complete(
        self,
        system: str,
        user: str,
        expect_json: bool = False,
        temperature: float = 0.1,
    ) -> LLMResponse: ...


class OllamaProvider(LLMProvider):
    """Local Ollama inference via REST API."""

    def __init__(self, config: OllamaConfig) -> None:
        self._config = config

    async def complete(
        self,
        system: str,
        user: str,
        expect_json: bool = False,
        temperature: float = 0.1,
    ) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": self._config.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "options": {"temperature": temperature},
        }
        if expect_json:
            payload["format"] = "json"

        async with httpx.AsyncClient(timeout=self._config.timeout) as client:
            resp = await client.post(
                f"{self._config.base_url.rstrip('/')}/api/chat",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            raw = data["message"]["content"]

        parsed: dict[str, Any] | None = None
        if expect_json:
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = None

        return LLMResponse(raw=raw, parsed=parsed)


class OpenAIProvider(LLMProvider):
    """OpenAI or any OpenAI-compatible endpoint."""

    def __init__(self, config: OpenAIConfig) -> None:
        self._client = OpenAI(
            api_key=config.api_key.get_secret_value(),
            base_url=config.base_url,
        )
        self._model = config.model

    async def complete(
        self,
        system: str,
        user: str,
        expect_json: bool = False,
        temperature: float = 0.1,
    ) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
        }
        if expect_json:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            resp = self._client.chat.completions.create(**kwargs)
            raw = resp.choices[0].message.content or ""
        except APIStatusError as e:
            raise RuntimeError(f"OpenAI API error: {e}") from e

        parsed: dict[str, Any] | None = None
        if expect_json:
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = None

        return LLMResponse(raw=raw, parsed=parsed)


def get_provider(config: LLMConfig) -> LLMProvider:
    """Factory: return the appropriate LLM provider based on config."""
    match config.provider:
        case "ollama":
            return OllamaProvider(config.ollama)
        case "openai":
            assert config.openai is not None, "OpenAI config required"
            return OpenAIProvider(config.openai)
        case "anthropic":
            assert config.openai is not None, "Anthropic requires OpenAI-compat config"
            return OpenAIProvider(config.openai)
        case _:
            raise ValueError(f"Unknown provider: {config.provider}")
