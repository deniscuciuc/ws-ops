# ws-ops — Copilot Instructions

This file is the **GitHub Copilot entrypoint** for this repository.
For the canonical AI agent reference (architecture, conventions, source registry,
error handling, database patterns, path resolution), see **[docs/ai-agents.md](../docs/ai-agents.md)**.

## Quick Start

```bash
make install        # uv sync
make test           # Run all tests
make lint           # ruff check
make typecheck      # pyright
make run ARGS="morning --help"   # Run CLI
```

## Key Points (not covered in the canonical doc)

- **Source registration**: after creating a new source, register it in `src/sources/__init__.py` via `register_source()` — not in `digest.py` or `cli.py` directly.
- **Source base class**: `src/sources/base.py` — implements `fetch() → classify() → act()` pipeline with built-in dedup and error isolation.
- **Entity IDs**: `source:account:external_id` format (e.g., `email:work:<Message-ID>`).
- **dry_run**: must skip ALL external writes (DB, IMAP, APIs) — verified by tests.
- **Prompts**: YAML files in `prompts/` with Jinja2 templates — never hardcoded.
- **Paths**: use `platformdirs` for cross-platform defaults — don't hardcode `~/.ws-ops/`.
