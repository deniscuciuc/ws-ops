# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Source registry (`src/registry.py`) — central registration for data sources
- CLI integration tests using `typer.testing.CliRunner` (7 new tests)
- GitHub Actions CI workflow (lint, test matrix, type-check)
- Portable path resolution via `platformdirs` (cross-platform config/data dirs)
- `.env` auto-detection across XDG config dir, CWD, and package root
- Prompt auto-copy from bundled package data on first run
- Makefile with common targets (`install`, `test`, `lint`, `typecheck`, `run`)
- Canonical AI agent docs (`docs/ai-agents.md`)
- `CHANGELOG.md` with Keep a Changelog format
- Release workflow and packaging metadata

### Changed

- `Source.run()` now skips all DB persistence during `dry_run` (truly side-effect free)
- Sources receive `PromptManager` instance instead of hardcoded `"./prompts"` path
- `_run_sources()` returns `DigestResult` for proper notification flow
- `actions --status all` queries all rows (not filtered to "open")
- `config-check` now validates prompt directory existence and DB writability
- Telegram `session_file` defaults to platform data dir when null
- `AGENTS.md` consolidated to project identity + pointer to `docs/ai-agents.md`
- `.github/copilot-instructions.md` consolidated to key points + canonical doc pointer
- Docs updated for new path strategy and installation flows

### Fixed

- `morning` and `evening` now pass the actual digest to Telegram notifier (was `None`)
