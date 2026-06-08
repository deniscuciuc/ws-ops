# Setup

## Requirements

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) installed
- Ollama running locally (or API keys for a remote LLM provider)

## Installation

```bash
# Clone
git clone https://github.com/yourname/ws-ops.git
cd ws-ops

# Install with uv (creates venv automatically)
uv sync

# Copy and configure
cp .env.example .env
$EDITOR .env

# Install CLI globally
uv tool install .

# Verify
ws-ops config-check
```

## Shell Alias (Optional)

```bash
# ~/.zshrc
alias wso="ws-ops"
```

## Quick Start

1. Configure at least one source in `.env`
2. Run `ws-ops config-check` to verify setup
3. Run `ws-ops morning` for your first digest
4. Set up Telegram bot notifications (optional)
