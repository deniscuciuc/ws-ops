# Configuration

All configuration lives in `.env` or environment variables. The prefix `WS_OPS_` is used
for all settings. Nested config uses `__` as delimiter (e.g., `WS_OPS_LLM__PROVIDER`).

## LLM

| Variable | Default | Description |
|----------|---------|-------------|
| `WS_OPS_LLM__PROVIDER` | `ollama` | `ollama`, `openai`, or `anthropic` |
| `WS_OPS_LLM__OLLAMA__MODEL` | `llama3.1:8b` | Ollama model name |
| `WS_OPS_LLM__OLLAMA__BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `WS_OPS_LLM__OPENAI__API_KEY` | — | OpenAI API key |
| `WS_OPS_LLM__OPENAI__MODEL` | `gpt-4o-mini` | OpenAI model |
| `WS_OPS_LLM__OPENAI__BASE_URL` | `https://api.openai.com/v1` | Compat endpoint URL |

## Sources

Multi-account sources use JSON arrays in env vars. See `.env.example` for full examples.

### Email

```dotenv
WS_OPS_EMAIL_ACCOUNTS='[{"name": "work", "host": "imap.gmail.com", ...}]'
```

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Account label |
| `host` | string | IMAP server |
| `port` | int | IMAP port (default: 993) |
| `username` | string | Login |
| `password` | string | App password |
| `fetch_limit` | int | Max emails per run (default: 50) |
| `folders_map` | dict | Slug → IMAP folder mapping |

### GitLab

```dotenv
WS_OPS_GITLAB_INSTANCES='[{"name": "qgcore", "url": "https://gitlab.com", ...}]'
```

### GitHub

```dotenv
WS_OPS_GITHUB_ACCOUNTS='[{"name": "personal", "token": "ghp_...", ...}]'
```

### Telegram

```dotenv
WS_OPS_TELEGRAM_ACCOUNTS='[{"name": "personal", "api_id": 12345, ...}]'
```

First run triggers interactive phone + code authentication. Session saved to `session_file`.

### Jira

```dotenv
WS_OPS_JIRA_INSTANCES='[{"name": "myorg", "server": "https://myorg.atlassian.net", ...}]'
```

## Global

| Variable | Default | Description |
|----------|---------|-------------|
| `WS_OPS_DRY_RUN` | `false` | Preview actions without executing |
| `WS_OPS_DB_PATH` | `~/.local/share/ws-ops/ws_ops.db`¹ | SQLite database path |
| `WS_OPS_PROMPTS_DIR` | `~/.local/share/ws-ops/prompts`¹ | Override prompts directory |
| `WS_OPS_OUTPUT_DIR` | `~/.local/share/ws-ops/output`¹ | Output directory |
| `WS_OPS_ENV_FILE` | auto-detected² | Explicit path to `.env` file |

¹ Platform-specific: shown for Linux. Uses `platformdirs` — macOS uses `~/Library/Application Support/ws-ops/`, Windows uses `%LOCALAPPDATA%/ws-ops/`.

² Resolution order: `WS_OPS_ENV_FILE` override → `XDG_CONFIG_HOME/ws-ops/.env` → `$PWD/.env` → package root `.env`.
