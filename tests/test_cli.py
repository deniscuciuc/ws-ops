"""CLI integration tests with mocked providers."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from src.cli import app

runner = CliRunner()


def test_cli_help_succeeds() -> None:
    """Verify all commands are listed."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "morning" in result.output
    assert "evening" in result.output
    assert "run" in result.output
    assert "actions" in result.output
    assert "config-check" in result.output


def test_config_check_no_env(tmp_path: Path) -> None:
    """config-check should report no sources configured by default."""
    with patch.dict(os.environ, {}, clear=True):
        result = runner.invoke(app, ["config-check"])
    assert result.exit_code == 0
    assert "Config loaded successfully" in result.output


def test_actions_no_db(tmp_path: Path) -> None:
    """actions should handle missing database gracefully."""
    result = runner.invoke(app, ["actions"])
    assert result.exit_code == 0


def test_actions_status_all(tmp_path: Path) -> None:
    """actions --status all should not error."""
    result = runner.invoke(app, ["actions", "--status", "all"])
    assert result.exit_code == 0


def test_run_unknown_source() -> None:
    """run with unknown source should filter to nothing, not crash."""
    result = runner.invoke(app, ["run", "nonexistent"])
    assert result.exit_code == 0


def test_morning_dry_run(tmp_path: Path) -> None:
    """morning --dry-run should complete without errors."""
    with patch.dict(os.environ, {}, clear=True):
        result = runner.invoke(app, ["morning", "--dry-run", "--no-notify"])
    assert result.exit_code == 0


def test_evening_no_notify(tmp_path: Path) -> None:
    """evening --no-notify should complete without errors."""
    with patch.dict(os.environ, {}, clear=True):
        result = runner.invoke(app, ["evening", "--no-notify"])
    assert result.exit_code == 0
