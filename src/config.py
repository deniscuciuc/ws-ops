"""Configuration models using pydantic-settings.

All secrets, endpoints, and thresholds live here — zero hardcodes in source code.
Supports multiple named accounts/instances per source via JSON env vars.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# ── LLM ──────────────────────────────────────────────────────────────────────


class OllamaConfig(BaseSettings):
    base_url: str = "http://localhost:11434"
    model: str = "llama3.1:8b"
    timeout: int = 120


class OpenAIConfig(BaseSettings):
    api_key: SecretStr
    model: str = "gpt-4o-mini"
    base_url: str = "https://api.openai.com/v1"


class LLMConfig(BaseSettings):
    provider: Literal["ollama", "openai", "anthropic"] = "ollama"
    ollama: OllamaConfig = OllamaConfig()
    openai: OpenAIConfig | None = None


# ── Sources ───────────────────────────────────────────────────────────────────


class EmailAccountConfig(BaseSettings):
    name: str
    host: str
    port: int = 993
    username: str
    password: SecretStr
    use_ssl: bool = True
    fetch_limit: int = 50
    folders_map: dict[str, str] = Field(default_factory=dict)


class GitLabInstanceConfig(BaseSettings):
    name: str
    url: str = "https://gitlab.com"
    token: SecretStr
    groups: list[str] = []
    watch_my_mrs: bool = True
    watch_pipelines: bool = True
    watch_mentions: bool = True


class GitHubAccountConfig(BaseSettings):
    name: str
    token: SecretStr
    orgs: list[str] = []
    watch_my_prs: bool = True
    watch_mentions: bool = True


class TelegramAccountConfig(BaseSettings):
    name: str
    api_id: int
    api_hash: SecretStr
    session_file: str
    watch_chats: list[str | int] = Field(default_factory=list)
    fetch_groups: bool = True
    fetch_channels: bool = True
    fetch_dms: bool = False
    unread_only: bool = True
    message_limit: int = 100


class TelegramBotConfig(BaseSettings):
    token: SecretStr
    chat_id: int


class JiraInstanceConfig(BaseSettings):
    name: str
    server: str
    email: str
    token: SecretStr
    projects: list[str] = []


# ── Root Config ───────────────────────────────────────────────────────────────


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        env_prefix="WS_OPS_",
        extra="ignore",
    )

    llm: LLMConfig = LLMConfig()

    email_accounts: list[EmailAccountConfig] = Field(default_factory=list)
    gitlab_instances: list[GitLabInstanceConfig] = Field(default_factory=list)
    github_accounts: list[GitHubAccountConfig] = Field(default_factory=list)
    telegram_accounts: list[TelegramAccountConfig] = Field(default_factory=list)
    jira_instances: list[JiraInstanceConfig] = Field(default_factory=list)

    telegram_bot: TelegramBotConfig | None = None

    dry_run: bool = False
    output_dir: str = "~/.ws-ops/output"
    db_path: str = "~/.ws-ops/ws_ops.db"
    prompts_dir: str = "./prompts"
