"""Shared fixtures for ws-ops tests."""

from __future__ import annotations

import pytest


@pytest.fixture
def sample_email_body() -> str:
    return (
        "Hi Denis, the deployment pipeline failed again. "
        "Can you please check the latest build? "
        "We need this fixed before the client demo on Friday. — Alex"
    )
