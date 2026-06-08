"""Configuration models using pydantic-settings.

All secrets, endpoints, and thresholds live here — zero hardcodes in source code.
Supports multiple named accounts/instances per source via JSON env vars.

Path resolution uses platformdirs for cross-platform defaults:
- Linux:   ~/.config/ws-ops/  (config),  ~/.local/share/ws-ops/  (data)
- macOS:   ~/Library/Application Support/ws-ops/  (both)
- Windows: %APPDATA%/ws-ops/  (config),  %LOCALAPPDATA%/ws-ops/  (data)
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Literal

import platformdirs
from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# ── Platform paths ────────────────────────────────────────────────────────────

_DATA_DIR = Path(platformdirs.user_data_dir("ws-ops", ensure_exists=True))
_CONFIG_DIR = Path(platformdirs.user_config_dir("ws-ops", ensure_exists=True))


def _resolve_env_file() -> str:
    """Find .env by priority: env override → XDG config dir → CWD → package root.

    Returns the first match so pydantic-settings loads it.
    """
    from os import environ

    explicit = environ.get("WS_OPS_ENV_FILE")
    if explicit:
        return explicit

    candidates = [
        _CONFIG_DIR / ".env",
        Path.cwd() / ".env",
        Path(__file__).resolve().parent.parent / ".env",
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    # Default to config dir — file may not exist yet; pydantic handles missing gracefully
    return str(_CONFIG_DIR / ".env")


def _ensure_prompts(prompts_dir: str) -> str:
    """Copy bundled prompts to the given directory if it is empty or missing.

    Falls back to installed package data, then to a repo-relative path for development.
    """
    dest = Path(prompts_dir).expanduser().resolve()
    if dest.exists() and any(dest.iterdir()):
        return str(dest)  # already populated

    dest.mkdir(parents=True, exist_ok=True)

    # Try package-bundled prompts first (installed via pip/uv tool install)
    try:
        import importlib.resources as ilr

        if ilr.is_resource("src", "prompts"):
            # Copy each bundled prompt
            for f in ilr.files("src.prompts").iterdir():
                name = str(f.name)
                if name.endswith(".yaml"):
                    shutil.copy2(str(f), str(dest / name))
            return str(dest)
    except (ModuleNotFoundError, TypeError, FileNotFoundError):
        pass

    # Fallback: repo-relative for development
    repo_prompts = Path(__file__).resolve().parent.parent / "prompts"
    if repo_prompts.is_dir():
        for f in repo_prompts.glob("*.yaml"):
            shutil.copy2(str(f), str(dest / f.name))

    return str(dest)


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
    session_file: str | None = None
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
        env_file=_resolve_env_file(),
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
    output_dir: str = str(_DATA_DIR / "output")
    db_path: str = str(_DATA_DIR / "ws_ops.db")
    prompts_dir: str = str(_DATA_DIR / "prompts")

    @model_validator(mode="after")
    def _init_runtime_paths(self) -> Config:
        """Ensure runtime directories exist and prompts are populated on first run."""
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        Path(self.output_dir).expanduser().resolve().mkdir(parents=True, exist_ok=True)
        self.prompts_dir = _ensure_prompts(self.prompts_dir)
        return self
