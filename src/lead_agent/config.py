"""Typed application settings loaded from environment variables and an optional .env file."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

_LOG_LEVELS = "^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$"


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or unusable."""


class Settings(BaseSettings):
    """Runtime configuration.

    Secrets are optional at load time so tooling (tests, linting) works without them.
    Call :meth:`require_runtime_secrets` before a real scan.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    openai_api_key: SecretStr | None = None
    telegram_bot_token: SecretStr | None = None
    telegram_chat_id: str | None = None

    openai_model: str = "gpt-4o-mini"
    urgency_threshold: int = Field(default=7, ge=1, le=10)
    max_post_age_days: int = Field(default=14, ge=1, le=90)
    log_level: str = Field(default="INFO", pattern=_LOG_LEVELS)
    dry_run: bool = False
    targets_path: Path = Path("targets.json")

    def missing_secrets(self) -> list[str]:
        """Return the names of required secrets that are unset or empty."""
        required = {
            "OPENAI_API_KEY": self.openai_api_key,
            "TELEGRAM_BOT_TOKEN": self.telegram_bot_token,
            "TELEGRAM_CHAT_ID": self.telegram_chat_id,
        }
        missing: list[str] = []
        for name, value in required.items():
            raw = value.get_secret_value() if isinstance(value, SecretStr) else value
            if not raw or not raw.strip():
                missing.append(name)
        return missing

    def require_runtime_secrets(self) -> None:
        """Raise :class:`ConfigError` listing every missing secret."""
        missing = self.missing_secrets()
        if missing:
            raise ConfigError(f"Missing required settings: {', '.join(missing)}")


def load_settings() -> Settings:
    """Load settings from the environment (and .env if present)."""
    return Settings()
