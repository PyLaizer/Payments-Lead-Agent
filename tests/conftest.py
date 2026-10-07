"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

_ENV_KEYS = (
    "OPENAI_API_KEY",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
    "OPENAI_MODEL",
    "URGENCY_THRESHOLD",
    "MAX_POST_AGE_DAYS",
    "LOG_LEVEL",
    "DRY_RUN",
    "TARGETS_PATH",
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove app-related variables so tests never depend on the host environment."""
    for key in _ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
