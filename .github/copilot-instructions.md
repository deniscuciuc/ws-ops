# ws-ops — Copilot Instructions

## Project Identity

`ws-ops` is a personal workstation automation CLI for a developer/CTO. It organizes email, digests dev feeds (GitLab, GitHub, Jira, Telegram), and surfaces actionable intelligence using local or remote LLMs. On-demand only — no daemons, no cron jobs.

## Architecture Overview

```
CLI (cli.py) → Digest Engine (digest.py) → Sources (sources/*) → LLM (llm.py) → Prompts (prompts/*)
              ↓                          ↓
         Database (db.py)           Notifier (notify.py)
```

### Data flow

1. **`cli.py`** — Typer app with 5 commands (`morning`, `evening`, `run`, `actions`, `config-check`). Commands that run sources are synchronous wrappers that call `asyncio.run()`.
2. **`digest.py`** — `run_all()` iterates config source lists, creates a `Source` instance per account, and runs them concurrently via `asyncio.gather()`.
3. **Each source** implements the `fetch() → classify() → act()` pipeline defined in `sources/base.py`. The `Source.run()` method handles dedup (checks DB), classification, action execution, DB persistence, and error isolation (one source can't crash another).
4. **`llm.py`** — Abstract `LLMProvider` with `OllamaProvider` (calls `/api/chat` via httpx) and `OpenAIProvider` (uses the openai SDK). Factory function `get_provider()` polymorphically selects the right one.
5. **`prompt_manager.py`** — Loads YAML prompt files from `prompts/` with Jinja2 rendering. Prompts are never hardcoded in source code.
6. **`db.py`** — Async SQLite (`aiosqlite`) with 3 tables: `items` (dedup), `action_items` (extracted tasks), `digests` (run history).

## Configuration System

Every source supports **multiple named accounts/instances**. Config uses `pydantic-settings` with env prefix `WS_OPS_` and `__` as nested delimiter. Multi-instance sources use JSON arrays in environment variables (e.g., `WS_OPS_EMAIL_ACCOUNTS='[{"name": "work", ...}]'`).

**Pattern for adding a new source config**: add a `*Config` class in `config.py`, add a field `list[*Config]` to the root `Config`, and update `.env.example`.

**Secrets**: All passwords, tokens, and keys use pydantic `SecretStr`. Access via `.get_secret_value()` at the call site.

## Source Architecture

### Base interface (`sources/base.py`)

```python
class Source(ABC, Generic[SourceConfigT]):
    async def fetch(self) -> list[SourceItem]: ...      # Fetch raw data
    async def classify(self, item) -> ClassifiedItem: ... # LLM classification
    async def act(self, item: ClassifiedItem) -> None: ... # Execute action
    async def run(self) -> SourceResult: ...             # Orchestrates the above
```

**Key dataclasses**: `SourceItem` (raw), `ClassifiedItem` (after LLM), `SourceResult` (per-source output).

**To add a new source**:
1. Create `src/sources/my_source.py` implementing `Source[MyConfig]`
2. Add `*Config` model to `config.py`
3. Add env vars to `.env.example`
4. Create prompt YAML in `prompts/`
5. Register in `digest.py` `run_all()` function
6. Register in `cli.py` `_filter_sources()`
7. Add docs in `docs/sources/`

### Existing sources

| Source | Read-only? | SDK | Action behavior |
|--------|-----------|-----|-----------------|
| Email | No (moves/deletes) | `imapclient` | `ACTION_MAP` in email.py dispatches IMAP operations |
| GitLab | Yes | `python-gitlab` | No-op act() |
| GitHub | Yes | `PyGitHub` | No-op act() |
| Telegram | Yes | `Telethon` | No-op act(), first run requires interactive auth |
| Jira | Yes | `jira` (atlassian-python-api) | No-op act() |

### Error handling contract

- Errors in `classify()` or `act()` for one item must not crash other items (caught per-item in `Source.run()`)
- Errors in one source must not crash other sources (caught as `Exception` return in `digest.py`'s `asyncio.gather(return_exceptions=True)`)

## LLM Prompt Management

- All prompts live as YAML files under `prompts/`. File name = prompt name (e.g., `email_classify.yaml`).
- Each YAML has: `name`, `version`, `description`, `system` (system prompt), `user` (Jinja2 template), `output_schema` (documentation, not enforced).
- Use `PromptManager.render_user("prompt_name", key=value)` to render the user template.
- Prompts expect JSON output. Pass `expect_json=True` to `LLMProvider.complete()`.
- **Never hardcode prompt strings in source files.**

## LLM Provider Rules

- `OllamaProvider` calls `/api/chat` REST endpoint (not the openai-compatible `/v1/chat/completions`).
- `OpenAIProvider` also serves Anthropic (via compatible endpoint URL override in config).
- `expect_json=True` sends `"format": "json"` for Ollama and `response_format: {"type": "json_object"}` for OpenAI.
- All classification prompts must ask for JSON output and set `temperature=0.1`.

## Database Patterns

- Item IDs follow the pattern `source:account:external_id` (e.g., `email:work:<Message-ID>`, `gitlab:qgcore:mr:42`).
- `items.acted` tracks whether the physical action was executed (not just classified). When `dry_run=True`, `acted` is 0.
- `action_items.status` is one of `open | done | snoozed`.

## Conventions

- **All I/O is async.** Use `asyncio.gather()` for concurrency. CLI commands use `asyncio.run()` as the sync entry point.
- **Every public function has type annotations.** Pyright strict mode must pass.
- **Use `rich` Console** for terminal output (tables, panels, status). Do not use `print()`.
- **Log with `logging.getLogger(__name__)`.** Use `log.exception()` in exception handlers for tracebacks.
- **`dry_run=True` must never mutate external state.** Check `self.dry_run` before any IMAP/DB mutation in `act()`.
- **Never log secrets.** Access `SecretStr` values only at the call site.
- **`from __future__ import annotations`** at the top of every module.
- **Use `datetime.now(UTC)`** (not `utcnow()` — deprecated).
- **Use `contextlib.suppress()`** instead of bare `try/except/pass`.

## Build & Test Commands

```bash
# Install everything
uv sync

# Install package in editable mode
uv pip install -e .

# Run all tests
uv run pytest

# Run a single test file
uv run pytest tests/test_llm.py

# Run a single test
uv run pytest tests/test_llm.py::TestGetProvider::test_ollama_provider -v

# Lint
uv run ruff check

# Auto-fix lint issues
uv run ruff check --fix

# Type check (pyright)
uv run pyright
```
