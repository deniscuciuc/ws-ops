# AI Agent Guide for ws-ops

This is the **canonical reference** for AI coding agents working on ws-ops.
Agent-specific entrypoint files (`.github/copilot-instructions.md`, `AGENTS.md`)
point here to avoid duplication and drift.

## Architecture

```
CLI (cli.py) → Digest Engine (digest.py) → Sources (src/sources/) → LLM (llm.py) → Prompts (prompts/*)
              ↓                          ↓
         Database (db.py)           Notifier (notify.py)
```

### Data flow
1. `cli.py` — Typer app (5 commands). Calls `asyncio.run()` around async logic.
2. `digest.py` — `run_all()` iterates the `SOURCE_REGISTRY`, creates `Source` instances, runs them via `asyncio.gather()`.
3. Each source implements `fetch() → classify() → act()` from `src/sources/base.py`. Dedup, persistence, and error isolation handled by `Source.run()`.
4. `llm.py` — Abstract `LLMProvider` + `OllamaProvider` (REST) + `OpenAIProvider` (SDK).
5. `prompt_manager.py` — Loads YAML prompts from `prompts/`, renders with Jinja2.
6. `db.py` — Async SQLite with 3 tables: `items`, `action_items`, `digests`.

## Adding a New Source

1. Create `src/sources/my_source.py` implementing `Source[MyConfig]`
2. Add `*Config` model to `src/config.py`
3. Add env vars to `.env.example`
4. Create prompt YAML in `prompts/`
5. **Register** in `src/sources/__init__.py` via `register_source()`
6. Add docs in `docs/sources/`

## Key Conventions

- **All I/O is async.** CLI commands use `asyncio.run()` as sync entry point.
- **Every public function has type annotations.** Pyright strict mode must pass.
- **Use `rich` Console** for terminal output — never `print()`.
- **Log with `logging.getLogger(__name__)`.** Use `log.exception()` in handlers.
- **`dry_run=True` must never mutate external state or the dedup DB.**
- **Never hardcode secrets.** Use `SecretStr` and access via `.get_secret_value()`.
- **Prompts live in YAML** under `prompts/` — never hardcoded in source.
- **`from __future__ import annotations`** at the top of every module.
- **Use `datetime.now(UTC)`** (not `utcnow()`).
- **Use `contextlib.suppress()`** instead of bare `try/except/pass`.
- **Paths use `platformdirs`** — cross-platform defaults for config and data.

## Common Commands

```bash
make install          # uv sync
make test             # Run all tests
make test-file f=X    # Run specific test file
make lint             # ruff check
make lint-fix         # ruff check --fix
make typecheck        # pyright
make run ARGS="morning --help"   # Run CLI
make clean            # Remove caches
```

## Source Registry

Sources are registered in `src/sources/__init__.py` using `register_source(name, config_field, SourceClass)` from `src/registry.py`. The registry is iterated by `digest.py` and `cli.py` — no scattered imports needed.

## Error Handling

- Errors in one item's `classify()` or `act()` must not crash other items (caught per-item in `Source.run()`).
- Errors in one source must not crash other sources (`asyncio.gather(return_exceptions=True)` in `digest.py`).

## Database Patterns

- Item IDs: `source:account:external_id` (e.g., `email:work:<Message-ID>`)
- `items.acted` tracks whether the action was executed (0 when `dry_run=True`)
- `action_items.status`: `open | done | snoozed`

## Path Resolution

Paths use `platformdirs`:
- **Config dir**: `~/.config/ws-ops/` (Linux), `~/Library/Application Support/` (macOS)
- **Data dir**: `~/.local/share/ws-ops/` (Linux)
- **`.env` lookup**: env override → config dir → CWD → package root
- **Prompts**: auto-copied from bundled package data on first run
- **Telegram sessions**: default to data dir when `session_file` is null
