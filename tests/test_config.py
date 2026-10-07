"""Tests for settings loading and validation."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from lead_agent.config import ConfigError, Settings


def make_settings(**overrides: object) -> Settings:
    """Build Settings without reading a local .env file."""
    return Settings(_env_file=None, **overrides)  # type: ignore[arg-type]


def test_defaults() -> None:
    s = make_settings()
    assert s.openai_model == "gpt-4o-mini"
    assert s.urgency_threshold == 7
    assert s.max_post_age_days == 14
    assert s.dry_run is False
    assert s.targets_path == Path("targets.json")


def test_reads_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("URGENCY_THRESHOLD", "8")
    monkeypatch.setenv("DRY_RUN", "true")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")
    s = make_settings()
    assert s.urgency_threshold == 8
    assert s.dry_run is True
    assert s.telegram_chat_id == "12345"


@pytest.mark.parametrize("value", ["0", "11"])
def test_threshold_out_of_range_rejected(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("URGENCY_THRESHOLD", value)
    with pytest.raises(ValidationError):
        make_settings()


def test_invalid_log_level_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "LOUD")
    with pytest.raises(ValidationError):
        make_settings()


def test_missing_secrets_reported() -> None:
    s = make_settings()
    assert s.missing_secrets() == ["OPENAI_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]
    with pytest.raises(ConfigError, match="OPENAI_API_KEY"):
        s.require_runtime_secrets()


def test_blank_secret_counts_as_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "   ")
    assert "OPENAI_API_KEY" in make_settings().missing_secrets()


def test_all_secrets_present_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")
    s = make_settings()
    assert s.missing_secrets() == []
    s.require_runtime_secrets()


def test_secrets_not_leaked_in_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-super-secret")
    assert "sk-super-secret" not in repr(make_settings())
