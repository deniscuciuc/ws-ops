# ws-ops — common commands
# First run: `uv sync` to create the virtualenv.

.PHONY: install install-global test test-file lint lint-fix typecheck run help clean

install:           ## Install dev dependencies and package
	uv sync

install-global:    ## Install as a global CLI tool
	uv tool install .

test:              ## Run all tests
	uv run pytest

test-file f=%:     ## Run tests in a specific file (make test-file f=tests/test_cli.py)
	uv run pytest $(f) -v

lint:              ## Lint with ruff
	uv run ruff check

lint-fix:          ## Auto-fix lint issues
	uv run ruff check --fix

typecheck:         ## Type check with pyright (strict mode)
	uv run pyright

run:               ## Run ws-ops (pass args via ARGS, e.g. make run ARGS="morning --help")
	uv run ws-ops $(ARGS)

clean:             ## Remove caches and build artifacts
	rm -rf .ruff_cache .pytest_cache *.egg-info/ dist/ build/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

help:              ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
