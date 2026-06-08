# ws-ops

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Ruff](https://img.shields.io/badge/code%20style-ruff-000000)](https://github.com/astral-sh/ruff)
[![Pyright](https://img.shields.io/badge/type%20checking-pyright-3178C6)](https://github.com/microsoft/pyright)
[![Status: Alpha](https://img.shields.io/badge/status-alpha-orange)]()

> **Personal AI-powered workstation automation for developers.**  
> Organizes your inbox, digests your dev feeds, and surfaces what matters — all from the terminal.

`ws-ops` is an on-demand CLI that pulls intelligence from your email, GitLab, GitHub, Telegram, and Jira, runs it through an LLM (local or remote), and delivers a concise daily brief. No daemons, no cron jobs, no GUI.

---

## Features

- **📧 Email** — Fetches unseen IMAP mail, classifies with LLM, auto-organizes into folders (archive, work, receipts, etc.). Deduplicates by Message-ID.
- **🦊 GitLab** — Open MRs awaiting your review, failed pipelines across your groups.
- **🐙 GitHub** — Open PRs awaiting review, CI failures on your repos.
- **✈️ Telegram** — Reads groups/channels/DMs via Telethon (your own account). Extracts action items and decisions with LLM.
- **📋 Jira** — Issues assigned to you, sprint progress, upcoming deadlines.
- **🤖 Multi-provider LLM** — Ollama (local), OpenAI, or Anthropic. Pick in config.
- **📦 Multi-account** — Every source supports multiple named instances (e.g., work + personal email).
- **🔒 Privacy-first** — Run entirely local with Ollama. No data leaves your machine.
- **🧪 Dry-run mode** — Preview every action before it executes.

---

## CLI Commands

```bash
# Full morning digest
ws-ops morning

# Run email only, no Telegram notification
ws-ops morning --source email --no-notify

# Preview without executing any actions
ws-ops morning --dry-run

# Run on-demand single source
ws-ops run gitlab

# Evening summary with action items for tomorrow
ws-ops evening

# Show open action items
ws-ops actions

# Validate config and test connections
ws-ops config-check
```

### Shell alias

```bash
alias wso=ws-ops
```

---

## Installation

### Requirements

- **Python 3.12+**
- **[uv](https://github.com/astral-sh/uv)** (fast Python package manager)
- **Ollama** running locally, or API keys for a remote LLM provider

### Setup

```bash
# Clone and enter
git clone https://github.com/deniscuciuc/ws-ops.git
cd ws-ops

# Install dependencies and create virtualenv
uv sync

# Copy and configure
cp .env.example .env
$EDITOR .env

# Install as a global CLI tool
uv tool install .

# Verify setup
ws-ops config-check
```

### Quick Start

1. Configure at least one source in `.env` (see examples in `.env.example`)
2. Run `ws-ops config-check` to verify all connections
3. Run `ws-ops morning` for your first digest
4. Set up the Telegram bot for push notifications (optional)

---

## Configuration

Configuration lives in `.env` or environment variables with the `WS_OPS_` prefix.

```dotenv
# LLM provider: ollama | openai | anthropic
WS_OPS_LLM__PROVIDER=ollama
WS_OPS_LLM__OLLAMA__MODEL=llama3.1:8b

# Sources use JSON arrays for multi-account support
WS_OPS_EMAIL_ACCOUNTS='[{"name": "work", "host": "imap.gmail.com", ...}]'
WS_OPS_GITLAB_INSTANCES='[{"name": "qgcore", "url": "https://gitlab.com", ...}]'
```

Full reference: [docs/configuration.md](docs/configuration.md)

---

## Development

```bash
# Install with dev dependencies
uv sync --group dev

# Run all tests
uv run pytest

# Run a single test
uv run pytest tests/test_llm.py::TestGetProvider::test_ollama_provider -v

# Lint
uv run ruff check

# Auto-fix lint issues
uv run ruff check --fix

# Type check (strict mode)
uv run pyright
```

### Project Structure

```
ws-ops/
├── src/              # Package root
│   ├── cli.py        # Typer CLI — entry point
│   ├── config.py     # pydantic-settings models
│   ├── db.py         # Async SQLite layer
│   ├── digest.py     # Digest engine (orchestrates sources)
│   ├── llm.py        # LLM provider abstraction
│   ├── notify.py     # Telegram Bot outbound sender
│   ├── prompt_manager.py  # YAML prompt loader + Jinja2 renderer
│   └── sources/      # Data source plugins
├── prompts/          # LLM prompts as YAML
├── tests/            # pytest test suite
└── docs/             # Documentation
```

### Architecture

```
CLI → Digest Engine → Sources (concurrent) → LLM → Prompt files
                    ↘ Database (SQLite)
                    ↘ Notifier (Telegram Bot)
```

Each source follows a `fetch()` → `classify()` → `act()` pipeline defined by the `Source` base class in `src/sources/base.py`. New sources implement this interface and register in `digest.py`.

---

## Contributing

Contributions are welcome! Here's how to add a new data source:

1. Create `src/sources/my_source.py` implementing `Source[MyConfig]`
2. Add a `*Config` model to `src/config.py`
3. Add env vars to `.env.example`
4. Create a prompt YAML in `prompts/`
5. Register in `src/digest.py` (add a few lines to `run_all()`)
6. Register in `src/cli.py` (add to `_filter_sources()`)
7. Add docs in `docs/sources/`

**Coding standards:**
- Python 3.12+, all I/O is async
- Type annotations everywhere — pyright strict mode must pass
- Prompts live in YAML, never hardcoded
- `dry_run=True` must never mutate external state
- Errors in one source must not crash others

---

## License

MIT — see [LICENSE](LICENSE).

