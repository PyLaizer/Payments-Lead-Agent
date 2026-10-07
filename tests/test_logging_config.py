"""Tests for logging setup."""

from __future__ import annotations

import logging

import pytest

from lead_agent.logging_config import configure_logging, get_logger


def test_configure_is_idempotent() -> None:
    configure_logging("INFO")
    logger = configure_logging("DEBUG")
    assert len(logger.handlers) == 1
    assert logger.level == logging.DEBUG


def test_child_logger_emits_to_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("INFO")
    get_logger("demo").info("hello world")
    out = capsys.readouterr().out
    assert "hello world" in out
    assert "lead_agent.demo" in out
