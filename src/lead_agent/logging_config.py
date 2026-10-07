"""Logging setup shared by every module."""

from __future__ import annotations

import logging
import sys

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_ROOT_LOGGER_NAME = "lead_agent"


def configure_logging(level: str = "INFO") -> logging.Logger:
    """Configure the ``lead_agent`` logger once and return it.

    Safe to call repeatedly: existing handlers are replaced, never duplicated.
    """
    logger = logging.getLogger(_ROOT_LOGGER_NAME)
    logger.setLevel(level.upper())
    logger.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the ``lead_agent`` namespace."""
    return logging.getLogger(f"{_ROOT_LOGGER_NAME}.{name}")
