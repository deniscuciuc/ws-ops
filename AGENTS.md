# ws-ops — Agent Project Prompt

> You are a **Senior Python Engineer** working on `ws-ops` — a personal workstation automation CLI
> for a developer/CTO. The tool organizes email, digests dev feeds (GitLab, GitHub, Jira, Telegram),
> and surfaces actionable intelligence using local or remote LLMs.
> Read this document fully before writing any code.

---

## Project Identity

| Field       | Value                                                                 |
|-------------|-----------------------------------------------------------------------|
| Name        | `ws-ops`                                                              |
| CLI command | `ws-ops` (or alias `wso`)                                             |
| Purpose     | Personal AI-powered workstation automation for developers             |
| Tagline     | *Organizes your inbox, digests your dev feeds, surfaces what matters* |
| Audience    | Solo developer / CTO running multiple projects                        |
| Style       | CLI-first, no GUI, no daemons, on-demand execution                    |

---

## Philosophy & Constraints

- **On-demand only** — no background daemons, no cron jobs. User runs it when they want.
  Heavy LLM inference should not interfere with active work sessions.
- **Zero hardcodes** — every token, credential, folder name, prompt, and threshold lives in config.
- **Modular sources** — each data source (email, GitLab, etc.) is a self-contained plugin.
  Adding a new source must not require touching core logic.
- **Multi-provider LLM** — support Ollama (local), OpenAI, Anthropic, and any OpenAI-compatible
  endpoint. User picks provider and model in config.
- **Prompt management** — prompts are not strings in code. They live in YAML files under `prompts/`,
  versioned, overridable per-user without touching source code.
- **Lightweight storage** — SQLite only. No PostgreSQL, no Redis. This is a personal tool.
- **Clean output** — terminal output uses `rich`. Telegram digest is Markdown-formatted.
- **No magic** — explicit over implicit. Every action is logged. Dry-run mode available everywhere.
