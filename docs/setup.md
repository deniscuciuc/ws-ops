# Setup

## Requirements

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) installed
- Ollama running locally (or API keys for a remote LLM provider)

## Installation

### From source (development)

```bash
# Clone
git clone https://github.com/yourname/ws-ops.git
cd ws-ops

# Install with uv (creates venv automatically)
uv sync

# Copy and configure
cp .env.example .env
$EDITOR .env

# Verify
uv run ws-ops config-check
```

### Global install (end user)

```bash
# From a local clone
uv tool install .

# Or direct from Git
uv tool install git+https://github.com/yourname/ws-ops.git

# Configure (creates ~/.config/ws-ops/.env on Linux)
mkdir -p ~/.config/ws-ops
cp .env.example ~/.config/ws-ops/.env
$EDITOR ~/.config/ws-ops/.env

# Verify
ws-ops config-check
```

### Shell Alias (Optional)

```bash
# ~/.zshrc
alias wso="ws-ops"
```

## Quick Start

1. Configure at least one source in `.env` (place it in `~/.config/ws-ops/.env` for global install, or `$PWD/.env` for local dev)
2. Run `ws-ops config-check` to verify setup
3. Run `ws-ops morning` for your first digest
4. Set up Telegram bot notifications (optional)
